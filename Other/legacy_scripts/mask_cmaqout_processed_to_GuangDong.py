#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mask CMAQ processed CSVs to GuangDong province.

- Input: CSV files in cmaqout_processed (unmasked), expected to contain columns ROW, COL and variables.
- Output: CSV files in cmaqout_processed_GuangDong, same content but values outside GuangDong are set to NaN.
  Output filename gets suffix `_GuangDong` before `.csv`.

Mask method follows `process_GDEI_ALL_True_AutoUnit.py`:
- Build grid center coordinates from IOAPI attributes (XORIG, YORIG, XCELL, YCELL, NCOLS, NROWS)
- Transform LCC projection coords to lon/lat
- Use Guangdong boundary polygon (China_provinces.json, adcode=440000) to determine inside/outside

Usage:
  python3 GuangDong/mask_cmaqout_processed_to_GuangDong.py \
    --input_dir /data/workspace/GuangDong/cmaqout_processed \
    --output_dir /data/workspace/GuangDong/cmaqout_processed_GuangDong \
    --grid_file /data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3 \
    --provinces_json /data/workspace/GuangDong/China_provinces.json
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd
import xarray as xr
import json

from shapely.geometry import shape
from shapely.geometry import Point
from shapely.prepared import prep
from pyproj import CRS, Transformer


def load_guangdong_boundary(provinces_json_path: str):
    with open(provinces_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        if props.get("adcode") == 440000:
            return shape(feature.get("geometry"))

    raise ValueError("广东省边界信息未找到 (adcode=440000)")


def get_grid_xy_from_ioapi(nc_file: str) -> Tuple[np.ndarray, np.ndarray, int, int, dict]:
    """Return 2D projected x/y coords (center points), rows, cols, and attrs."""
    with xr.open_dataset(nc_file) as ds:
        # Dimensions: prefer ROW/COL when available
        rows = int(len(ds["ROW"])) if "ROW" in ds.dims or "ROW" in ds.coords else int(ds.dims.get("ROW", 0))
        cols = int(len(ds["COL"])) if "COL" in ds.dims or "COL" in ds.coords else int(ds.dims.get("COL", 0))

        if rows <= 0 or cols <= 0:
            # fallback to NROWS/NCOLS attrs
            rows = int(ds.attrs.get("NROWS"))
            cols = int(ds.attrs.get("NCOLS"))

        xorig = float(ds.attrs.get("XORIG", 0.0))
        yorig = float(ds.attrs.get("YORIG", 0.0))
        xcell = float(ds.attrs.get("XCELL", 1.0))
        ycell = float(ds.attrs.get("YCELL", 1.0))

        x_coords = xorig + (np.arange(cols) + 0.5) * xcell
        y_coords = yorig + (np.arange(rows) + 0.5) * ycell
        x_2d, y_2d = np.meshgrid(x_coords, y_coords)

        return x_2d, y_2d, rows, cols, dict(ds.attrs)


def build_transformer_from_ioapi_attrs(attrs: dict) -> Transformer:
    required = ["P_ALP", "P_BET", "P_GAM", "XCENT", "YCENT"]
    missing = [k for k in required if k not in attrs]
    if missing:
        raise ValueError(f"网格文件缺少投影属性: {missing}")

    p_alp = float(attrs["P_ALP"])
    p_bet = float(attrs["P_BET"])
    p_gam = float(attrs["P_GAM"])
    xcent = float(attrs["XCENT"])
    ycent = float(attrs["YCENT"])

    proj_lcc = CRS.from_string(
        f"+proj=lcc +lat_1={p_alp} +lat_2={p_bet} +lat_0={ycent} +lon_0={p_gam} "
        f"+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    proj_wgs84 = CRS.from_epsg(4326)
    return Transformer.from_crs(proj_lcc, proj_wgs84, always_xy=True)


def create_guangdong_mask(grid_file: str, provinces_json: str) -> np.ndarray:
    boundary = load_guangdong_boundary(provinces_json)
    boundary_prep = prep(boundary)

    x_2d, y_2d, rows, cols, attrs = get_grid_xy_from_ioapi(grid_file)
    transformer = build_transformer_from_ioapi_attrs(attrs)

    # Vectorized transform to lon/lat
    lon, lat = transformer.transform(x_2d, y_2d)

    mask = np.zeros((rows, cols), dtype=bool)
    # Shapely contains isn't vectorized reliably; loop over flattened arrays
    lon_f = lon.ravel()
    lat_f = lat.ravel()
    out = np.zeros(lon_f.shape[0], dtype=bool)
    for i in range(lon_f.shape[0]):
        out[i] = boundary_prep.contains(Point(float(lon_f[i]), float(lat_f[i])))
    mask[:, :] = out.reshape((rows, cols))

    return mask


def list_input_csvs(input_dir: Path) -> List[Path]:
    files = sorted(input_dir.glob("*.csv"))
    out: List[Path] = []
    for p in files:
        name = p.name
        if "_HuiZhou" in name:
            continue
        if "_GuangDong" in name:
            continue
        # 这些通常不是网格逐点文件
        if "RegionalAverage" in name:
            continue
        out.append(p)
    return out


def mask_one_csv(path: Path, out_dir: Path, mask: np.ndarray) -> Path | None:
    df = pd.read_csv(path)
    if "ROW" not in df.columns or "COL" not in df.columns:
        return None

    df_sorted = df.sort_values(["ROW", "COL"]).reset_index(drop=True)
    rows, cols = mask.shape
    expected = rows * cols
    if len(df_sorted) != expected:
        # 尽量兼容：只要 ROW/COL 覆盖全域也可
        # 但这里按最小要求处理：长度不匹配则跳过
        raise ValueError(f"{path.name} 行数({len(df_sorted)})与网格({rows}x{cols}={expected})不匹配")

    value_cols = [c for c in df_sorted.columns if c not in ("ROW", "COL")]

    for col_name in value_cols:
        # 只对数值列做mask；非数值列保持原样
        if not pd.api.types.is_numeric_dtype(df_sorted[col_name]):
            continue
        grid = df_sorted[col_name].to_numpy().reshape((rows, cols))
        grid_masked = np.where(mask, grid, np.nan)
        df_sorted[col_name] = grid_masked.reshape(-1)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = path.stem + "_GuangDong.csv"
    out_path = out_dir / out_name
    df_sorted.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Mask cmaqout_processed CSVs to GuangDong province (outside set to NaN)")
    ap.add_argument("--input_dir", required=True)
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--grid_file", required=True)
    ap.add_argument("--provinces_json", required=True)
    ap.add_argument("--limit", type=int, default=None, help="Optional limit number of files (for testing)")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"input_dir not found: {input_dir}")

    print("Building GuangDong mask...")
    mask = create_guangdong_mask(args.grid_file, args.provinces_json)
    print(f"Mask built. Inside GuangDong grids: {int(mask.sum())} / {mask.size}")

    files = list_input_csvs(input_dir)
    if args.limit is not None:
        files = files[: args.limit]

    if not files:
        print("No eligible CSVs found.")
        return 0

    print(f"Processing {len(files)} CSV files...")
    ok = 0
    skipped = 0
    for p in files:
        try:
            out = mask_one_csv(p, out_dir, mask)
            if out is None:
                skipped += 1
                print(f"SKIP (no ROW/COL): {p.name}")
            else:
                ok += 1
                print(f"OK: {p.name} -> {out.name}")
        except Exception as e:
            print(f"FAIL: {p.name}: {e}")

    print(f"Done. ok={ok}, skipped={skipped}, total={len(files)}")
    print(f"Output dir: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

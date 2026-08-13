#!/usr/bin/env python3
"""Create land-only and GuangDong-masked MCIP CSVs from a source folder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep
from pyproj import CRS, Transformer


# Configuration: edit these paths as needed
INPUT_DIR = Path("/data/workspace/GuangDong/mcipout_processed")
LAND_OUTPUT_DIR = Path("/data/workspace/GuangDong/mcipout_processed_land")
GUANGDONG_OUTPUT_DIR = Path("/data/workspace/GuangDong/mcipout_processed_GuangDong")
GRID_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"
CHINA_JSON = "/data/workspace/GuangDong/china.json"
PROVINCES_JSON = "/data/workspace/GuangDong/China_provinces.json"
FILE_LIMIT: int | None = None


def load_land_geometry(china_json_path: str):
    with open(china_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    polygons = []
    for feat in data.get("features", []):
        geom_def = feat.get("geometry")
        if not geom_def:
            continue
        geom = shape(geom_def)
        if not geom.is_valid:
            geom = geom.buffer(0)
        if geom.is_empty:
            continue
        polygons.append(geom)
    if not polygons:
        raise ValueError("未在 china.json 中找到任何多边形")
    return unary_union(polygons)


def load_guangdong_boundary(provinces_json_path: str):
    with open(provinces_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        if props.get("adcode") == 440000:
            geom = shape(feat.get("geometry"))
            if not geom.is_valid:
                geom = geom.buffer(0)
            if not geom.is_empty:
                return geom
    raise ValueError("未在 China_provinces.json 中找到广东省边界 (adcode=440000)")


def get_grid_xy_from_ioapi(nc_file: str) -> Tuple[np.ndarray, np.ndarray, int, int, dict]:
    with xr.open_dataset(nc_file) as ds:
        rows = int(len(ds["ROW"])) if "ROW" in ds.coords else int(ds.dims.get("ROW", 0))
        cols = int(len(ds["COL"])) if "COL" in ds.coords else int(ds.dims.get("COL", 0))
        if rows <= 0 or cols <= 0:
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

    proj_lcc = CRS.from_string(
        "+proj=lcc +lat_1={lat1} +lat_2={lat2} +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs".format(
            lat1=float(attrs["P_ALP"]),
            lat2=float(attrs["P_BET"]),
            lat0=float(attrs["YCENT"]),
            lon0=float(attrs["P_GAM"]),
        )
    )
    proj_wgs84 = CRS.from_epsg(4326)
    return Transformer.from_crs(proj_lcc, proj_wgs84, always_xy=True)


def create_land_mask(grid_file: str, china_json: str) -> np.ndarray:
    land_geom = load_land_geometry(china_json)
    land_prep = prep(land_geom)

    x_2d, y_2d, rows, cols, attrs = get_grid_xy_from_ioapi(grid_file)
    transformer = build_transformer_from_ioapi_attrs(attrs)
    lon, lat = transformer.transform(x_2d, y_2d)

    mask = np.zeros((rows, cols), dtype=bool)
    lon_f = lon.ravel()
    lat_f = lat.ravel()
    inside = np.zeros(lon_f.shape[0], dtype=bool)
    for idx in range(lon_f.shape[0]):
        inside[idx] = land_prep.contains(Point(float(lon_f[idx]), float(lat_f[idx])))
    mask[:, :] = inside.reshape((rows, cols))
    return mask


def create_guangdong_mask(grid_file: str, provinces_json: str) -> np.ndarray:
    gd_geom = prep(load_guangdong_boundary(provinces_json))

    x_2d, y_2d, rows, cols, attrs = get_grid_xy_from_ioapi(grid_file)
    transformer = build_transformer_from_ioapi_attrs(attrs)
    lon, lat = transformer.transform(x_2d, y_2d)

    mask = np.zeros((rows, cols), dtype=bool)
    lon_f = lon.ravel()
    lat_f = lat.ravel()
    inside = np.zeros(lon_f.shape[0], dtype=bool)
    for idx in range(lon_f.shape[0]):
        inside[idx] = gd_geom.contains(Point(float(lon_f[idx]), float(lat_f[idx])))
    mask[:, :] = inside.reshape((rows, cols))
    return mask


def list_input_csvs(input_dir: Path) -> List[Path]:
    files = sorted(input_dir.glob("*.csv"))
    out: List[Path] = []
    for p in files:
        name = p.name
        if any(token in name for token in ("_land", "_GuangDong", "_HuiZhou")):
            continue
        if "RegionalAverage" in name:
            continue
        out.append(p)
    return out


def mask_dataframe(df_sorted: pd.DataFrame, mask: np.ndarray, numeric_cols: List[str]) -> pd.DataFrame:
    rows, cols = mask.shape
    masked = df_sorted.copy()
    for col_name in numeric_cols:
        grid = masked[col_name].to_numpy().reshape((rows, cols))
        masked[col_name] = np.where(mask, grid, np.nan).reshape(-1)
    return masked


def main() -> int:
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"input_dir not found: {INPUT_DIR}")

    print("Building land mask (china.json)...")
    land_mask = create_land_mask(GRID_FILE, CHINA_JSON)
    print(f"Land mask built. Land grids: {int(land_mask.sum())} / {land_mask.size}")

    print("Building GuangDong mask (China_provinces.json)...")
    gd_mask = create_guangdong_mask(GRID_FILE, PROVINCES_JSON)
    print(f"GuangDong mask built. Inside grids: {int(gd_mask.sum())} / {gd_mask.size}")

    files = list_input_csvs(INPUT_DIR)
    if FILE_LIMIT is not None:
        files = files[: FILE_LIMIT]

    if not files:
        print("No eligible CSVs found.")
        return 0

    LAND_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GUANGDONG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Processing {len(files)} CSV files...")
    ok_land = ok_gd = skipped = 0
    for csv_path in files:
        try:
            df = pd.read_csv(csv_path)
            if "ROW" not in df.columns or "COL" not in df.columns:
                skipped += 1
                print(f"SKIP (no ROW/COL): {csv_path.name}")
                continue

            df_sorted = df.sort_values(["ROW", "COL"]).reset_index(drop=True)
            rows, cols = land_mask.shape
            expected = rows * cols
            if len(df_sorted) != expected:
                raise ValueError(f"{csv_path.name} 行数({len(df_sorted)})与网格({rows}x{cols}={expected})不匹配")

            numeric_cols = [c for c in df_sorted.columns if c not in ("ROW", "COL") and pd.api.types.is_numeric_dtype(df_sorted[c])]

            land_df = mask_dataframe(df_sorted, land_mask, numeric_cols)
            land_out = LAND_OUTPUT_DIR / f"{csv_path.stem}_land.csv"
            land_df.to_csv(land_out, index=False, encoding="utf-8-sig")
            ok_land += 1

            gd_df = mask_dataframe(df_sorted, gd_mask, numeric_cols)
            gd_out = GUANGDONG_OUTPUT_DIR / f"{csv_path.stem}_GuangDong.csv"
            gd_df.to_csv(gd_out, index=False, encoding="utf-8-sig")
            ok_gd += 1

            print(f"OK: {csv_path.name} -> {land_out.name} & {gd_out.name}")
        except Exception as exc:
            print(f"FAIL: {csv_path.name}: {exc}")

    print(f"Done. ok_land={ok_land}, ok_gd={ok_gd}, skipped={skipped}, total_files={len(files)}")
    print(f"Land output dir: {LAND_OUTPUT_DIR}")
    print(f"GuangDong output dir: {GUANGDONG_OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

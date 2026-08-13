#!/usr/bin/env python3
"""
Run_Map_Single.py — 单独空间分布图入口
========================================
输入: Data/Processed/ 或 Data/Masked/
输出: Picture/Map_Single/

用法:
    python Run_Map_Single.py                    # 默认全数据源
    python Run_Map_Single.py --source cmaq      # 仅 CMAQ
    python Run_Map_Single.py --source mcip      # 仅 MCIP
    python Run_Map_Single.py --region GuangDong # 仅广东掩膜数据
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Core_Map import run_single_map_pipeline

# ============================================================
# 项目路径配置
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent

# 网格与边界文件
MODEL_FILE = str(PROJECT_ROOT / "Data" / "Boundary" / "GRIDCRO2D_2000121_GuangDongD3")
BOUNDARY_JSON = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"

# 数据源 → 输入目录 / 输出目录映射
SOURCE_MAP = {
    "cmaq": {
        "input": str(PROJECT_ROOT / "Data" / "Processed" / "CMAQ"),
        "output": str(PROJECT_ROOT / "Picture" / "Map_Single" / "CMAQ"),
    },
    "mcip": {
        "input": str(PROJECT_ROOT / "Data" / "Processed" / "MCIP"),
        "output": str(PROJECT_ROOT / "Picture" / "Map_Single" / "MCIP"),
    },
    "emission": {
        "input": str(PROJECT_ROOT / "Data" / "Processed" / "Emission"),
        "output": str(PROJECT_ROOT / "Picture" / "Map_Single" / "Emission"),
    },
}

# 默认年份和月份
DEFAULT_YEARS = ["2000", "2023", "2030", "2060"]
DEFAULT_MONTHS = ["01", "07"]


def main():
    parser = argparse.ArgumentParser(description="GuangDong 单独空间分布图")
    parser.add_argument("--source", action="append", dest="sources",
                        choices=["cmaq", "mcip", "emission"],
                        help="数据源 (可重复指定)")
    parser.add_argument("--region", type=str, default="",
                        choices=["", "GuangDong", "HuiZhou", "Land"],
                        help="区域掩膜后缀")
    parser.add_argument("--unified-legend", action="store_true",
                        help="使用统一图例")
    args = parser.parse_args()

    sources = args.sources or ["cmaq", "mcip", "emission"]
    region_suffix = f"_{args.region}" if args.region else ""

    for src in sources:
        cfg = SOURCE_MAP[src]
        if not os.path.isdir(cfg["input"]):
            print(f"\n[SKIP] {src}: 输入目录不存在: {cfg['input']}")
            continue

        run_single_map_pipeline(
            data_dir=cfg["input"],
            output_dir=cfg["output"],
            model_file=MODEL_FILE,
            boundary_json=BOUNDARY_JSON,
            data_source=src,
            years=DEFAULT_YEARS,
            months=DEFAULT_MONTHS,
            region_suffix=region_suffix,
            unified_legend=args.unified_legend,
        )

    print("\n全部完成。")


if __name__ == "__main__":
    main()

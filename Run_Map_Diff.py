#!/usr/bin/env python3
"""
Run_Map_Diff.py — 差异对比地图入口
====================================
输入: Data/Processed/ 或 Data/Masked/
输出: Picture/Map_Diff/

用法:
    python Run_Map_Diff.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Core_Map import run_diff_map_pipeline

# ============================================================
# 项目路径配置
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent

MODEL_FILE = str(PROJECT_ROOT / "Data" / "Boundary" / "GRIDCRO2D_2000121_GuangDongD3")
BOUNDARY_JSON = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"

# CMAQ 数据目录
CMAQ_DATA_DIR = str(PROJECT_ROOT / "Data" / "Processed" / "CMAQ")
CMAQ_OUTPUT_DIR = str(PROJECT_ROOT / "Picture" / "Map_Diff" / "CMAQ")

# MCIP 数据目录
MCIP_DATA_DIR = str(PROJECT_ROOT / "Data" / "Processed" / "MCIP")
MCIP_OUTPUT_DIR = str(PROJECT_ROOT / "Picture" / "Map_Diff" / "MCIP")

# ============================================================
# 对比配置: (文件1, 文件2, 输出后缀)
# 格式: 列表可在使用时按需修改
# ============================================================

# CMAQ CASE 对比
CMAQ_COMPARISON_PAIRS = [
    # 排放变化影响 (CASE1 vs CASE4: 同气象、不同排放)
    ("2000_Emission[2000met]_01.csv", "2023_Emission[2000met]_01.csv", "CASE1-CASE4_Jan"),
    ("2000_Emission[2000met]_07.csv", "2023_Emission[2000met]_07.csv", "CASE1-CASE4_Jul"),
    # 气象变化影响 (CASE1 vs CASE2: 同排放、不同气象)
    ("2000_Emission[2000met]_01.csv", "2000_Emission[2023met]_01.csv", "CASE1-CASE2_Jan"),
    ("2000_Emission[2000met]_07.csv", "2000_Emission[2023met]_07.csv", "CASE1-CASE2_Jul"),
    # 基准对比 (CASE1 vs CASE3: 2000 vs 2023)
    ("2000_Emission[2000met]_01.csv", "2023_Emission[2023met]_01.csv", "CASE1-CASE3_Jan"),
    ("2000_Emission[2000met]_07.csv", "2023_Emission[2023met]_07.csv", "CASE1-CASE3_Jul"),
    # 未来情景 (CASE5 vs CASE3, CASE6 vs CASE3)
    ("2060_Emission[2060met]_01.csv", "2023_Emission[2023met]_01.csv", "CASE5-CASE3_Jan"),
    ("2060_Emission[2060met]_07.csv", "2023_Emission[2023met]_07.csv", "CASE5-CASE3_Jul"),
    ("2030_Emission[2030met]_01.csv", "2023_Emission[2023met]_01.csv", "CASE6-CASE3_Jan"),
    ("2030_Emission[2030met]_07.csv", "2023_Emission[2023met]_07.csv", "CASE6-CASE3_Jul"),
]

# MCIP 对比
MCIP_COMPARISON_PAIRS = [
    ("2000_mcipout_01.csv", "2023_mcipout_01.csv", "2000vs2023_Jan"),
    ("2000_mcipout_07.csv", "2023_mcipout_07.csv", "2000vs2023_Jul"),
    ("2030_mcipout_01.csv", "2023_mcipout_01.csv", "2030vs2023_Jan"),
    ("2030_mcipout_07.csv", "2023_mcipout_07.csv", "2030vs2023_Jul"),
    ("2060_mcipout_01.csv", "2023_mcipout_01.csv", "2060vs2023_Jan"),
    ("2060_mcipout_07.csv", "2023_mcipout_07.csv", "2060vs2023_Jul"),
]


def main():
    print("=" * 60)
    print("Run_Map_Diff — 差异对比地图")
    print("=" * 60)

    # CMAQ 差异对比
    if os.path.isdir(CMAQ_DATA_DIR):
        run_diff_map_pipeline(
            data_dir=CMAQ_DATA_DIR,
            output_dir=CMAQ_OUTPUT_DIR,
            model_file=MODEL_FILE,
            boundary_json=BOUNDARY_JSON,
            data_source="cmaq",
            comparison_pairs=CMAQ_COMPARISON_PAIRS,
        )

    # MCIP 差异对比
    if os.path.isdir(MCIP_DATA_DIR):
        run_diff_map_pipeline(
            data_dir=MCIP_DATA_DIR,
            output_dir=MCIP_OUTPUT_DIR,
            model_file=MODEL_FILE,
            boundary_json=BOUNDARY_JSON,
            data_source="mcip",
            comparison_pairs=MCIP_COMPARISON_PAIRS,
        )

    print("\n全部完成。")


if __name__ == "__main__":
    main()

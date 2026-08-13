#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Bar chart for Heatwave area-days (km^2*day) by Case.

统计口径：
- 使用 mcipout_processed_land 中的 {year}_mcipout_07_land.csv（仅陆地区域）
- 每行对应一个 3km × 3km 网格，面积为 9 km^2
- 对 Heatwave_Days 做面积加权求和：sum(Heatwave_Days) * 9 = km^2*day

本脚本仅使用 Case1（2000年）和 Case3（2023年），颜色与 emission 脚本一致。
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path
from matplotlib.patches import Patch

# Set font (Times New Roman for English + Chinese fallback)
plt.rcParams["font.family"] = ['Times New Roman', 'Noto Serif CJK JP', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display issue
plt.rcParams['text.usetex'] = False  # Disable LaTeX rendering

# ============================
# Case Configuration
# ============================
# Case definitions（与 emission 脚本保持一致）
Case_DEFINITIONS = {
    'Case1': ('2000', '2000', '2000e2000m'),  # 2000排放+2000气象
    'Case2': ('2000', '2023', '2000e2023m'),  # 2000排放+2023气象
    'Case3': ('2023', '2023', '2023e2023m'),  # 2023排放+2023气象
    'Case4': ('2023', '2000', '2023e2000m'),  # 2023排放+2000气象
    'Case5': ('2060', '2060', '2060e2060m'),  # 2060排放+2060气象
    'Case6': ('2030', '2030', '2030e2030m'),  # 2030排放+2030气象
}
# 仅使用 Case1 和 Case3
CaseS = ['Case1', 'Case3']

# Case 对应的气象年份（用于读取 mcipout 数据文件）
CASE_MET_YEAR = {
    'Case1': '2000',
    'Case3': '2023',
}

# Case colors（与 emission 脚本完全一致）
Case_COLORS = {
    'Case1': '#E3A018',  # golden orange
    'Case2': '#6F2DA8',  # royal purple
    'Case3': '#1B8248',  # deep green
    'Case4': '#D73027',  # bright red
    'Case5': '#9C27B0',
    'Case6': '#FFB703',
}

MONTH_CODE = "07"  # 7 月

# 数据目录：使用已做陆地区域处理的结果（仅陆地）
DATA_DIR = Path("/data/workspace/GuangDong/mcipout_processed_hourly_land")
FILENAME_TEMPLATE = "{year}_mcipout_{month}_land.csv"

COLUMN = "Heatwave_Days"

# 网格面积（固定 3km × 3km）
GRID_AREA_KM2 = 3.0 * 3.0

# Output directory
BASE_DIR = Path("/data/workspace/GuangDong")
OUTPUT_DIR = BASE_DIR / "BarCharts_Output_Heatwave"

TITLE = "陆地热浪面积*天数（7月）"
YLABEL = r"面积*天数 (km$^2$·day)"


def load_area_days_for_case(case_id: str) -> float:
    """读取某 Case 对应气象年的 7 月陆地 Heatwave_Days，计算 km^2*day。"""
    year = CASE_MET_YEAR[case_id]
    fp = DATA_DIR / FILENAME_TEMPLATE.format(year=year, month=MONTH_CODE)
    if not fp.exists():
        raise FileNotFoundError(f"未找到数据文件：{fp}")
    df = pd.read_csv(fp)
    if COLUMN not in df.columns:
        raise ValueError(f"文件缺少列 {COLUMN}：{fp}")
    vals = pd.to_numeric(df[COLUMN], errors='coerce').to_numpy(dtype=float)
    return float(np.nansum(vals) * GRID_AREA_KM2)


def prepare_case_series() -> dict:
    """准备 Case1 与 Case3 的 km^2*day。"""
    series = {}
    for case_id in CaseS:
        try:
            val = load_area_days_for_case(case_id)
            series[case_id] = val
            year = CASE_MET_YEAR[case_id]
            print(f"  ✅ {case_id}（{year}年气象）7月: {val:.2f} km^2·day")
        except Exception as e:
            print(f"  ❌ {case_id} 失败: {e}")
            series[case_id] = np.nan
    return series


# ============================
# Bar Chart Plotting Function
# ============================
def plot_case_barchart(series: dict):
    x_labels = CaseS
    y_vals = [series.get(c, np.nan) for c in x_labels]
    colors = [Case_COLORS.get(c, '#4C78A8') for c in x_labels]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(x_labels, y_vals, color=colors, edgecolor="black", linewidth=0.8)

    plt.title(TITLE, fontsize=20, fontweight='bold')
    plt.ylabel(YLABEL, fontsize=18, fontweight='bold')
    plt.xticks(fontsize=15)
    plt.yticks(fontsize=15)

    for rect, val in zip(bars, y_vals):
        if np.isfinite(val):
            plt.text(
                rect.get_x() + rect.get_width() / 2,
                rect.get_height(),
                f"{val:.0f}",
                ha='center',
                va='bottom',
                fontsize=15,
                fontweight='bold',
            )

    y_arr = np.array(y_vals, dtype=float)
    if np.isfinite(y_arr).any():
        max_val = np.nanmax(y_arr)
        plt.ylim(0, max_val * 1.1)

    handles = [
        Patch(facecolor=Case_COLORS.get(c, '#4C78A8'), edgecolor='black', label=c)
        for c in x_labels
    ]
    plt.legend(
        handles=handles,
        loc='upper center',
        bbox_to_anchor=(0.5, -0.08),
        ncol=len(x_labels),
        frameon=False,
        fontsize=14,
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = OUTPUT_DIR / "Heatwave_AreaDays_07_land_Case1_3.png"
    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ Saved: {out}")


# ============================
# Main Function
# ============================
def main():
    print("=" * 80)
    print("         Heatwave Area-Days Bar Chart - Case1 vs Case3 (July)")
    print("=" * 80)

    print("\n📋 Case Definitions:")
    for case_id in CaseS:
        emission, met, desc = Case_DEFINITIONS[case_id]
        print(f"  {case_id}: {desc} (排放{emission}, 气象{met})")

    print(f"\n🔍 Checking data directory:")
    if DATA_DIR.exists():
        print(f"  ✅ {DATA_DIR}")
    else:
        print(f"  ❌ {DATA_DIR} (directory not found)")
        return

    series = prepare_case_series()
    plot_case_barchart(series)

    print("\n🎉 Bar chart generated successfully!")
    print(f"📁 Output directory: {OUTPUT_DIR}")


# ============================
# Execution Entry
# ============================
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Bar chart for Heatwave area-days (km^2*day) by year.

统计口径：
- 使用 mcipout_processed_land 中的 {year}_mcipout_07_land.csv（仅陆地区域）
- 每行对应一个 3km × 3km 网格，面积为 9 km^2
- 对 Heatwave_Days 做面积加权求和：sum(Heatwave_Days) * 9 = km^2*day

输出：对比 2000 与 2023 两根柱形图（7月）
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
# Year-based Configuration
# ============================
YEARS = ["2000", "2023"]
MONTH_CODE = "07"  # 7 月

# 数据目录：使用已做陆地区域处理的结果（仅陆地）
DATA_DIR = Path("/data/workspace/GuangDong/mcipout_processed_hourly_land")
FILENAME_TEMPLATE = "{year}_mcipout_{month}_land.csv"

# COLUMN = "Heatwave_Days"
COLUMN = "Heatwave_Days"

# 网格面积（固定 3km × 3km）
GRID_AREA_KM2 = 3.0 * 3.0

# Output directory
BASE_DIR = Path("/data/workspace/GuangDong")
OUTPUT_DIR = BASE_DIR / "BarCharts_Output_Heatwave"

TITLE = "陆地热浪面积*天数（7月）"
YLABEL = r"面积*天数 (km$^2$·day)"

def load_area_days_for_year(year: str) -> float:
    """读取某年 7 月的陆地 Heatwave_Days，计算 km^2*day。"""
    fp = DATA_DIR / FILENAME_TEMPLATE.format(year=year, month=MONTH_CODE)
    if not fp.exists():
        raise FileNotFoundError(f"未找到数据文件：{fp}")
    df = pd.read_csv(fp)
    if COLUMN not in df.columns:
        raise ValueError(f"文件缺少列 {COLUMN}：{fp}")
    vals = pd.to_numeric(df[COLUMN], errors='coerce').to_numpy(dtype=float)
    return float(np.nansum(vals) * GRID_AREA_KM2)

def prepare_year_series() -> dict:
    """准备 2000 与 2023 两个年份的 km^2*day。"""
    series = {}
    for y in YEARS:
        try:
            val = load_area_days_for_year(y)
            series[y] = val
            print(f"  ✅ {y}年 7月: {val:.2f} km^2·day")
        except Exception as e:
            print(f"  ❌ {y}年 失败: {e}")
            series[y] = np.nan
    return series

# ============================
# Boxplot Plotting Function
# ============================
def plot_year_barchart(series: dict):
    x_labels = ["2000年", "2023年"]
    y_vals = [series.get("2000", np.nan), series.get("2023", np.nan)]
    colors = ["#FFC107", "#6F2DA8"]

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

    if np.isfinite(np.array(y_vals)).any():
        max_val = np.nanmax(y_vals)
        plt.ylim(0, max_val * 1.1)

    # 不显示图例与网格

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = OUTPUT_DIR / "Heatwave_AreaDays_07_land_2000_2023.png"
    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ Saved: {out}")

# ============================
# Main Function
# ============================
def main():
    print("=" * 80)
    print("         Heatwave Area-Days Bar Chart - 2000 vs 2023 (July)")
    print("=" * 80)

    print(f"\n🔍 Checking data directory:")
    if DATA_DIR.exists():
        print(f"  ✅ {DATA_DIR}")
    else:
        print(f"  ❌ {DATA_DIR} (directory not found)")
        return

    # Prepare values for 2000/2023
    series = prepare_year_series()

    # Plot 2-bar chart
    plot_year_barchart(series)

    print("\n🎉 Bar chart generated successfully!")
    print(f"📁 Output directory: {OUTPUT_DIR}")

# ============================
# Execution Entry
# ============================
if __name__ == "__main__":
    main()
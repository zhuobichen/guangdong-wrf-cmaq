#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Bar chart for exceedance area-days (km^2*day) across Cases.

统计口径：
- 使用 cmaqout_processed_GuangDong 中的 *_GuangDong.csv（广东省外网格为 NaN）
- 每行对应一个 3km × 3km 网格，面积为 9 km^2
- 对超标天数变量做面积加权求和：sum(Days) * 9 = km^2*day

变量：
- PM2.5_Days（默认使用 01 月文件）
- O3_Days（默认使用 07 月文件）
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
# Case definitions
Case_DEFINITIONS = {
    'Case1': ('2000', '2000', '2000e2000m'),  # 2000排放+2000气象
    'Case2': ('2000', '2023', '2000e2023m'),  # 2000排放+2023气象
    'Case3': ('2023', '2023', '2023e2023m'),  # 2023排放+2023气象
    'Case4': ('2023', '2000', '2023e2000m'),  # 2023排放+2000气象
    'Case5': ('2060', '2060', '2060e2060m'),  # 2060排放+2060气象
    'Case6': ('2030', '2030', '2030e2030m'),  # 2030排放+2030气象
}
# Default Cases to compare
# CaseS = ['Case1', 'Case3', 'Case5', 'Case6']
CaseS = ['Case1', 'Case2', 'Case3', 'Case4']

# Case colors for plotting
Case_COLORS = {
    'Case1': '#E3A018',  # golden orange (solid line)
    'Case2': '#6F2DA8',  # royal purple (dashed line)
    'Case3': '#1B8248',  # deep green (dash-dot)
    'Case4': '#D73027',  # bright red (dotted)
    'Case5': '#9C27B0',
    'Case6': '#FFB703',
}

# Month mapping (Chinese labels)
MONTH_MAPPING = {f"{i:02d}": f"{i}月" for i in range(1, 13)}

# 数据目录：使用已做广东省掩膜的结果（省外为NaN）
DATA_DIR = Path("/data/workspace/GuangDong/cmaqout_processed_GuangDong")
FILE_SUFFIX = "_GuangDong"

# 网格面积（固定 3km × 3km）
GRID_AREA_KM2 = 3.0 * 3.0

# Output directory
BASE_DIR = Path("/data/workspace/GuangDong")
OUTPUT_DIR = BASE_DIR / "BarCharts_Output_CaseComparison"

# ============================
# Variable Configuration (Area-days)
# ============================
VARIABLES = {
    'PM2.5': {
        'column': 'PM2.5_Days',
        'title_cn': 'PM2.5≥75μg/m3 陆地超标面积*天数',
        'ylabel_cn': r'PM2.5≥75μg/m3 面积*天数 (km$^2$·day)',
        'month_code': '01'
    },
    'O3': {
        'column': 'O3_Days',
        'title_cn': 'O3 陆地超标面积*天数',
        'ylabel_cn': r'O3≥80ppb 超标面积*天数 (km$^2$·day)',
        'month_code': '07'
    },
}

# ============================
# Case Helper Functions
# ============================
def get_Case_filename_pattern(Case_id, month_code, file_suffix=''):
    """Generate filename patterns for a given Case"""
    if Case_id not in Case_DEFINITIONS:
        raise ValueError(f"Unknown Case: {Case_id}")
    
    emission_year, met_year, Case_key = Case_DEFINITIONS[Case_id]
    
    patterns = [
        f"{emission_year}_Emission[{met_year}met]_{month_code}{file_suffix}.csv",
        f"{Case_key}_{month_code}{file_suffix}.csv",
        f"{Case_id}_{month_code}{file_suffix}.csv",
        f"{emission_year}e{met_year}m_{month_code}{file_suffix}.csv",
        # Fallback patterns
        f"{emission_year}_Emission_{month_code}{file_suffix}.csv",
        f"{met_year}_Emission_{month_code}{file_suffix}.csv"
    ]
    
    return patterns

def find_Case_file(Case_id, month_code, data_dir, file_suffix=''):
    """Find file for a given Case"""
    patterns = get_Case_filename_pattern(Case_id, month_code, file_suffix)
    
    for pattern in patterns:
        file_path = data_dir / pattern
        if file_path.exists():
            return file_path
    
    # Try without suffix as last resort
    patterns_without_suffix = get_Case_filename_pattern(Case_id, month_code)
    for pattern in patterns_without_suffix:
        file_path = data_dir / pattern
        if file_path.exists():
            return file_path
    
    return None

def load_area_days(Case_id: str, var_name: str) -> tuple[float, str]:
    """Load one Case and compute total exceedance area-days (km^2*day)."""
    var_cfg = VARIABLES[var_name]
    month_code = var_cfg['month_code']
    file_path = find_Case_file(Case_id, month_code, DATA_DIR, FILE_SUFFIX)
    if not file_path or not file_path.exists():
        raise FileNotFoundError(f"Data file not found: Case={Case_id}, month={month_code}, dir={DATA_DIR}")

    month_name = MONTH_MAPPING.get(month_code, f"Month {month_code}")
    df = pd.read_csv(file_path)

    col = var_cfg['column']
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found in file {file_path}")

    days = pd.to_numeric(df[col], errors='coerce').to_numpy(dtype=float)
    total_area_days = float(np.nansum(days) * GRID_AREA_KM2)
    return total_area_days, month_name

# ============================
# Data Preparation Function
# ============================
def prepare_area_days():
    """Prepare aggregated km^2*day per Case for each variable."""
    results: dict[str, dict[str, float]] = {}
    month_info: dict[str, str] = {}

    for var_name, var_cfg in VARIABLES.items():
        print(f"\n📊 Processing: {var_cfg['title_cn']} ({var_cfg['column']})")
        series: dict[str, float] = {}
        month_name = None
        for Case_id in CaseS:
            try:
                val, mname = load_area_days(Case_id, var_name)
                month_name = mname
                series[Case_id] = val
                print(f"  ✅ {Case_id} {mname}: {val:.2f} km^2·day")
            except Exception as e:
                print(f"  ❌ {Case_id} failed: {e}")
                series[Case_id] = np.nan

        results[var_name] = series
        month_info[var_name] = month_name or "Unknown Month"

    return results, month_info

# ============================
# Boxplot Plotting Function
# ============================
def plot_area_days_barchart(var_name: str, series: dict[str, float], month_name: str):
    var_cfg = VARIABLES[var_name]

    x_labels = CaseS
    y = [series.get(c, np.nan) for c in x_labels]
    colors = [Case_COLORS.get(c, '#4C78A8') for c in x_labels]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(x_labels, y, color=colors, edgecolor="black", linewidth=0.8)

    plt.title(f"{var_cfg['title_cn']}（{month_name}）", fontsize=18, fontweight='bold')
    plt.ylabel(var_cfg['ylabel_cn'], fontsize=16, fontweight='bold')
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)

    for rect, val in zip(bars, y):
        if np.isfinite(val):
            plt.text(
                rect.get_x() + rect.get_width() / 2,
                rect.get_height(),
                f"{val:.0f}",
                ha='center',
                va='bottom',
                fontsize=12,
                fontweight='bold',
            )

    y_vals = np.array(y, dtype=float)
    if np.isfinite(y_vals).any():
        max_val = np.nanmax(y_vals)
        plt.ylim(0, max_val * 1.1)

    handles = [
        Patch(facecolor=Case_COLORS.get(Case, '#4C78A8'), edgecolor='black', label=Case)
        for Case in x_labels
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
    out = OUTPUT_DIR / f"{var_name}_AreaDays_{month_name}_GuangDong.png"
    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ Saved: {out}")

# ============================
# Main Function
# ============================
def main():
    print("=" * 80)
    print("         Area-Days Bar Charts - Case1, Case2, Case3, Case4")
    print("=" * 80)

    # Show Case definitions
    print("\n📋 Case Definitions:")
    for Case_id, (emission, met, desc) in Case_DEFINITIONS.items():
        print(f"  {Case_id}: {desc} (排放{emission}, 气象{met})")

    print(f"\n🔍 Checking data directory:")
    if DATA_DIR.exists():
        print(f"  ✅ {DATA_DIR}")
    else:
        print(f"  ❌ {DATA_DIR} (directory not found)")
        return

    # Prepare aggregated area-days
    area_days, month_info = prepare_area_days()

    # Plot
    for var_name in VARIABLES.keys():
        plot_area_days_barchart(var_name, area_days[var_name], month_info.get(var_name, "Unknown Month"))

    print("\n🎉 All bar charts generated successfully!")
    print(f"📁 Output directory: {OUTPUT_DIR}")

# ============================
# Execution Entry
# ============================
if __name__ == "__main__":
    main()
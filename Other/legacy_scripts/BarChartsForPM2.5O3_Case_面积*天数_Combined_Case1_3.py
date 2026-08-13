#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""合并图：emission(PM2.5, O3) + mcipout(Heatwave) — Case1 vs Case3

将三张子图排成一行，底部共用 Case1/Case3 图例。
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path
from matplotlib.patches import Patch

# Set font
plt.rcParams["font.family"] = ['Times New Roman', 'Noto Serif CJK JP', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['text.usetex'] = False

# ============================
# Case Configuration
# ============================
Case_DEFINITIONS = {
    'Case1': ('2000', '2000', '2000e2000m'),
    'Case2': ('2000', '2023', '2000e2023m'),
    'Case3': ('2023', '2023', '2023e2023m'),
    'Case4': ('2023', '2000', '2023e2000m'),
    'Case5': ('2060', '2060', '2060e2060m'),
    'Case6': ('2030', '2030', '2030e2030m'),
}
CaseS = ['Case1', 'Case3']

Case_COLORS = {
    'Case1': '#E3A018',
    'Case2': '#6F2DA8',
    'Case3': '#1B8248',
    'Case4': '#D73027',
    'Case5': '#9C27B0',
    'Case6': '#FFB703',
}

MONTH_MAPPING = {f"{i:02d}": f"{i}月" for i in range(1, 13)}

# ============================
# Emission 数据配置
# ============================
EMISSION_DATA_DIR = Path("/data/workspace/GuangDong/cmaqout_processed_GuangDong")
EMISSION_FILE_SUFFIX = "_GuangDong"
GRID_AREA_KM2 = 3.0 * 3.0

EMISSION_VARIABLES = {
    'PM2.5': {
        'column': 'PM2.5_Days',
        'title_cn': 'PM2.5≥75μg/m³ 超标面积×天数',
        'ylabel_cn': r'面积×天数 (km$^2$·day)',
        'month_code': '01',
    },
    'O3': {
        'column': 'O3_Days',
        # 关键修改1：将 O₃ 改为 O3
        'title_cn': 'O3≥80ppb 超标面积×天数',
        'ylabel_cn': r'面积×天数 (km$^2$·day)',
        'month_code': '07',
    },
}

# ============================
# Mcipout 数据配置
# ============================
MCIPOUT_DATA_DIR = Path("/data/workspace/GuangDong/mcipout_processed_hourly_land")
MCIPOUT_FILENAME_TEMPLATE = "{year}_mcipout_{month}_land.csv"
MCIPOUT_COLUMN = "Heatwave_Days"
MCIPOUT_MONTH_CODE = "07"
CASE_MET_YEAR = {'Case1': '2000', 'Case3': '2023'}

MCIPOUT_VARIABLE = {
    'title_cn': '陆地热浪面积×天数（7月）',
    'ylabel_cn': r'面积×天数 (km$^2$·day)',
}

# Output
BASE_DIR = Path("/data/workspace/GuangDong")
OUTPUT_DIR = BASE_DIR / "BarCharts_Output_Combined"


# ============================
# Data Loading — Emission
# ============================
def get_emission_filename_patterns(case_id, month_code, suffix=''):
    emission_year, met_year, case_key = Case_DEFINITIONS[case_id]
    return [
        f"{emission_year}_Emission[{met_year}met]_{month_code}{suffix}.csv",
        f"{case_key}_{month_code}{suffix}.csv",
        f"{case_id}_{month_code}{suffix}.csv",
        f"{emission_year}e{met_year}m_{month_code}{suffix}.csv",
        f"{emission_year}_Emission_{month_code}{suffix}.csv",
        f"{met_year}_Emission_{month_code}{suffix}.csv",
    ]

def find_emission_file(case_id, month_code):
    for suffix in [EMISSION_FILE_SUFFIX, '']:
        for pat in get_emission_filename_patterns(case_id, month_code, suffix):
            fp = EMISSION_DATA_DIR / pat
            if fp.exists():
                return fp
    return None

def load_emission_area_days(case_id: str, var_name: str) -> tuple[float, str]:
    var_cfg = EMISSION_VARIABLES[var_name]
    month_code = var_cfg['month_code']
    fp = find_emission_file(case_id, month_code)
    if not fp:
        raise FileNotFoundError(f"Emission file not found: Case={case_id}, month={month_code}")
    month_name = MONTH_MAPPING.get(month_code, month_code)
    df = pd.read_csv(fp)
    col = var_cfg['column']
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not in {fp}")
    days = pd.to_numeric(df[col], errors='coerce').to_numpy(dtype=float)
    return float(np.nansum(days) * GRID_AREA_KM2), month_name


# ============================
# Data Loading — Mcipout
# ============================
def load_mcipout_area_days(case_id: str) -> float:
    year = CASE_MET_YEAR[case_id]
    fp = MCIPOUT_DATA_DIR / MCIPOUT_FILENAME_TEMPLATE.format(year=year, month=MCIPOUT_MONTH_CODE)
    if not fp.exists():
        raise FileNotFoundError(f"Mcipout file not found: {fp}")
    df = pd.read_csv(fp)
    if MCIPOUT_COLUMN not in df.columns:
        raise ValueError(f"Column '{MCIPOUT_COLUMN}' not in {fp}")
    vals = pd.to_numeric(df[MCIPOUT_COLUMN], errors='coerce').to_numpy(dtype=float)
    return float(np.nansum(vals) * GRID_AREA_KM2)


# ============================
# Prepare all data
# ============================
def prepare_all_data():
    emission_results = {}
    emission_months = {}
    for var_name in EMISSION_VARIABLES:
        series = {}
        month_name = None
        for case_id in CaseS:
            try:
                val, mname = load_emission_area_days(case_id, var_name)
                series[case_id] = val
                month_name = mname
                print(f"  ✅ Emission {var_name} {case_id} {mname}: {val:.2f} km²·day")
            except Exception as e:
                print(f"  ❌ Emission {var_name} {case_id}: {e}")
                series[case_id] = np.nan
        emission_results[var_name] = series
        emission_months[var_name] = month_name or "Unknown"

    mcipout_series = {}
    for case_id in CaseS:
        try:
            val = load_mcipout_area_days(case_id)
            mcipout_series[case_id] = val
            print(f"  ✅ Mcipout Heatwave {case_id}: {val:.2f} km²·day")
        except Exception as e:
            print(f"  ❌ Mcipout Heatwave {case_id}: {e}")
            mcipout_series[case_id] = np.nan

    return emission_results, emission_months, mcipout_series


# ============================
# Draw single subplot (shared style)
# ============================
def draw_bar_subplot(ax, series: dict, title: str, ylabel: str):
    x_labels = CaseS
    y_vals = [series.get(c, np.nan) for c in x_labels]
    colors = [Case_COLORS.get(c, '#4C78A8') for c in x_labels]

    bars = ax.bar(x_labels, y_vals, color=colors, edgecolor="black", linewidth=0.8)

    ax.set_title(title, fontsize=14, fontweight='bold', pad=8)
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    ax.tick_params(axis='x', labelsize=13)
    ax.tick_params(axis='y', labelsize=12)

    for rect, val in zip(bars, y_vals):
        if np.isfinite(val):
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                rect.get_height(),
                f"{val:.0f}",
                ha='center', va='bottom',
                fontsize=12, fontweight='bold',
            )

    y_arr = np.array(y_vals, dtype=float)
    if np.isfinite(y_arr).any():
        ax.set_ylim(0, np.nanmax(y_arr) * 1.15)

    ax.grid(False)


# ============================
# Main plot
# ============================
def plot_combined(emission_results, emission_months, mcipout_series):
    fig, axes = plt.subplots(1, 3, figsize=(22, 5.2))

    # 子图1：PM2.5 超标面积×天数（1月）
    month_pm = emission_months.get('PM2.5', '')
    draw_bar_subplot(
        axes[0],
        emission_results['PM2.5'],
        title=f"PM2.5≥75μg/m³ 超标面积×天数（{month_pm}）",
        ylabel=r'面积×天数 (km$^2$·day)',
    )

    # 子图2：O3 超标面积×天数（7月）
    month_o3 = emission_months.get('O3', '')
    # 关键修改2：这里标题会直接使用 EMISSION_VARIABLES['O3']['title_cn'] 的值（已改为O3）
    draw_bar_subplot(
        axes[1],
        emission_results['O3'],
        title=f"O3≥80ppb 超标面积×天数（{month_o3}）",  # 也可以直接用 var_cfg['title_cn'] 保持统一
        ylabel=r'面积×天数 (km$^2$·day)',
    )

    # 子图3：热浪面积×天数（7月）
    draw_bar_subplot(
        axes[2],
        mcipout_series,
        title="陆地热浪面积×天数（7月）",
        ylabel=r'面积×天数 (km$^2$·day)',
    )

    # 共用图例（底部居中）
    legend_handles = [
        Patch(facecolor=Case_COLORS[c], edgecolor='black', label=c)
        for c in CaseS
    ]
    fig.legend(
        handles=legend_handles,
        loc='lower center',
        ncol=len(CaseS),
        fontsize=18,
        frameon=False,
        bbox_to_anchor=(0.5, -0.02),
        handlelength=3.0,
        handleheight=1.0,
        handletextpad=0.8,
        columnspacing=3.0,
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.14, wspace=0.22)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = OUTPUT_DIR / "Combined_AreaDays_Case1_3.png"
    plt.savefig(out, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✅ Saved: {out}")


# ============================
# Main
# ============================
def main():
    print("=" * 80)
    print("   Combined Area-Days Bar Charts — Case1 vs Case3")
    print("=" * 80)

    for dir_path in [EMISSION_DATA_DIR, MCIPOUT_DATA_DIR]:
        status = "✅" if dir_path.exists() else "❌"
        print(f"  {status} {dir_path}")

    emission_results, emission_months, mcipout_series = prepare_all_data()
    plot_combined(emission_results, emission_months, mcipout_series)

    print(f"\n🎉 Done! Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
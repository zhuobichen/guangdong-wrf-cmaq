#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Boxplot Comparison Script - Using Case labels with emission-met pairing
Modified to handle different emission/met year combinations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re
from pathlib import Path
import matplotlib.font_manager as font_manager

# Set font - 添加中文字体支持
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display issue
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['text.usetex'] = False  # Disable LaTeX rendering

# ============================
# Configuration Parameters
# ============================
# CASE映射配置（从差值地图代码复制）
CASE_DEFINITIONS = {
    # CASE: (Emission, met, 描述)
    'CASE1': ('2000', '2000', '2000e2000m'),
    'CASE2': ('2000', '2023', '2000e2023m'),
    'CASE3': ('2023', '2023', '2023e2023m'),
    'CASE4': ('2023', '2000', '2023e2000m'),
    'CASE5': ('2060', '2060', '2060e2060m'),
    'CASE6': ('2030', '2030', '2030e2030m'),
}

CASE_MAPPING = {
    # 反向映射：从排放-气象组合到CASE
    '2000e2000m': 'CASE1',
    '2000e2023m': 'CASE2', 
    '2023e2023m': 'CASE3',
    '2023e2000m': 'CASE4',
    '2060e2060m': 'CASE5',
    '2030e2030m': 'CASE6',
}

# Case display order - 可以根据需要修改要显示的CASE
CASES = ['CASE2', 'CASE3', 'CASE5', 'CASE6']
# 如果想画其他CASE，比如：
# CASES = ['CASE2', 'CASE3', 'CASE5', 'CASE6']

# Month mapping - 修改为中文月份
MONTH_MAPPING = {
    '01': '1月',
    '02': '2月',
    '03': '3月',
    '04': '4月',
    '05': '5月',
    '06': '6月',
    '07': '7月',
    '08': '8月',
    '09': '9月',
    '10': '10月',
    '11': '11月',
    '12': '12月'
}

# Region configuration - 使用统一的数据目录，不按年份区分
REGIONS = {
    'GuangDong': {
        'name': 'GuangDong',
        'data_dir': Path("/data/workspace/GuangDong/cmaqout_processed"),
        'file_suffix': '',
        'color': '#1f77b4',      # Blue
        'box_color': '#aec7e8'   # Light blue
    },
    'HuiZhou': {
        'name': 'HuiZhou',
        'data_dir': Path("/data/workspace/GuangDong/cmaqout_processed_HuiZhou"),
        'file_suffix': '_HuiZhou',
        'color': '#ff7f0e',      # Orange
        'box_color': '#ffbb78'   # Light orange
    }
}

# Output directory
BASE_DIR = Path("/data/workspace/GuangDong")
OUTPUT_DIR = BASE_DIR / "Emission_Comparison_BoxPlots"

# ============================
# Variable Configuration
# ============================
VARIABLES = {
    'O3': {
        'column': 'O3',
        'unit': 'ppb',
        'title': 'O3',
        'ylabel': 'O3 (ppb)',
        'month_code': '07'
    },
    'PM2.5': {
        'column': 'PM2.5',
        'unit': 'μg/m³',
        'title': 'PM2.5',
        'ylabel': 'PM2.5 (μg/m³)',
        'month_code': '01'
    },
    'O3_Days': {
        'column': 'O3_Days',
        'unit': 'days',
        'title': 'O3超标天',
        'ylabel': 'O3≥80ppb Days (days)',
        'month_code': '07'
    },
    'PM2.5_Days': {
        'column': 'PM2.5_Days',
        'unit': 'days',
        'title': 'PM2.5超标天',
        'ylabel': 'PM2.5≥75μg/m³ Days (days)',
        'month_code': '01'
    }
}

# ============================
# Helper Functions (from difference map code)
# ============================
def get_case_from_filename(filename):
    """从文件名中提取CASE信息"""
    match = re.search(r'(\d{4})_Emission\[(\d{4})met\]', filename)
    if match:
        emission = match.group(1)
        met = match.group(2)
        case_key = f"{emission}e{met}m"
        return CASE_MAPPING.get(case_key, case_key)
    return None

def get_case_number(case_str):
    """从CASE字符串中提取数字"""
    match = re.search(r'CASE(\d+)', case_str)
    if match:
        return match.group(1)
    return case_str

# ============================
# Data Loading Function
# ============================
def load_data_for_case(region_key, case_id, var_name):
    """Load data for specified region, case, and variable using emission-met pairing"""
    region_config = REGIONS[region_key]
    data_dir = region_config['data_dir']
    file_suffix = region_config.get('file_suffix', '')
    
    # 获取CASE对应的排放年和气象年
    if case_id not in CASE_DEFINITIONS:
        raise ValueError(f"Unknown case: {case_id}")
    emission_year, met_year, case_key = CASE_DEFINITIONS[case_id]
    
    # Get month code for variable
    month_code = VARIABLES[var_name]['month_code']
    month_name = MONTH_MAPPING.get(month_code, f"{month_code}月")
    
    # 构建文件名模式（与差值地图中的模式一致）
    patterns = [
        f"{emission_year}_Emission[{met_year}met]_{month_code}{file_suffix}.csv",
        f"{emission_year}_Emission_{met_year}met_{month_code}{file_suffix}.csv",
        f"Emission[{met_year}met]_{month_code}{file_suffix}.csv",
        f"{case_key}_{month_code}{file_suffix}.csv",
        f"{case_id}_{month_code}{file_suffix}.csv",
        # Fallback patterns
        f"{emission_year}_Emission[{met_year}met]_{month_code}.csv",
        f"{emission_year}_Emission_{met_year}met_{month_code}.csv",
        f"Emission[{met_year}met]_{month_code}.csv",
        f"{case_key}_{month_code}.csv",
        f"{case_id}_{month_code}.csv"
    ]
    
    file_path = None
    found = False
    for pattern in patterns:
        test_path = data_dir / pattern
        if test_path.exists():
            file_path = test_path
            found = True
            break
    
    if not found:
        # 尝试扫描目录中匹配该CASE的文件
        print(f"    ⚠️  直接匹配失败，扫描目录寻找{case_key}相关文件...")
        for file in data_dir.glob(f"*{month_code}{file_suffix}.csv"):
            if case_key in str(file) or case_id in str(file) or \
               f"{emission_year}e{met_year}m" in str(file) or \
               f"{emission_year}_Emission[{met_year}met]" in str(file):
                file_path = file
                found = True
                break
    
    if not found:
        raise FileNotFoundError(f"Data file not found for {case_id} ({case_key})\n"
                               f"Emission: {emission_year}, Met: {met_year}, Month: {month_code}\n"
                               f"Tried patterns: {', '.join(patterns)}")
    
    print(f"    Loading {month_name} data from: {file_path.name} (Case: {case_id}, {case_key})")
    
    df = pd.read_csv(file_path)
    
    # Check if required column exists
    var_config = VARIABLES[var_name]
    required_col = var_config['column']
    if required_col not in df.columns:
        raise ValueError(f"Column '{required_col}' not found in file {file_path}")
    
    return df[required_col].dropna().values, month_name, case_id

# ============================
# Data Preparation Function
# ============================
def prepare_data_for_plotting():
    """Prepare data for plotting"""
    plot_data = {}
    case_info = {}
    
    for var_name, var_config in VARIABLES.items():
        print(f"\n📊 Processing variable: {var_config['title']}")
        var_data = {}
        var_cases = {}
        
        for region_key, region_config in REGIONS.items():
            print(f"  Region: {region_config['name']}")
            region_data = {}
            region_cases = {}
            
            for case_id in CASES:
                try:
                    data, month_name, case_label = load_data_for_case(region_key, case_id, var_name)
                    region_data[case_id] = data
                    region_cases[case_id] = case_label
                    var_cases[case_id] = case_label  # Save case label for this variable
                    print(f"    ✅ {case_id} {month_name} data: length={len(data)}, mean={np.mean(data):.2f}")
                except Exception as e:
                    print(f"    ❌ {case_id} data load failed: {str(e)}")
                    region_data[case_id] = np.array([])
                    region_cases[case_id] = case_id  # Keep case ID as fallback
            
            var_data[region_key] = region_data
        
        plot_data[var_name] = var_data
        case_info[var_name] = var_cases
    
    return plot_data, case_info

# ============================
# Boxplot Plotting Function
# ============================
def plot_combined_boxplot(var_name, plot_data, case_info):
    """Plot combined boxplot with both regions side by side for each case"""
    var_config = VARIABLES[var_name]
    month_code = var_config['month_code']
    month_name = MONTH_MAPPING.get(month_code, f"{month_code}月")
    
    print(f"\n📈 Plotting {month_name} {var_config['title']} - Combined boxplot with Case labels")
    
    # Prepare data for plotting
    all_data = []
    labels = []
    positions = []
    colors = []
    box_colors = []
    
    # Set up positions (each case has two boxes: GuangDong and HuiZhou)
    pos = 1
    case_positions = []  # 存储每个Case的中心位置
    for case_id in CASES:
        case_label = case_info[var_name].get(case_id, case_id)
        case_center = pos + 0.15  # Case标签放在两个箱型的中间
        case_positions.append((case_label, case_center))
        
        # GuangDong data
        gd_data = plot_data[var_name]['GuangDong'].get(case_id, [])
        if len(gd_data) > 0:
            all_data.append(gd_data)
            labels.append('')  # 箱型下方不显示标签
            positions.append(pos)
            colors.append(REGIONS['GuangDong']['color'])
            box_colors.append(REGIONS['GuangDong']['box_color'])
        
        # HuiZhou data
        hz_data = plot_data[var_name]['HuiZhou'].get(case_id, [])
        if len(hz_data) > 0:
            all_data.append(hz_data)
            labels.append('')  # 箱型下方不显示标签
            positions.append(pos + 0.3)
            colors.append(REGIONS['HuiZhou']['color'])
            box_colors.append(REGIONS['HuiZhou']['box_color'])
        
        pos += 1.5  # Space between cases
    
    if not all_data:
        print("  ❌ No valid data for plotting")
        return
    
    # Create figure
    plt.figure(figsize=(16, 8))
    
    # Create boxplot
    bp = plt.boxplot(
        all_data,
        positions=positions,
        labels=labels,
        patch_artist=True,
        widths=0.3,
        showfliers=True,
        flierprops={
            'marker': 'o',
            'markerfacecolor': 'red',
            'markeredgecolor': 'black',
            'markersize': 6,
            'alpha': 0.7
        },
        medianprops={
            'color': 'black',
            'linewidth': 2
        },
        boxprops={
            'linewidth': 1.2
        },
        whiskerprops={
            'linewidth': 1.2
        },
        capprops={
            'linewidth': 1.2
        }
    )
    
    # Set box colors
    for i, box in enumerate(bp['boxes']):
        box.set(facecolor=box_colors[i], alpha=0.8)
    
    # 动态生成CASE列表标题
    case_list_str = ', '.join(CASES)
    plt.title(f'{month_name} {var_config["title"]} ({case_list_str})',
              fontsize=18, fontweight='bold', pad=20)
    plt.ylabel(var_config['ylabel'], fontsize=14, fontweight='bold')
    
    # 手动添加Case标签（仅显示CASE名称，fontsize=16）
    y_offset = -0.15 if var_name.endswith('_Days') else -0.3
    for case_label, case_center in case_positions:
        plt.text(case_center, y_offset,
                case_label,
                transform=plt.gca().transData,
                ha='center', va='top',
                fontsize=16, fontweight='bold')
    
    # Set y-axis limits
    if var_name in ['O3', 'PM2.5', 'O3_Days', 'PM2.5_Days']:
        all_values = []
        for data in all_data:
            all_values.extend(data)
        if all_values:
            plt.ylim(0, max(all_values) * 1.15)
    
    # Add grid
    plt.grid(True, alpha=0.3, axis='y')
    plt.gca().set_facecolor('#f8f9fa')
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=REGIONS['GuangDong']['box_color'], edgecolor='black',
              label='GuangDong'),
        Patch(facecolor=REGIONS['HuiZhou']['box_color'], edgecolor='black',
              label='HuiZhou')
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=12)
    
    # 生成动态的文件名
    case_filename_str = '-'.join(CASES)
    month_pinyin = {
        '01': 'January', '02': 'February', '03': 'March', '04': 'April',
        '05': 'May', '06': 'June', '07': 'July', '08': 'August',
        '09': 'September', '10': 'October', '11': 'November', '12': 'December'
    }.get(month_code, f"Month{month_code}")
    output_file = OUTPUT_DIR / f"{var_name}_{month_pinyin}_{case_filename_str}_Boxplot.png"
    
    # Save figure
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ {month_name} {var_config['title']} boxplot saved: {output_file}")

# ============================
# Main Function
# ============================
def main():
    print("=" * 80)
    print("         Boxplot Analysis - Cases with Emission-Met Pairing")
    print("=" * 80)
    
    # 显示当前配置的CASE列表
    print(f"\n📋 当前配置的CASE列表: {', '.join(CASES)}")
    print(f"\n📋 CASE详细配置:")
    for case_id in CASES:
        if case_id in CASE_DEFINITIONS:
            emission, met, desc = CASE_DEFINITIONS[case_id]
            print(f"  {case_id}: {desc} = {emission}排放 + {met}气象")
    
    # Check data directories
    for region_key, region_config in REGIONS.items():
        print(f"\n🔍 Checking {region_config['name']} data directory:")
        data_dir = region_config['data_dir']
        if data_dir.exists():
            print(f"  ✅ {data_dir}")
            # 列出目录中的CSV文件
            csv_files = list(data_dir.glob("*.csv"))
            print(f"  📁 目录中有 {len(csv_files)} 个CSV文件")
            # 显示前5个文件
            for i, file in enumerate(csv_files[:5]):
                case = get_case_from_filename(str(file))
                print(f"     - {file.name} -> {case}")
        else:
            print(f"  ❌ {data_dir} (directory not found)")
    
    # Prepare data
    plot_data, case_info = prepare_data_for_plotting()
    
    # Plot combined boxplots for each variable
    for var_name, var_config in VARIABLES.items():
        if var_name in plot_data:
            plot_combined_boxplot(var_name, plot_data, case_info)
        else:
            print(f"❌ {var_name} has no data, skipping")
    
    print("\n🎉 All boxplots generated successfully!")
    print(f"📁 Output directory: {OUTPUT_DIR}")

# ============================
# Execution Entry
# ============================
if __name__ == "__main__":
    main()
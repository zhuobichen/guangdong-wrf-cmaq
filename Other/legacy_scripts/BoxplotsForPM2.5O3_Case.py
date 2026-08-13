#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Boxplot Comparison Script - Case1 to Case4
Modified from BoxplotsForPM2.5O3.py to support Case comparison
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path
import matplotlib.font_manager as font_manager
import re

# Set font
plt.rcParams["font.family"] = ["serif", "Times New Roman", "DejaVu Serif"]
plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display issue
plt.rcParams['text.usetex'] = False  # Disable LaTeX rendering

# ============================
# CASE Configuration
# ============================
# CASE definitions
CASE_DEFINITIONS = {
    'CASE1': ('2000', '2000', '2000e2000m'),  # 2000排放+2000气象
    'CASE2': ('2000', '2023', '2000e2023m'),  # 2000排放+2023气象
    'CASE3': ('2023', '2023', '2023e2023m'),  # 2023排放+2023气象
    'CASE4': ('2023', '2000', '2023e2000m'),  # 2023排放+2000气象
    'CASE5': ('2060', '2060', '2060e2060m'),  # 2060排放+2060气象
    'CASE6': ('2030', '2030', '2030e2030m'),  # 2030排放+2030气象
}
# Default CASEs to compare
# CASES = ['CASE1', 'CASE3', 'CASE5', 'CASE6']
CASES = ['CASE1', 'CASE2', 'CASE3', 'CASE4']

# Month mapping
MONTH_MAPPING = {
    '01': 'January',
    '02': 'February', 
    '03': 'March',
    '04': 'April',
    '05': 'May',
    '06': 'June',
    '07': 'July',
    '08': 'August',
    '09': 'September',
    '10': 'October',
    '11': 'November',
    '12': 'December'
}

# Variable month configuration
VARIABLE_MONTHS = {
    'O3': '07',      # O3 uses July data
    'PM2.5': '01'    # PM2.5 uses January data
}

# Region configuration
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

# Whether to include HuiZhou in loading & plotting
INCLUDE_HUIZHOU = False  # 设置为 False 时不读取/绘制惠州


def get_enabled_region_keys():
    """Return list of region keys that are enabled for analysis/plotting."""
    keys = ['GuangDong']  # 始终包含广东
    if INCLUDE_HUIZHOU and 'HuiZhou' in REGIONS:
        keys.append('HuiZhou')
    return keys

# Output directory
BASE_DIR = Path("/data/workspace/GuangDong")
OUTPUT_DIR = BASE_DIR / "Boxplots_Output_CaseComparison"

# ============================
# Variable Configuration
# ============================
VARIABLES = {
    'O3': {
        'column': 'O3',
        'unit': 'ppb',
        'title': 'O₃ ',
        'ylabel': 'O₃ (ppb)',
        'month_code': '07'
    },
    'PM2.5': {
        'column': 'PM2.5',
        'unit': 'μg/m³',
        'title': 'PM2.5 ',
        'ylabel': 'PM2.5 (μg/m³)',
        'month_code': '01'
    }
}

# ============================
# CASE Helper Functions
# ============================
def get_case_filename_pattern(case_id, month_code, file_suffix=''):
    """Generate filename patterns for a given CASE"""
    if case_id not in CASE_DEFINITIONS:
        raise ValueError(f"Unknown CASE: {case_id}")
    
    emission_year, met_year, case_key = CASE_DEFINITIONS[case_id]
    
    patterns = [
        f"{emission_year}_Emission[{met_year}met]_{month_code}{file_suffix}.csv",
        f"{case_key}_{month_code}{file_suffix}.csv",
        f"{case_id}_{month_code}{file_suffix}.csv",
        f"{emission_year}e{met_year}m_{month_code}{file_suffix}.csv",
        # Fallback patterns
        f"{emission_year}_Emission_{month_code}{file_suffix}.csv",
        f"{met_year}_Emission_{month_code}{file_suffix}.csv"
    ]
    
    return patterns

def find_case_file(case_id, month_code, data_dir, file_suffix=''):
    """Find file for a given CASE"""
    patterns = get_case_filename_pattern(case_id, month_code, file_suffix)
    
    for pattern in patterns:
        file_path = data_dir / pattern
        if file_path.exists():
            return file_path
    
    # Try without suffix as last resort
    patterns_without_suffix = get_case_filename_pattern(case_id, month_code)
    for pattern in patterns_without_suffix:
        file_path = data_dir / pattern
        if file_path.exists():
            return file_path
    
    return None

# ============================
# Data Loading Function
# ============================
def load_data(region_key, case_id, var_name):
    """Load data for specified region, CASE, and variable"""
    region_config = REGIONS[region_key]
    data_dir = region_config['data_dir']
    file_suffix = region_config.get('file_suffix', '')
    
    # Get month code for the variable
    month_code = VARIABLES[var_name]['month_code']
    
    # Find the file for this CASE
    file_path = find_case_file(case_id, month_code, data_dir, file_suffix)
    
    if not file_path or not file_path.exists():
        raise FileNotFoundError(f"Data file not found for CASE {case_id} (month {month_code}) in {data_dir}")

    # Extract month from filename for verification
    month_str = month_code
    month_name = MONTH_MAPPING.get(month_str, f"Month {month_str}")
    
    print(f"    Loading {month_name} data from: {file_path.name}")
    
    df = pd.read_csv(file_path)

    # Check if required column exists
    var_config = VARIABLES[var_name]
    required_col = var_config['column']
    if required_col not in df.columns:
        raise ValueError(f"Column '{required_col}' not found in file {file_path}")

    return df[required_col].dropna().values, month_name

# ============================
# Data Preparation Function
# ============================
def prepare_data_for_plotting():
    """Prepare data for plotting"""
    plot_data = {}
    month_info = {}

    for var_name, var_config in VARIABLES.items():
        print(f"\n📊 Processing variable: {var_config['title']}")
        var_data = {}
        var_month = None
        
        for region_key in get_enabled_region_keys():
            region_config = REGIONS[region_key]
            print(f"  Region: {region_config['name']}")
            region_data = {}
            
            for case_id in CASES:
                try:
                    data, month_name = load_data(region_key, case_id, var_name)
                    region_data[case_id] = data
                    var_month = month_name  # Save month name for this variable
                    print(f"    ✅ {case_id} {month_name} data: length={len(data)}, mean={np.mean(data):.2f}")
                except Exception as e:
                    print(f"    ❌ {case_id} data load failed: {str(e)}")
                    region_data[case_id] = np.array([])
            
            var_data[region_key] = region_data
        
        plot_data[var_name] = var_data
        month_info[var_name] = var_month

    return plot_data, month_info

# ============================
# Boxplot Plotting Function
# ============================
def plot_combined_boxplot(var_name, plot_data, month_info):
    """Plot combined boxplot with both regions side by side for each CASE"""
    var_config = VARIABLES[var_name]
    month_name = month_info.get(var_name, "Unknown Month")

    print(f"\n📈 Plotting {var_config['title']} ({month_name}) - Combined boxplot")

    # Prepare data for plotting
    all_data = []
    labels = []
    positions = []
    colors = []
    box_colors = []
    
    # Set up positions (each CASE has 1 or more boxes: regions side by side)
    pos = 1
    enabled_regions = get_enabled_region_keys()
    for case_id in CASES:
        # for each CASE, put enabled regions side by side
        offset_idx = 0
        for region_key in enabled_regions:
            region_cfg = REGIONS[region_key]
            region_plot_data = plot_data[var_name][region_key].get(case_id, [])
            if len(region_plot_data) > 0:
                all_data.append(region_plot_data)
                labels.append(f'{case_id}\n{region_cfg["name"]}')
                positions.append(pos + 0.3 * offset_idx)
                colors.append(region_cfg['color'])
                box_colors.append(region_cfg['box_color'])
                offset_idx += 1

        pos += 1.5  # Space between CASEs

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
    
    # Set title with CASE information
    # plt.title(f'{var_config["title"]} Comparison ({month_name}) (Case1, Case2, Case3, Case4)', 
    plt.title(f'{var_config["title"]} Comparison ({month_name}) (Case1, Case3, Case5, Case6 )', 
              fontsize=18, fontweight='bold', pad=20)
    plt.ylabel(var_config['ylabel'], fontsize=14, fontweight='bold')
    plt.xlabel('Case and Region', fontsize=14, fontweight='bold')
    
    # Set y-axis limits
    if 'O3' in var_name or 'PM2.5' in var_name:
        all_values = []
        for data in all_data:
            all_values.extend(data)
        if all_values:
            plt.ylim(0, max(all_values) * 1.1)
    
    # Add grid
    plt.grid(True, alpha=0.3, axis='y')
    plt.gca().set_facecolor('#f8f9fa')
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = []
    for region_key in get_enabled_region_keys():
        region_cfg = REGIONS[region_key]
        legend_elements.append(
            Patch(
                facecolor=region_cfg['box_color'],
                edgecolor='black',
                label=region_cfg['name']
            )
        )
    plt.legend(handles=legend_elements, loc='upper right', fontsize=12)
    
    # Save figure with CASE in filename
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    month_code = VARIABLES[var_name]['month_code']
    output_file = OUTPUT_DIR / f"{var_name}_CaseComparison_{month_name}.png"

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"✅ {var_config['title']} ({month_name}) boxplot saved: {output_file}")

    # Generate statistics table
    generate_statistics_table(var_name, plot_data, month_name)

def generate_statistics_table(var_name, plot_data, month_name):
    """Generate detailed statistics table"""
    var_config = VARIABLES[var_name]
    stats_data = []
    
    for case_id in CASES:
        for region_key in get_enabled_region_keys():
            region_config = REGIONS[region_key]
            region_data = plot_data[var_name][region_key]
            
            if case_id in region_data and len(region_data[case_id]) > 0:
                data = region_data[case_id]
                stats = {
                    'Case': case_id,
                    'Description': CASE_DEFINITIONS[case_id][2],
                    'Month': month_name,
                    'Region': region_config['name'],
                    'Sample Size': len(data),
                    'Min': f"{np.min(data):.2f}",
                    'Max': f"{np.max(data):.2f}",
                    'Mean': f"{np.mean(data):.2f}",
                    'Median': f"{np.median(data):.2f}",
                    'Std': f"{np.std(data):.2f}"
                }
                stats_data.append(stats)
            else:
                stats = {
                    'Case': case_id,
                    'Description': CASE_DEFINITIONS[case_id][2],
                    'Month': month_name,
                    'Region': region_config['name'],
                    'Sample Size': 0,
                    'Min': 'N/A',
                    'Max': 'N/A',
                    'Mean': 'N/A',
                    'Median': 'N/A',
                    'Std': 'N/A'
                }
                stats_data.append(stats)
    
    stats_df = pd.DataFrame(stats_data)
    print(f"\n📊 {var_config['title']} ({month_name}) Detailed Statistics:")
    print(stats_df.to_string(index=False))
    
    # Save statistics table with CASE in filename
    month_code = VARIABLES[var_name]['month_code']
    stats_file = OUTPUT_DIR / f"{var_name}_CaseComparison_{month_name}_statistics.csv"
    stats_df.to_csv(stats_file, index=False, encoding='utf-8-sig')
    print(f"📄 Statistics table saved: {stats_file}")

# ============================
# Main Function
# ============================
def main():
    print("=" * 80)
    print("         Boxplot Comparison Analysis - Case1, Case2, Case3, Case4")
    print("=" * 80)

    # Show CASE definitions
    print("\n📋 CASE Definitions:")
    for case_id, (emission, met, desc) in CASE_DEFINITIONS.items():
        print(f"  {case_id}: {desc} (排放{emission}, 气象{met})")

    # Check data directories
    for region_key in get_enabled_region_keys():
        region_config = REGIONS[region_key]
        print(f"\n🔍 Checking {region_config['name']} data directory:")
        if region_config['data_dir'].exists():
            print(f"  ✅ {region_config['data_dir']}")
        else:
            print(f"  ❌ {region_config['data_dir']} (directory not found)")

    # Prepare data
    plot_data, month_info = prepare_data_for_plotting()

    # Plot combined boxplots for each variable
    for var_name, var_config in VARIABLES.items():
        if var_name in plot_data:
            plot_combined_boxplot(var_name, plot_data, month_info)
        else:
            print(f"❌ {var_name} has no data, skipping")

    print("\n🎉 All boxplots generated successfully!")
    print(f"📁 Output directory: {OUTPUT_DIR}")

# ============================
# Execution Entry
# ============================
if __name__ == "__main__":
    main()
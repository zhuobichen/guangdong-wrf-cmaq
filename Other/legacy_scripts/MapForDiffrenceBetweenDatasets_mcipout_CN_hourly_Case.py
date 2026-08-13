#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from esil.rsm_helper.model_property import model_attribute
from esil.map_helper import get_multiple_data, show_maps
import cmaps
import re

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# 基础配置
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
cmap_delta = cmaps.ViBlGrWhYeOrRe

# Case 定义（与 emission/mcipout 系列脚本保持一致）
CASE_DEFINITIONS = {
    'Case1': {'year': '2000', 'label': 'Case1'},
    'Case3': {'year': '2023', 'label': 'Case3'},
}

# === 气象变量配置 ===
VARIABLE_CONFIGS = {
    'TA_mean': {
        'display_name': 'TEMP',
        'column_name': 'TA_mean',
        'unit': '°C',
        'file_pattern': 'mcipout',
        'stats_type': 'Mean',
        'legend_range': (-5, 5),
        'colorbar_format': '.1f',
        'show_domain_stat': True
    },
    'TA_max': {
        'display_name': 'TEMP_Max',
        'column_name': 'TA_max',
        'unit': '°C',
        'file_pattern': 'mcipout',
        'stats_type': 'Max',
        'legend_range': (-5, 5),
        'colorbar_format': '.1f',
        'show_domain_stat': True
    },
    'SOL_RAD': {
        'display_name': 'SOL_RAD',
        'column_name': 'SOL_RAD_mean',
        'unit': 'W/m²',
        'file_pattern': 'mcipout',
        'stats_type': 'Mean',
        'legend_range': (None, None),
        'colorbar_format': '.0f',
        'show_domain_stat': True
    },
    'SOL_RAD_max': {
        'display_name': 'SOL_RAD_Max',
        'column_name': 'SOL_RAD_max',
        'unit': 'W/m²',
        'file_pattern': 'mcipout',
        'stats_type': 'Max',
        'legend_range': (None, None),
        'colorbar_format': '.0f',
        'show_domain_stat': True
    },
    'PBLH': {
        'display_name': 'PBLH',
        'column_name': 'PBLH_mean',
        'unit': 'm',
        'file_pattern': 'mcipout',
        'stats_type': 'Mean',
        'legend_range': (None, None),
        'colorbar_format': '.0f',
        'show_domain_stat': True
    },
    'PBLH_max': {
        'display_name': 'PBLH_Max',
        'column_name': 'PBLH_max',
        'unit': 'm',
        'file_pattern': 'mcipout',
        'stats_type': 'Max',
        'legend_range': (None, None),
        'colorbar_format': '.0f',
        'show_domain_stat': True
    },
    'TA_mean_month': {
        'display_name': 'TA Mean Month',
        'column_name': 'TA_mean_month',
        'unit': '°C',
        'file_pattern': 'mcipout',
        'stats_type': 'Mean',
        'legend_range': (None, None),
        'colorbar_format': '.0f',
        'show_domain_stat': True
    },
    'Heatwave_Days': {
        'display_name': 'Heatwave Days (≥35°C)',
        'column_name': 'Heatwave_Days_Coverage',
        'unit': 'Days',
        'file_pattern': 'mcipout',
        'stats_type': 'Max',
        'legend_range': (-10, 10),
        'colorbar_format': '.2f',
        'show_domain_stat': True
    }
}

# === 数据对比配置（Case1 - Case3，即 2000 - 2023，hourly 数据目录）===
COMPARISON_CONFIGS = [
    [
        '/data/workspace/GuangDong/mcipout_processed_hourly/2000_mcipout_07.csv',
        '/data/workspace/GuangDong/mcipout_processed_hourly/2023_mcipout_07.csv',
        'Case1', 'Case3',
        'Case1_minus_Case3'
    ],
]


def extract_month_from_filename(filename):
    """从文件名中提取月份"""
    match = re.search(r'_(\d{2})(?:\.\w+$|$)', filename)
    if match:
        month_num = int(match.group(1))
        if 1 <= month_num <= 12:
            return month_num
    return None


def get_variable_info(var_name):
    if var_name not in VARIABLE_CONFIGS:
        raise ValueError(f"未配置变量: {var_name}")
    return VARIABLE_CONFIGS[var_name]


def generate_plot_title(var_config, case1_label, case2_label, month=7):
    """生成标题：7月 Heatwave Days (Coverage, ≥35°C): Case1 - Case3"""
    month_names_cn = {
        1: '1月', 2: '2月', 3: '3月', 4: '4月',
        5: '5月', 6: '6月', 7: '7月', 8: '8月',
        9: '9月', 10: '10月', 11: '11月', 12: '12月'
    }
    month_name = month_names_cn.get(month, f'{month}月')
    display_name = var_config['display_name']
    return f"{month_name} {display_name}: {case1_label} - {case2_label}"


def generate_output_filename(var_config, output_suffix, month=7):
    """生成输出文件名"""
    base_var_name = var_config['column_name'].replace('_mean', '').replace('_max', '')
    if var_config['stats_type'] == 'Max':
        display_name = f"{base_var_name}_Max"
    else:
        display_name = base_var_name
    month_str = f"{month:02d}"
    filename = f"{display_name}_{output_suffix}_{month_str}.png"
    return filename


def plot_difference_map(data1, data2, var_config, file_config, model_file,
                        save_dir, boundary_json_file, month=7):
    """绘制气象变量差值地图"""
    print(f"开始绘制差值地图...")

    try:
        mp = model_attribute(model_file)
        proj, longitudes, latitudes = mp.projection, mp.lons, mp.lats
        grid_shape = longitudes.shape
        print(f"模型网格信息: {grid_shape}")
    except Exception as e:
        print(f"加载模型信息失败: {str(e)}")
        return None

    column_name = var_config['column_name']

    # 对 Heatwave_Days_Coverage 做兼容回退
    if column_name not in data1.columns or column_name not in data2.columns:
        if column_name == 'Heatwave_Days_Coverage' and \
                'Heatwave_Days' in data1.columns and 'Heatwave_Days' in data2.columns:
            print("⚠️  CSV中未找到 Heatwave_Days_Coverage，回退使用旧列 Heatwave_Days。")
            print("   建议重新运行小时热浪提取脚本以生成 Heatwave_Days_Coverage 列。")
            column_name = 'Heatwave_Days'
        else:
            print(f"错误: 数据中缺少 {column_name} 列")
            print(f"可用列 - 数据1: {list(data1.columns)}")
            print(f"可用列 - 数据2: {list(data2.columns)}")
            return None

    expected_size = grid_shape[0] * grid_shape[1]
    if len(data1) != expected_size or len(data2) != expected_size:
        print(f"数据长度不匹配: 数据1={len(data1)}, 数据2={len(data2)}, 网格={expected_size}")
        min_len = min(len(data1), len(data2), expected_size)
        data1 = data1.iloc[:min_len]
        data2 = data2.iloc[:min_len]
        grid_shape = (int(np.sqrt(min_len)), int(np.sqrt(min_len)))
        print(f"调整后的数据长度: {min_len}, 网格: {grid_shape}")

    try:
        data1_sorted = data1.sort_values(by=['ROW', 'COL'])
        data2_sorted = data2.sort_values(by=['ROW', 'COL'])

        var1 = data1_sorted[column_name].values.reshape(grid_shape)
        var2 = data2_sorted[column_name].values.reshape(grid_shape)

        diff = var1 - var2

        # Case 标识
        case1_id = file_config[2]
        case2_id = file_config[3]
        case1_label = CASE_DEFINITIONS.get(case1_id, {}).get('label', case1_id)
        case2_label = CASE_DEFINITIONS.get(case2_id, {}).get('label', case2_id)
        calculation_desc = f"{case1_label} - {case2_label}"

        print(f"差值计算: {calculation_desc}")
        print(f"差值统计: min={diff.min():.3f}, max={diff.max():.3f}, mean={diff.mean():.3f}")

        if var_config['legend_range'] == (None, None):
            vmin = np.nanpercentile(diff, 0.5)
            vmax = np.nanpercentile(diff, 99.5)
            var_config['legend_range'] = (vmin, vmax)
            print(f"自动计算图例范围（0.5%-99.5%分位数）：{vmin:.3f} ~ {vmax:.3f} {var_config['unit']}")
        else:
            print(f"使用手动指定图例范围：{var_config['legend_range'][0]} ~ {var_config['legend_range'][1]} {var_config['unit']}")
    except Exception as e:
        print(f"数据重塑失败: {str(e)}")
        return None

    output_suffix = file_config[4]
    plot_title = generate_plot_title(var_config, case1_label, case2_label, month)
    output_filename = generate_output_filename(var_config, output_suffix, month)

    plot_data = {}
    get_multiple_data(
        plot_data,
        dataset_name=plot_title,
        variable_name="",
        grid_x=longitudes,
        grid_y=latitudes,
        grid_concentration=diff,
        is_delta=True,
        cmap=cmap_delta
    )

    plot_settings = {
        'unit': var_config['unit'],
        'cmap': cmap_delta,
        'show_lonlat': True,
        'projection': proj,
        'is_wrf_out_data': True,
        'boundary_file': boundary_json_file,
        'show_original_grid': True,
        'delta_map_settings': {
            "cmap": cmap_delta,
            "value_range": var_config['legend_range'],
            "colorbar_ticks_value_format": var_config['colorbar_format'],
            "value_format": var_config['colorbar_format']
        },
        'title_fontsize': 14,
        'xy_title_fontsize': 12,
        'show_dependenct_colorbar': True,
        'show_domain_mean': var_config['show_domain_stat'],
        'show_domain_max': var_config['show_domain_stat']
    }

    try:
        fig = show_maps(
            plot_data,
            unit=plot_settings['unit'],
            cmap=plot_settings['cmap'],
            show_lonlat=plot_settings['show_lonlat'],
            projection=plot_settings['projection'],
            is_wrf_out_data=plot_settings['is_wrf_out_data'],
            boundary_file=plot_settings['boundary_file'],
            show_original_grid=plot_settings['show_original_grid'],
            delta_map_settings=plot_settings['delta_map_settings'],
            title_fontsize=plot_settings['title_fontsize'],
            xy_title_fontsize=plot_settings['xy_title_fontsize'],
            show_dependenct_colorbar=plot_settings['show_dependenct_colorbar'],
            show_domain_mean=plot_settings['show_domain_mean'],
            show_domain_max=plot_settings['show_domain_max']
        )

        os.makedirs(save_dir, exist_ok=True)
        save_file = os.path.join(save_dir, output_filename)

        fig.savefig(save_file, dpi=300, bbox_inches="tight")
        print(f"✅ 图像已保存至: {save_file}")
        plt.close(fig)

        return save_file

    except Exception as e:
        print(f"❌ 绘图时出错: {str(e)}")
        return None


def process_file_comparison(file_config, var_name, model_file, boundary_file, save_dir, month=None):
    """处理单个文件对比"""
    file1 = file_config[0]
    file2 = file_config[1]
    case1_id = file_config[2]
    case2_id = file_config[3]
    output_suffix = file_config[4]

    case1_label = CASE_DEFINITIONS.get(case1_id, {}).get('label', case1_id)
    case2_label = CASE_DEFINITIONS.get(case2_id, {}).get('label', case2_id)

    if month is None:
        month = extract_month_from_filename(file1)
        if month is None:
            month = extract_month_from_filename(file2)
        if month is None:
            print(f"⚠️ 无法从文件名中提取月份，使用默认月份7")
            month = 7
        else:
            print(f"✅ 从文件名中提取到月份: {month}")

    print(f"\n{'='*70}")
    print(f"处理文件对比: {output_suffix}")
    print(f"文件1: {os.path.basename(file1)} ({case1_label})")
    print(f"文件2: {os.path.basename(file2)} ({case2_label})")
    print(f"变量: {var_name}")
    print(f"检测到月份: {month}")
    print(f"{'='*70}")

    if not os.path.exists(file1):
        print(f"❌ 文件不存在: {file1}")
        return None

    if not os.path.exists(file2):
        print(f"❌ 文件不存在: {file2}")
        return None

    try:
        data1 = pd.read_csv(file1)
        data2 = pd.read_csv(file2)
        print(f"✅ 数据读取成功: 数据1={len(data1)}行, 数据2={len(data2)}行")
        print(f"数据1列名: {list(data1.columns)}")
        print(f"数据2列名: {list(data2.columns)}")
    except Exception as e:
        print(f"❌ 读取数据失败: {str(e)}")
        return None

    var_config = get_variable_info(var_name)

    save_file = plot_difference_map(
        data1, data2, var_config, file_config,
        model_file, save_dir, boundary_file, month
    )

    if save_file:
        print(f"✅ {var_name} {output_suffix} 处理完成")
    else:
        print(f"❌ {var_name} {output_suffix} 处理失败")

    return save_file


def main():
    """主函数"""
    print("=" * 70)
    print("气象变量差异图批量绘制 — Hourly Case 版本（Case1 vs Case3）")
    print("=" * 70)

    MODEL_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"
    BOUNDARY_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"
    SAVE_DIR = "/data/workspace/GuangDong/Mcip_Comparison_Plots_Hourly_Case"

    # 默认处理热浪天数（小时级覆盖）
    VARIABLES_TO_PROCESS = ['Heatwave_Days']

    print(f"Case 对应关系:")
    for cid, cinfo in CASE_DEFINITIONS.items():
        print(f"  {cid} → {cinfo['year']}年数据  ({cinfo['label']})")
    print(f"\n处理变量: {VARIABLES_TO_PROCESS}")
    print(f"文件对比数量: {len(COMPARISON_CONFIGS)}")
    print(f"输出目录: {SAVE_DIR}")
    print(f"标题格式: 月份 变量名: Case1 - Case3")
    print(f"文件命名格式: 变量名_Case1_minus_Case3_月份.png")

    total_processed = 0
    total_successful = 0
    processed_files = []

    for var_name in VARIABLES_TO_PROCESS:
        for file_config in COMPARISON_CONFIGS:
            total_processed += 1
            try:
                save_file = process_file_comparison(
                    file_config, var_name, MODEL_FILE, BOUNDARY_FILE,
                    SAVE_DIR, None
                )
                if save_file:
                    total_successful += 1
                    processed_files.append(save_file)
            except Exception as e:
                print(f"❌ 处理 {var_name} {file_config[4]} 时发生错误: {str(e)}")
                continue

    print(f"\n{'='*70}")
    print(f"处理完成！")
    print(f"{'='*70}")
    print(f"总处理数量: {total_processed}")
    print(f"成功数量: {total_successful}")
    print(f"失败数量: {total_processed - total_successful}")
    print(f"图像保存在: {SAVE_DIR}")
    print(f"\n生成的气象变量差值图:")
    for i, file_path in enumerate(processed_files, 1):
        print(f"  {i}. {os.path.basename(file_path)}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

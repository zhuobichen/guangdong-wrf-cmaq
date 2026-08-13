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
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['font.family'] = 'sans-serif'

# 确保所有元素都使用中文字体
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# 基础配置
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
cmap_delta = cmaps.ViBlGrWhYeOrRe  # 差值图颜色映射

# === CMAQ输出变量配置 ===
VARIABLE_CONFIGS = {
    'O3': {
        'display_name': 'O3',
        'column_name': 'O3',
        'unit': 'ppb',
        'file_pattern': 'Emission',
        'stats_type': 'Mean',
        'legend_range': (-23, 23),
        'colorbar_format': '.1f',
        'show_domain_stat': True,
        'is_exceedance': False,
        'exceedance_title': 'O3≥80ppb Days'
    },
    'PM2.5': {
        'display_name': 'PM2.5',
        'column_name': 'PM2.5',
        'unit': 'μg/m³',
        'file_pattern': 'Emission',
        'stats_type': 'Mean',
        'legend_range': (None, None),
        'colorbar_format': '.1f',
        'show_domain_stat': True,
        'is_exceedance': False,
        'exceedance_title': 'PM2.5≥75μg/m³ Days'
    },
    'O3_Days': {
        'display_name': 'O3超标天',
        'column_name': 'O3_Days',
        'unit': 'days',
        'file_pattern': 'Emission',
        'stats_type': 'Count',
        'legend_range': (-6, 6),
        'colorbar_format': '.0f',
        'show_domain_stat': True,
        'is_exceedance': True,
        'exceedance_title': 'O3≥80ppb Days'
    },
    'PM2.5_Days': {
        'display_name': 'PM2.5超标天',
        'column_name': 'PM2.5_Days',
        'unit': 'days',
        'file_pattern': 'Emission',
        'stats_type': 'Count',
        'legend_range': (-3, 3),
        'colorbar_format': '.0f',
        'show_domain_stat': True,
        'is_exceedance': True,
        'exceedance_title': 'PM2.5≥75μg/m³ Days'
    }
}

# === CASE映射配置 ===
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

def extract_month_from_filename(filename):
    """从CMAQ输出文件名中提取月份"""
    match = re.search(r'_(\d{2})\.csv$', os.path.basename(filename))
    if match:
        month = int(match.group(1))
        if 1 <= month <= 12:
            return month
    return None

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

def generate_plot_title(var_name, case1, case2, month, output_suffix=""):
    """生成新的标题格式"""
    month_names_cn = {
        1: '1月', 2: '2月', 3: '3月', 4: '4月',
        5: '5月', 6: '6月', 7: '7月', 8: '8月',
        9: '9月', 10: '10月', 11: '11月', 12: '12月'
    }

    month_name = month_names_cn.get(month, f'{month}月')
    var_config = VARIABLE_CONFIGS[var_name]

    # 获取CASE编号
    case1_num = get_case_number(case1)
    case2_num = get_case_number(case2)

    # 根据变量类型生成不同格式的标题
    if var_config.get('is_exceedance', False):
        # 超标天变量格式：1月 PM2.5≥75μg/m³ Days (Case1 - Case3)
        title = f"{month_name} {var_config['exceedance_title']} (Case{case1_num} - Case{case2_num})"
    else:
        # 浓度变量格式：1月 PM2.5 (Case1 - Case3)
        title = f"{month_name} {var_config['display_name']} (Case{case1_num} - Case{case2_num})"

    return title

def generate_output_filename(var_name, case1, case2, month, output_suffix=""):
    """生成新的文件名格式"""
    month_names_en = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    
    month_name = month_names_en.get(month, f'M{month:02d}')
    
    # 变量名映射
    var_mapping = {
        'O3': 'O3_Conc',
        'PM2.5': 'PM2.5_Conc',
        'O3_Days': 'O3_Exceedance',
        'PM2.5_Days': 'PM2.5_Exceedance'
    }
    var_display = var_mapping.get(var_name, var_name)
    
    # 使用输出后缀或自动生成
    if output_suffix:
        case_part = output_suffix
    else:
        case1_num = get_case_number(case1)
        case2_num = get_case_number(case2)
        case_part = f"Case{case1_num}-Case{case2_num}"
    
    filename = f"{var_display}_{case_part}.png"
    return filename

def plot_cmaq_difference_map(data1, data2, var_name, file1, file2, output_suffix, model_file, save_dir, boundary_json_file):
    """绘制CMAQ变量差值地图"""
    print(f"开始绘制{var_name}差值地图...")

    # 加载模型投影信息
    try:
        mp = model_attribute(model_file)
        proj, longitudes, latitudes = mp.projection, mp.lons, mp.lats
        grid_shape = longitudes.shape
        print(f"模型网格信息: {grid_shape}")
    except Exception as e:
        print(f"加载模型信息失败: {str(e)}")
        return None

    # 获取变量信息
    var_config = VARIABLE_CONFIGS[var_name]
    column_name = var_config['column_name']

    # 检查数据列是否存在
    if column_name not in data1.columns or column_name not in data2.columns:
        print(f"错误: 数据中缺少 {column_name} 列")
        print(f"可用列 - 数据1: {list(data1.columns)}")
        print(f"可用列 - 数据2: {list(data2.columns)}")
        return None

    # 确保数据长度匹配网格尺寸
    expected_size = grid_shape[0] * grid_shape[1]
    if len(data1) != expected_size or len(data2) != expected_size:
        print(f"数据长度不匹配: 数据1={len(data1)}, 数据2={len(data2)}, 网格={expected_size}")
        
        # 尝试调整数据长度
        min_len = min(len(data1), len(data2), expected_size)
        data1 = data1.iloc[:min_len]
        data2 = data2.iloc[:min_len]
        grid_shape = (int(np.sqrt(min_len)), int(np.sqrt(min_len)))
        print(f"调整后的数据长度: {min_len}, 网格: {grid_shape}")

    # 重塑数据并计算差值
    try:
        # 确保数据按ROW, COL排序
        data1_sorted = data1.sort_values(by=['ROW', 'COL'])
        data2_sorted = data2.sort_values(by=['ROW', 'COL'])

        var1 = data1_sorted[column_name].values.reshape(grid_shape)
        var2 = data2_sorted[column_name].values.reshape(grid_shape)
        
        # 计算差值（文件1 - 文件2）
        diff = var1 - var2

        # 从文件名获取CASE信息
        case1 = get_case_from_filename(file1)
        case2 = get_case_from_filename(file2)
        month = extract_month_from_filename(file1)
        if month is None:
            month = extract_month_from_filename(file2)
        
        print(f"自动识别CASE: {case1} - {case2}")
        print(f"差值统计: min={diff.min():.6f}, max={diff.max():.6f}, mean={diff.mean():.6f}")
        
        # 自动计算图例范围
        if var_config['legend_range'] == (None, None):
            # 计算0.5%和99.5%分位数，排除极端值
            vmin = np.nanpercentile(diff, 0.5)
            vmax = np.nanpercentile(diff, 99.5)
            var_config['legend_range'] = (vmin, vmax)
            print(f"自动计算图例范围（0.5%-99.5%分位数）：{vmin:.6f} ~ {vmax:.6f} {var_config['unit']}")
        else:
            print(f"使用手动指定图例范围：{var_config['legend_range'][0]} ~ {var_config['legend_range'][1]} {var_config['unit']}")

    except Exception as e:
        print(f"数据处理失败: {str(e)}")
        return None

    # 生成标题和文件名
    plot_title = generate_plot_title(var_name, case1, case2, month, output_suffix)
    output_filename = generate_output_filename(var_name, case1, case2, month, output_suffix)

    # 准备绘图数据
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

    # 绘图配置（参考你的工作代码）
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

    # 绘制并保存图像
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

def process_cmaq_comparison(file_config, var_name, model_file, boundary_file, save_dir):
    """处理单个CMAQ变量文件对比"""
    file1 = file_config[0]
    file2 = file_config[1]
    output_suffix = file_config[2] if len(file_config) > 2 else ""

    print(f"\n{'='*70}")
    print(f"处理CMAQ {var_name} 文件对比: {output_suffix}")
    print(f"文件1: {os.path.basename(file1)}")
    print(f"文件2: {os.path.basename(file2)}")
    print(f"注意: 差值计算为 (文件1 - 文件2)")
    print(f"{'='*70}")

    # 检查文件是否存在
    if not os.path.exists(file1) or not os.path.exists(file2):
        print(f"❌ 文件不存在")
        return None

    # 读取数据
    try:
        data1 = pd.read_csv(file1)
        data2 = pd.read_csv(file2)
        print(f"✅ 数据读取成功: 数据1={len(data1)}行, 数据2={len(data2)}行")

        # 显示数据信息
        print(f"数据1列名: {list(data1.columns)}")
        print(f"数据2列名: {list(data2.columns)}")

        var_config = VARIABLE_CONFIGS[var_name]
        column_name = var_config['column_name']

        if column_name in data1.columns:
            var_1 = data1[column_name]
            print(f"数据1 {var_name}统计: mean={var_1.mean():.6f}, max={var_1.max():.6f}, "
                  f"non-zero={(var_1 > 0).sum()}/{len(var_1)}")

        if column_name in data2.columns:
            var_2 = data2[column_name]
            print(f"数据2 {var_name}统计: mean={var_2.mean():.6f}, max={var_2.max():.6f}, "
                  f"non-zero={(var_2 > 0).sum()}/{len(var_2)}")

    except Exception as e:
        print(f"❌ 读取数据失败: {str(e)}")
        return None

    # 绘制CMAQ变量差值地图
    save_file = plot_cmaq_difference_map(
        data1, data2, var_name, file1, file2, output_suffix, model_file, save_dir, boundary_file
    )

    if save_file:
        print(f"✅ {var_name} {output_suffix} 处理完成")
    else:
        print(f"❌ {var_name} {output_suffix} 处理失败")

    return save_file

# === CMAQ输出数据对比配置 ===
# 格式：[文件名1, 文件名2, 输出后缀(可选)]
# 注意：差值计算为 (文件1 - 文件2)
CMAQ_COMPARISON_CONFIGS = [
    # CMAQ模拟效果2000 (CASE1 - CASE3)
    # [
    #     '/data/workspace/GuangDong/cmaqout_processed/2000_Emission[2000met]_07.csv',
    #     '/data/workspace/GuangDong/cmaqout_processed/2023_Emission[2023met]_07.csv',
    #     'CASE1-CASE3_Jul'  # CASE1 - CASE3
    # ],
    # [
    #     '/data/workspace/GuangDong/cmaqout_processed/2000_Emission[2000met]_01.csv',
    #     '/data/workspace/GuangDong/cmaqout_processed/2023_Emission[2023met]_01.csv',
    #     'CASE1-CASE3_Jan'  # CASE1 - CASE3
    # ],
    
    # # 气象变化影响 (CASE1 - CASE2)
    # [
    #     '/data/workspace/GuangDong/cmaqout_processed/2000_Emission[2000met]_01.csv',
    #     '/data/workspace/GuangDong/cmaqout_processed/2000_Emission[2023met]_01.csv',
    #     'CASE1-CASE2_Jan'  # CASE1 - CASE2
    # ],
    # [
    #     '/data/workspace/GuangDong/cmaqout_processed/2000_Emission[2000met]_07.csv',
    #     '/data/workspace/GuangDong/cmaqout_processed/2000_Emission[2023met]_07.csv',
    #     'CASE1-CASE2_Jul'  # CASE1 - CASE2
    # ],
    
    #清单变化影响 (CASE1 - CASE4)
    [
        '/data/workspace/GuangDong/cmaqout_processed/2000_Emission[2000met]_01.csv',
        '/data/workspace/GuangDong/cmaqout_processed/2023_Emission[2000met]_01.csv',
        'CASE1-CASE4_Jan'  # CASE1 - CASE4
    ],
    [
        '/data/workspace/GuangDong/cmaqout_processed/2000_Emission[2000met]_07.csv',
        '/data/workspace/GuangDong/cmaqout_processed/2023_Emission[2000met]_07.csv',
        'CASE1-CASE4_Jul'  # CASE1 - CASE4
    ],

    # [
    #     '/data/workspace/GuangDong/cmaqout_processed/2060_Emission[2060met]_07.csv',
    #     '/data/workspace/GuangDong/cmaqout_processed/2023_Emission[2023met]_07.csv',
    #     'CASE5-CASE3_Jul'  # CASE5 - CASE3
    # ],
    # [
    #     '/data/workspace/GuangDong/cmaqout_processed/2060_Emission[2060met]_01.csv',
    #     '/data/workspace/GuangDong/cmaqout_processed/2023_Emission[2023met]_01.csv',
    #     'CASE5-CASE3_Jan'  # CASE5 - CASE3
    # ],

    # [
    #     '/data/workspace/GuangDong/cmaqout_processed/2030_Emission[2030met]_07.csv',
    #     '/data/workspace/GuangDong/cmaqout_processed/2023_Emission[2023met]_07.csv',
    #     'CASE6-CASE3_Jul'  # CASE6 - CASE3
    # ],
    # [
    #     '/data/workspace/GuangDong/cmaqout_processed/2030_Emission[2030met]_01.csv',
    #     '/data/workspace/GuangDong/cmaqout_processed/2023_Emission[2023met]_01.csv',
    #     'CASE6-CASE3_Jan'  # CASE6 - CASE3
    # ],
    
]

def main():
    """主函数"""
    print("=" * 70)
    print("CMAQ输出数据差异图批量绘制 (支持CASE命名)")
    print("=" * 70)

    # === 配置参数 ===
    MODEL_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"
    BOUNDARY_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"
    SAVE_DIR = "/data/workspace/GuangDong/Emission_Comparison_Plots_CN"

    # 选择要处理的变量
    # VARIABLES_TO_PROCESS = ['O3', 'PM2.5', 'O3_Days', 'PM2.5_Days']
    VARIABLES_TO_PROCESS = ['O3']
    # VARIABLES_TO_PROCESS = ['O3', 'PM2.5']

    print(f"处理变量: {VARIABLES_TO_PROCESS}")
    print(f"文件对比数量: {len(CMAQ_COMPARISON_CONFIGS)}")
    print(f"输出目录: {SAVE_DIR}")
    print(f"\nCASE映射规则:")
    for case, (emission, met, desc) in CASE_DEFINITIONS.items():
        print(f"  {case}: {emission}排放, {met}气象 ({desc})")

    # 处理所有配置的变量和文件对比
    total_processed = 0
    total_successful = 0
    processed_files = []

    for var_name in VARIABLES_TO_PROCESS:
        for file_config in CMAQ_COMPARISON_CONFIGS:
            total_processed += 1
            try:
                save_file = process_cmaq_comparison(
                    file_config, var_name, MODEL_FILE, BOUNDARY_FILE, SAVE_DIR
                )
                if save_file:
                    total_successful += 1
                    processed_files.append(save_file)
            except Exception as e:
                print(f"❌ 处理 {var_name} {file_config[-1]} 时发生错误: {str(e)}")
                continue

    print(f"\n{'='*70}")
    print(f"CMAQ数据差值图处理完成！")
    print(f"{'='*70}")
    print(f"总处理数量: {total_processed}")
    print(f"成功数量: {total_successful}")
    print(f"失败数量: {total_processed - total_successful}")
    print(f"图像保存在: {SAVE_DIR}")
    print(f"\n生成的CMAQ差值图:")
    for i, file_path in enumerate(processed_files, 1):
        print(f"  {i}. {os.path.basename(file_path)}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
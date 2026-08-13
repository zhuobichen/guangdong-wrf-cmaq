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

# 基础配置
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
cmap_delta = cmaps.ViBlGrWhYeOrRe  # 差值图颜色映射

# === 气象变量配置 ===
# 支持多种气象变量的差异图绘制
VARIABLE_CONFIGS = {
    'TA_mean': {
        'display_name': 'Temperature',
        'column_name': 'TA_mean',
        'unit': '°C',
        'file_pattern': 'mcipout',  # 文件前缀模式
        'stats_type': 'Mean',
        'legend_range': (None, None),  # 自定义图例范围
        'colorbar_format': '.1f',  # 色标数值格式
        'show_domain_stat': True   # 显示区域统计
    },
    'TA_max': {
        'display_name': 'Temperature',
        'column_name': 'TA_max',
        'unit': '°C',
        'file_pattern': 'mcipout',
        'stats_type': 'Max',
        'legend_range': (None, None),
        'colorbar_format': '.1f',
        'show_domain_stat': True
    },
    'SOL_RAD_mean': {
        'display_name': 'Solar Radiation',
        'column_name': 'SOL_RAD_mean',
        'unit': 'W/m²',
        'file_pattern': 'mcipout',
        'stats_type': 'Mean',
        'legend_range': (None, None),
        'colorbar_format': '.0f',
        'show_domain_stat': True
    },
    'SOL_RAD_max': {
        'display_name': 'Solar Radiation',
        'column_name': 'SOL_RAD_max',
        'unit': 'W/m²',
        'file_pattern': 'mcipout',
        'stats_type': 'Max',
        'legend_range': (None, None),
        'colorbar_format': '.0f',
        'show_domain_stat': True
    },
    'PBLH_mean': {
        'display_name': 'Boundary Layer Height',
        'column_name': 'PBLH_mean',
        'unit': 'm',
        'file_pattern': 'mcipout',
        'stats_type': 'Mean',
        'legend_range': (None, None),
        'colorbar_format': '.0f',
        'show_domain_stat': True
    },
    'PBLH_max': {
        'display_name': 'Boundary Layer Height',
        'column_name': 'PBLH_max',
        'unit': 'm',
        'file_pattern': 'mcipout',
        'stats_type': 'Max',
        'legend_range': (None, None),
        'colorbar_format': '.0f',
        'show_domain_stat': True
    }
}

# === 数据对比配置 ===
# 直接指定具体文件名和对应年份，格式：[文件名1, 文件名2, 年份1, 年份2, 输出后缀]
COMPARISON_CONFIGS = [
    # 示例配置：第一个文件减第二个文件
    [
        '/data/workspace/GuangDong/mcipout_processed/2000_mcipout_07.csv',  # 文件1
        '/data/workspace/GuangDong/mcipout_processed/2023_mcipout_07.csv',  # 文件2
        2000,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2000_minus_2023'  # 输出文件后缀
    ],

    [
        '/data/workspace/GuangDong/mcipout_processed/2000_mcipout_01.csv',  # 文件1
        '/data/workspace/GuangDong/mcipout_processed/2023_mcipout_01.csv',  # 文件2
        2000,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2000_minus_2023'  # 输出文件后缀
    ],

    [
        '/data/workspace/GuangDong/mcipout_processed/2030_mcipout_01.csv',  # 文件1
        '/data/workspace/GuangDong/mcipout_processed/2023_mcipout_01.csv',  # 文件2
        2030,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2030_minus_2023'  # 输出文件后缀
    ],

    [
        '/data/workspace/GuangDong/mcipout_processed/2030_mcipout_07.csv',  # 文件1
        '/data/workspace/GuangDong/mcipout_processed/2023_mcipout_07.csv',  # 文件2
        2030,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2030_minus_2023'  # 输出文件后缀
    ],

    [
        '/data/workspace/GuangDong/mcipout_processed/2060_mcipout_01.csv',  # 文件1
        '/data/workspace/GuangDong/mcipout_processed/2023_mcipout_01.csv',  # 文件2
        2060,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2060_minus_2023'  # 输出文件后缀
    ],

    [
        '/data/workspace/GuangDong/mcipout_processed/2060_mcipout_07.csv',  # 文件1
        '/data/workspace/GuangDong/mcipout_processed/2023_mcipout_07.csv',  # 文件2
        2060,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2060_minus_2023'  # 输出文件后缀
    ],

    # [
    #     '/data/workspace/GuangDong/mcipout_processed/2023_mcipout_07.csv',  # 文件1
    #     '/data/workspace/GuangDong/mcipout_processed/2060_mcipout_07.csv',  # 文件2
    #     2023,        # 文件1对应年份
    #     2060,        # 文件2对应年份
    #     '2023_minus_2060'  # 输出文件后缀
    # ],
    # 可以添加更多配置...
    # [
    #     '/path/to/file1.csv',    # 文件1
    #     '/path/to/file2.csv',    # 文件2
    #     2025,                   # 文件1年份
    #     2030,                   # 文件2年份
    #     '2025_minus_2030'       # 输出后缀
    # ],
]

def extract_month_from_filename(filename):
    """从文件名中提取月份（从末尾的_01, _07等格式）"""
    import re
    # 匹配文件名末尾的月份格式，如 _01, _07 等
    match = re.search(r'_(\d{2})(?:\.\w+$|$)', filename)
    if match:
        month_num = int(match.group(1))
        if 1 <= month_num <= 12:
            return month_num
    return None  # 如果无法提取或无效月份，返回None

def get_variable_info(var_name):
    """获取变量信息"""
    if var_name not in VARIABLE_CONFIGS:
        raise ValueError(f"未配置变量: {var_name}")
    return VARIABLE_CONFIGS[var_name]

def generate_file_paths(year1, year2, month=7, use_huizhou=False):
    """生成文件路径（已弃用，现在直接从配置中获取文件路径）"""
    # 这个函数现在不需要了，因为文件路径直接从配置中获取
    pass

def generate_plot_title(var_config, year1, year2, month=7, output_suffix=""):
    """生成绘图标题"""
    month_names = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
                   5: 'May', 6: 'June', 7: 'July', 8: 'August',
                   9: 'September', 10: 'October', 11: 'November', 12: 'December'}

    month_name = month_names.get(month, f'Month{month}')
    display_name = var_config['display_name']
    stats_type = var_config['stats_type']

    # 从输出后缀判断是否为惠州版本
    region_suffix = " (Huizhou)" if "HuiZhou" in output_suffix else ""

    # 生成更清晰的标题，保持与文件命名一致
    title = f"{display_name} Difference ({month_name} {stats_type}): {year1} - {year2}{region_suffix}"
    return title

def generate_output_filename(var_config, output_suffix, month=7):
    """生成输出文件名"""
    var_short_name = var_config['column_name'].replace('_mean', '').replace('_max', '')

    # 映射变量名
    name_mapping = {
        'TA': 'TA',
        'SOL_RAD': 'SOLAR',
        'PBLH': 'PBLH'
    }

    short_name = name_mapping.get(var_short_name, var_short_name)
    stats_type = var_config['stats_type']

    # 月份名称映射（保持与文件路径格式一致）
    month_str = f"{month:02d}"  # 使用两位数月份格式，如01, 07

    # 根据输出后缀生成一致的文件名格式
    # 例如：TA_2000vs2023_07_Mean.png
    if 'minus' in output_suffix:
        # 提取年份信息
        years = output_suffix.replace('_minus_', 'vs')
        filename = f"{short_name}_{years}_{month_str}{stats_type}.png"
    else:
        # 其他情况保持原有逻辑，但使用数字月份
        filename = f"{short_name}_{output_suffix}_{month_str}{stats_type}.png"

    return filename

def plot_difference_map(data1, data2, var_config, file_config, model_file,
                       save_dir, boundary_json_file, month=7):
    """
    绘制气象变量差值地图
    """
    print(f"开始绘制差值地图...")

    # 加载模型投影信息
    try:
        mp = model_attribute(model_file)
        proj, longitudes, latitudes = mp.projection, mp.lons, mp.lats
        grid_shape = longitudes.shape
        print(f"模型网格信息: {grid_shape}")
    except Exception as e:
        print(f"加载模型信息失败: {str(e)}")
        return

    # 获取变量信息
    column_name = var_config['column_name']

    # 检查数据列是否存在
    if column_name not in data1.columns or column_name not in data2.columns:
        print(f"错误: 数据中缺少 {column_name} 列")
        print(f"可用列 - 数据1: {list(data1.columns)}")
        print(f"可用列 - 数据2: {list(data2.columns)}")
        return

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
        var1 = data1[column_name].values.reshape(grid_shape)
        var2 = data2[column_name].values.reshape(grid_shape)

        # 计算差值（文件1 - 文件2）
        diff = var1 - var2
        year1 = file_config[2]  # 文件1对应年份
        year2 = file_config[3]  # 文件2对应年份
        calculation_desc = f"{year1} - {year2}"

        print(f"差值计算: {calculation_desc}")
        print(f"差值统计: min={diff.min():.3f}, max={diff.max():.3f}, mean={diff.mean():.3f}")

        # 自动计算基于分位数的图例范围
        if var_config['legend_range'] == (None, None):
            # 计算0.5%和99.5%分位数，排除极端值
            vmin = np.nanpercentile(diff, 0.5)
            vmax = np.nanpercentile(diff, 99.5)
            var_config['legend_range'] = (vmin, vmax)
            print(f"自动计算图例范围（0.5%-99.5%分位数）：{vmin:.3f} ~ {vmax:.3f} {var_config['unit']}")
        else:
            print(f"使用手动指定图例范围：{var_config['legend_range'][0]} ~ {var_config['legend_range'][1]} {var_config['unit']}")
    except Exception as e:
        print(f"数据重塑失败: {str(e)}")
        return

    # 生成标题和文件名
    output_suffix = file_config[4]  # 输出后缀
    plot_title = generate_plot_title(var_config, year1, year2, month, output_suffix)
    output_filename = generate_output_filename(var_config, output_suffix, month)

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

    # 绘图配置
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
            "value_range": var_config['legend_range'],  # 使用自定义图例范围
            "colorbar_ticks_value_format": var_config['colorbar_format'],
            "value_format": var_config['colorbar_format']
        },
        'title_fontsize': 12,
        'xy_title_fontsize': 10,
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

        # 确保保存目录存在
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
    # 解析文件配置
    file1 = file_config[0]
    file2 = file_config[1]
    year1 = file_config[2]
    year2 = file_config[3]
    output_suffix = file_config[4]

    # 如果没有提供月份，从文件名中动态提取
    if month is None:
        month = extract_month_from_filename(file1)
        if month is None:
            month = extract_month_from_filename(file2)
        if month is None:
            print(f"⚠️ 无法从文件名中提取月份，使用默认月份7")
            month = 7
        else:
            print(f"✅ 从文件名中提取到月份: {month}")

    print(f"\n{'='*60}")
    print(f"处理文件对比: {output_suffix}")
    print(f"文件1: {os.path.basename(file1)} ({year1}年)")
    print(f"文件2: {os.path.basename(file2)} ({year2}年)")
    print(f"变量: {var_name}")
    print(f"检测到月份: {month}")
    print(f"{'='*60}")

    # 检查文件是否存在
    if not os.path.exists(file1):
        print(f"❌ 文件不存在: {file1}")
        return None

    if not os.path.exists(file2):
        print(f"❌ 文件不存在: {file2}")
        return None

    # 读取数据
    try:
        data1 = pd.read_csv(file1)
        data2 = pd.read_csv(file2)
        print(f"✅ 数据读取成功: 数据1={len(data1)}行, 数据2={len(data2)}行")

        # 显示前几行数据信息
        print(f"数据1列名: {list(data1.columns)}")
        print(f"数据2列名: {list(data2.columns)}")

    except Exception as e:
        print(f"❌ 读取数据失败: {str(e)}")
        return None

    # 获取变量配置
    var_config = get_variable_info(var_name)

    # 绘制差值地图
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
    print("开始气象变量差异图批量绘制...")

    # === 配置参数 ===
    MODEL_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"
    BOUNDARY_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"
    SAVE_DIR = "/data/workspace/GuangDong/Mcip_Comparison_Plots"

    # 选择要处理的变量
    # 可以根据需要修改这些列表
    # VARIABLES_TO_PROCESS = ['TA_mean', 'TA_max', 'SOL_RAD_mean','SOL_RAD_max', 'PBLH_mean','PBLH_max']  # 要处理的变量
    VARIABLES_TO_PROCESS = ['PBLH_mean'] 
    print(f"处理变量: {VARIABLES_TO_PROCESS}")
    print(f"文件对比数量: {len(COMPARISON_CONFIGS)}")
    print(f"输出目录: {SAVE_DIR}")
    print(f"月份将从文件名中动态提取（如 _01 表示January，_07 表示July）")

    # 处理所有配置的变量和文件对比
    total_processed = 0
    total_successful = 0
    processed_files = []

    for var_name in VARIABLES_TO_PROCESS:
        for file_config in COMPARISON_CONFIGS:
            total_processed += 1
            try:
                save_file = process_file_comparison(
                    file_config, var_name, MODEL_FILE, BOUNDARY_FILE,
                    SAVE_DIR, None  # 传递None让函数自动提取月份
                )
                if save_file:
                    total_successful += 1
                    processed_files.append(save_file)
            except Exception as e:
                print(f"❌ 处理 {var_name} {file_config[4]} 时发生错误: {str(e)}")
                continue

    print(f"\n{'='*60}")
    print(f"处理完成！")
    print(f"总处理数量: {total_processed}")
    print(f"成功数量: {total_successful}")
    print(f"失败数量: {total_processed - total_successful}")
    print(f"图像保存在: {SAVE_DIR}")
    print(f"\n生成的图像文件:")
    for i, file_path in enumerate(processed_files, 1):
        print(f"  {i}. {os.path.basename(file_path)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
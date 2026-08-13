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

# 颜色映射
cmap_conc = cmaps.WhiteBlueGreenYellowRed
cmap_nox = cmaps.WhiteBlueGreenYellowRed
cmap_so2 = cmaps.WhiteBlueGreenYellowRed
cmap_nh3 = cmaps.WhiteBlueGreenYellowRed
cmap_voc = cmaps.WhiteBlueGreenYellowRed
cmap_delta = cmaps.ViBlGrWhYeOrRe  # 差值图颜色映射

# === 污染物变量配置 ===
VARIABLE_CONFIGS = {
    # PM2.5
    'PM2.5': {
        'display_name': 'PM2.5',
        'column_name': 'PM2.5',
        'unit': 'μg/m³',
        'file_pattern': 'EM',
        'legend_range': (None, None),
        'colorbar_format': '.2f',
        'cmap': cmap_conc,
        'show_domain_stat': True
    },

    # NOX
    'NOX': {
        'display_name': 'NOX',
        'column_name': 'NOX',
        'unit': 'moles/s',
        'file_pattern': 'EM',
        'legend_range': (None, None),
        'colorbar_format': '.4f',
        'cmap': cmap_nox,
        'show_domain_stat': True
    },

    # SO2
    'SO2': {
        'display_name': 'SO2',
        'column_name': 'SO2',
        'unit': 'moles/s',
        'file_pattern': 'EM',
        'legend_range': (None, None),
        'colorbar_format': '.3f',
        'cmap': cmap_so2,
        'show_domain_stat': True
    },

    # NH3
    'NH3': {
        'display_name': 'NH3',
        'column_name': 'NH3',
        'unit': 'moles/s',
        'file_pattern': 'EM',
        'legend_range': (None, None),
        'colorbar_format': '.3f',
        'cmap': cmap_nh3,
        'show_domain_stat': True
    },

    # VOC
    'VOC': {
        'display_name': 'VOC',
        'column_name': 'VOC',
        'unit': 'moles/s',
        'file_pattern': 'EM',
        'legend_range': (None, None),
        'colorbar_format': '.3f',
        'cmap': cmap_voc,
        'show_domain_stat': True
    },

    # 人口密度
    'Population': {
        'display_name': '人口密度',
        'column_name': 'Population',
        'unit': '人/km²',
        'file_pattern': 'EM',
        'legend_range': (None, None),
        'colorbar_format': '.2f',
        'cmap': cmap_conc,
        'show_domain_stat': True
    },

    # 排放强度
    'Emission': {
        'display_name': '排放强度',
        'column_name': 'Emission',
        'unit': 'kg/km²·d',
        'file_pattern': 'EM',
        'legend_range': (None, None),
        'colorbar_format': '.2f',
        'cmap': cmap_conc,
        'show_domain_stat': True
    }
}

# 兼容旧的PM2.5配置
PM25_VARIABLE_CONFIG = VARIABLE_CONFIGS

# === 污染物排放数据对比配置 ===
# 格式：[文件名1, 文件名2, 年份1, 年份2, 输出后缀]
COMPARISON_CONFIGS = [
    # 2000 vs 2023 对比
    [
        '/data/workspace/GuangDong/emissionlist/EM_200001_ALL_OnlyGuangDong.csv',
        '/data/workspace/GuangDong/emissionlist/EM_202301_ALL_OnlyGuangDong.csv',
        2000, 2023,
        '2000_minus_2023'
    ],
    [
        '/data/workspace/GuangDong/emissionlist/EM_200007_ALL_OnlyGuangDong.csv',
        '/data/workspace/GuangDong/emissionlist/EM_202307_ALL_OnlyGuangDong.csv',
        2000, 2023,
        '2000_minus_2023'
    ],
]

# 兼容旧的配置名称
EMISSION_COMPARISON_CONFIGS = COMPARISON_CONFIGS

def extract_month_from_filename(filename):
    """从文件名中提取月份（EM_YYYYMM格式）"""
    match = re.search(r'EM_(\d{4})(\d{2})', os.path.basename(filename))
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        if 1 <= month <= 12:
            return month, year
    return None, None  # 如果无法提取，返回None

def get_month_name_cn(month):
    """将月份数字转换为中文月份名称"""
    month_names_cn = {
        1: '1月', 2: '2月', 3: '3月', 4: '4月',
        5: '5月', 6: '6月', 7: '7月', 8: '8月',
        9: '9月', 10: '10月', 11: '11月', 12: '12月'
    }
    return month_names_cn.get(month, f'{month}月')

def get_variable_info(var_name):
    """获取变量信息"""
    if var_name not in VARIABLE_CONFIGS:
        raise ValueError(f"未配置变量: {var_name}")
    return VARIABLE_CONFIGS[var_name]

def get_variable_cmap(var_name):
    """获取变量对应的颜色映射"""
    if var_name in VARIABLE_CONFIGS:
        return VARIABLE_CONFIGS[var_name]['cmap']
    return cmap_conc

def generate_plot_title(var_config, year1, year2, month=7, output_suffix=""):
    """生成新的中文标题格式：1月 PM2.5: 2060 - 2023"""
    month_name = get_month_name_cn(month)
    display_name = var_config['display_name']

    # 生成标题格式：1月 变量名: 年份1 - 年份2
    title = f"{month_name} {display_name}: {year1} - {year2}"

    return title

def generate_output_filename(var_config, output_suffix, month=7):
    """生成输出文件名"""
    display_name = var_config['display_name']

    # 月份格式
    month_str = f"{month:02d}"

    # 根据输出后缀生成文件名
    if 'minus' in output_suffix:
        # 提取年份信息，例如 2060_minus_2023
        years_info = output_suffix
        filename = f"{display_name}_{years_info}_{month_str}.png"
    else:
        filename = f"{display_name}_{output_suffix}_{month_str}.png"

    return filename

def plot_difference_map(data1, data2, var_config, file_config, model_file,
                       save_dir, boundary_json_file, month=7):
    """绘制污染物变量差值地图"""
    print(f"开始绘制差值地图...")

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
        year1 = file_config[2]  # 文件1对应年份
        year2 = file_config[3]  # 文件2对应年份
        calculation_desc = f"{year1} - {year2}"

        print(f"差值计算: {calculation_desc}")
        print(f"差值统计: min={diff.min():.6f}, max={diff.max():.6f}, mean={diff.mean():.6f}")
        print(f"零值网格数: {np.sum(diff == 0)} ({np.sum(diff == 0)/diff.size*100:.2f}%)")

        # 自动计算基于分位数的图例范围
        if var_config['legend_range'] == (None, None):
            # 计算0.5%和99.5%分位数，排除极端值
            vmin = np.nanpercentile(diff, 0.5)
            vmax = np.nanpercentile(diff, 99.5)

            # 对于非常小的最小值，设为0
            if abs(vmin) < 0.01:
                vmin = 0

            var_config['legend_range'] = (vmin, vmax)
            print(f"自动计算图例范围（0.5%-99.5%分位数）：{vmin:.6f} ~ {vmax:.6f} {var_config['unit']}")
        else:
            print(f"使用手动指定图例范围：{var_config['legend_range'][0]} ~ {var_config['legend_range'][1]} {var_config['unit']}")
    except Exception as e:
        print(f"数据重塑失败: {str(e)}")
        return None

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

def plot_pm25_difference_map(data1, data2, file_config, model_file, save_dir, boundary_json_file):
    """兼容旧的PM2.5函数"""
    var_config = get_variable_info('PM2.5')
    month, _ = extract_month_from_filename(file_config[0])
    if month is None:
        month, _ = extract_month_from_filename(file_config[1])
    if month is None:
        month = 7

    return plot_difference_map(data1, data2, var_config, file_config, model_file, save_dir, boundary_json_file, month)

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
        month, _ = extract_month_from_filename(file1)
        if month is None:
            month, _ = extract_month_from_filename(file2)
        if month is None:
            print(f"⚠️ 无法从文件名中提取月份，使用默认月份7")
            month = 7
        else:
            print(f"✅ 从文件名中提取到月份: {month}")

    print(f"\n{'='*70}")
    print(f"处理文件对比: {output_suffix}")
    print(f"文件1: {os.path.basename(file1)} ({year1}年)")
    print(f"文件2: {os.path.basename(file2)} ({year2}年)")
    print(f"变量: {var_name}")
    print(f"检测到月份: {month}")
    print(f"{'='*70}")

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

def process_emission_comparison(file_config, model_file, boundary_file, save_dir):
    """兼容旧的PM2.5函数"""
    return process_file_comparison(file_config, 'PM2.5', model_file, boundary_file, save_dir, None)

def main():
    """主函数"""
    print("=" * 70)
    print("污染物排放差异图批量绘制 (中文版本)")
    print("=" * 70)

    # === 配置参数 ===
    MODEL_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"
    BOUNDARY_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"
    SAVE_DIR = "/data/workspace/GuangDong/PeopleEmission_Plots_CN"

    # 选择要处理的变量
    # 可以根据需要修改这些列表
    # VARIABLES_TO_PROCESS = ['PM2.5']  # 仅PM2.5
    VARIABLES_TO_PROCESS = ['NOX']  # 主要污染物
    # VARIABLES_TO_PROCESS = ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC', 'Population', 'Emission']  # 所有变量

    print(f"处理变量: {VARIABLES_TO_PROCESS}")
    print(f"文件对比数量: {len(COMPARISON_CONFIGS)}")
    print(f"输出目录: {SAVE_DIR}")
    print(f"标题格式: 月份 变量名: 年份1 - 年份2")
    print(f"文件命名格式: 变量名_年份对比_月份.png")

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

    print(f"\n{'='*70}")
    print(f"处理完成！")
    print(f"{'='*70}")
    print(f"总处理数量: {total_processed}")
    print(f"成功数量: {total_successful}")
    print(f"失败数量: {total_processed - total_successful}")
    print(f"图像保存在: {SAVE_DIR}")
    print(f"\n生成的污染物差异图:")
    for i, file_path in enumerate(processed_files, 1):
        print(f"  {i}. {os.path.basename(file_path)}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
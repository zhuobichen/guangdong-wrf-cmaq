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

# 基础配置
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
cmap_delta = cmaps.ViBlGrWhYeOrRe  # 差值图颜色映射

# === PM2.5排放变量配置 ===
PM25_VARIABLE_CONFIG = {
    'PM2.5': {
        'display_name': 'PM2.5 Emissions',
        'column_name': 'PM2.5',
        'unit': 'g/s',
        'file_pattern': 'EM_',  # PM2.5排放文件前缀
        'stats_type': 'Monthly Average',
        'legend_range': (None, None),  # 自动计算图例范围
        'colorbar_format': '.1f',  # 保留一位小数的格式
        'show_domain_stat': True   # 显示区域统计
    }
    
}

# === PM2.5排放数据对比配置 ===
# 直接指定具体文件名和对应年份，格式：[文件名1, 文件名2, 年份1, 年份2, 输出后缀]
EMISSION_COMPARISON_CONFIGS = [
    # 2000年 vs 2030年 对比
    [
        '/data/workspace/GuangDong/emissionlist/EM_200001_PM2.5.csv',  # 2000年1月
        '/data/workspace/GuangDong/emissionlist/EM_202301_PM2.5.csv',  # 2030年1月
        2000,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2000_minus_2023_Jan'  # 输出文件后缀
    ],

    [
        '/data/workspace/GuangDong/emissionlist/EM_200007_PM2.5.csv',  # 2000年7月
        '/data/workspace/GuangDong/emissionlist/EM_202307_PM2.5.csv',  # 2023年7月
        2000,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2000_minus_2023_Jul'  # 输出文件后缀
    ],

    # 2030年 vs 2000年 对比（反方向）
    [
        '/data/workspace/GuangDong/emissionlist/EM_203001_PM2.5.csv',  # 2030年1月
        '/data/workspace/GuangDong/emissionlist/EM_202301_PM2.5.csv',  # 2000年1月
        2030,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2030_minus_2023_Jan'  # 输出文件后缀
    ],

    [
        '/data/workspace/GuangDong/emissionlist/EM_203007_PM2.5.csv',  # 2030年7月
        '/data/workspace/GuangDong/emissionlist/EM_202307_PM2.5.csv',  # 2000年7月
        2030,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2030_minus_2023_Jul'  # 输出文件后缀
    ],

    [
        '/data/workspace/GuangDong/emissionlist/EM_206007_PM2.5.csv',  # 2030年7月
        '/data/workspace/GuangDong/emissionlist/EM_202307_PM2.5.csv',  # 2000年7月
        2060,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2060_minus_2023_Jul'  # 输出文件后缀
    ],

    [
        '/data/workspace/GuangDong/emissionlist/EM_206001_PM2.5.csv',  # 2030年1月
        '/data/workspace/GuangDong/emissionlist/EM_202301_PM2.5.csv',  # 2000年1月
        2060,        # 文件1对应年份
        2023,        # 文件2对应年份
        '2060_minus_2023_Jan'  # 输出文件后缀
    ],

    # 如果有其他年份对比，可以继续添加
    # [
    #     '/data/workspace/GuangDong/emissionlist/EM_201001_PM2.5.csv',  # 2010年1月
    #     '/data/workspace/GuangDong/emissionlist/EM_200001_PM2.5.csv',  # 2000年1月
    #     2010,        # 文件1对应年份
    #     2000,        # 文件2对应年份
    #     '2010_minus_2000_Jan'  # 输出文件后缀
    # ],
]

def extract_month_from_filename(filename):
    """从PM2.5排放文件名中提取月份（格式：EM_YYYYMM_PM2.5.csv）"""
    # 匹配EM_年份月份_PM2.5.csv格式
    match = re.search(r'EM_(\d{4})(\d{2})_PM2\.5\.csv', os.path.basename(filename))
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        if 1 <= month <= 12:
            return month, year
    return None, None  # 如果无法提取，返回None

def generate_plot_title(year1, year2, month, output_suffix=""):
    """生成PM2.5排放差值图的标题"""
    month_names = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
                   5: 'May', 6: 'June', 7: 'July', 8: 'August',
                   9: 'September', 10: 'October', 11: 'November', 12: 'December'}

    month_name = month_names.get(month, f'Month{month}')

    # 根据输出后缀确定标题
    if '2000_minus_2030' in output_suffix:
        title = f"PM2.5 Emissions ({month_name}): 2000 - 2030"
    elif '2030_minus_2000' in output_suffix:
        title = f"PM2.5 Emissions ({month_name}): 2030 - 2000"
    else:
        title = f"PM2.5 Emissions ({month_name}): {year1} - {year2}"

    return title

def generate_output_filename(year1, year2, month, output_suffix=""):
    """生成PM2.5排放差值图的输出文件名"""
    month_names = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
                   5: 'May', 6: 'June', 7: 'July', 8: 'August',
                   9: 'September', 10: 'October', 11: 'November', 12: 'December'}

    month_name = month_names.get(month, f'Month{month}')

    # 根据输出后缀生成文件名
    if '2000_minus_2030' in output_suffix:
        filename = f"PM25_2000_minus_2030_{month_name}.png"
    elif '2030_minus_2000' in output_suffix:
        filename = f"PM25_2030_minus_2000_{month_name}.png"
    else:
        filename = f"PM25_{year1}_minus_{year2}_{month_name}.png"

    return filename

def plot_pm25_difference_map(data1, data2, file_config, model_file, save_dir, boundary_json_file):
    """
    绘制PM2.5排放差值地图
    """
    print(f"开始绘制PM2.5排放差值地图...")

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
    var_config = PM25_VARIABLE_CONFIG['PM2.5']
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

        # 从文件名中提取月份信息
        month, _ = extract_month_from_filename(file_config[0])
        if month is None:
            month, _ = extract_month_from_filename(file_config[1])

        calculation_desc = f"{year1} - {year2}"

        print(f"差值计算: {calculation_desc}")
        print(f"差值统计: min={diff.min():.6f}, max={diff.max():.6f}, mean={diff.mean():.6f}")
        print(f"零值网格数: {np.sum(diff == 0)} ({np.sum(diff == 0)/diff.size*100:.2f}%)")

        # 自动计算基于分位数的图例范围
        if var_config['legend_range'] == (None, None):
            # 计算0.5%和99.5%分位数，排除极端值
            vmin = np.nanpercentile(diff, 0.5)
            vmax = np.nanpercentile(diff, 99.5)
            var_config['legend_range'] = (vmin, vmax)
            print(f"自动计算图例范围（0.5%-99.5%分位数）：{vmin:.6f} ~ {vmax:.6f} {var_config['unit']}")
        else:
            print(f"使用手动指定图例范围：{var_config['legend_range'][0]} ~ {var_config['legend_range'][1]} {var_config['unit']}")

    except Exception as e:
        print(f"数据重塑失败: {str(e)}")
        return None

    # 生成标题和文件名
    output_suffix = file_config[4]  # 输出后缀
    plot_title = generate_plot_title(year1, year2, month, output_suffix)
    output_filename = generate_output_filename(year1, year2, month, output_suffix)

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

def process_emission_comparison(file_config, model_file, boundary_file, save_dir):
    """处理单个PM2.5排放文件对比"""
    # 解析文件配置
    file1 = file_config[0]
    file2 = file_config[1]
    year1 = file_config[2]
    year2 = file_config[3]
    output_suffix = file_config[4]

    print(f"\n{'='*70}")
    print(f"处理PM2.5排放文件对比: {output_suffix}")
    print(f"文件1: {os.path.basename(file1)} ({year1}年)")
    print(f"文件2: {os.path.basename(file2)} ({year2}年)")
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

        # 显示数据信息
        print(f"数据1列名: {list(data1.columns)}")
        print(f"数据2列名: {list(data2.columns)}")

        # 显示基本统计信息
        if 'PM2.5' in data1.columns:
            pm25_1 = data1['PM2.5']
            print(f"数据1 PM2.5统计: mean={pm25_1.mean():.6f}, max={pm25_1.max():.6f}, "
                  f"non-zero={(pm25_1 > 0).sum()}/{len(pm25_1)}")

        if 'PM2.5' in data2.columns:
            pm25_2 = data2['PM2.5']
            print(f"数据2 PM2.5统计: mean={pm25_2.mean():.6f}, max={pm25_2.max():.6f}, "
                  f"non-zero={(pm25_2 > 0).sum()}/{len(pm25_2)}")

    except Exception as e:
        print(f"❌ 读取数据失败: {str(e)}")
        return None

    # 绘制PM2.5排放差值地图
    save_file = plot_pm25_difference_map(
        data1, data2, file_config, model_file, save_dir, boundary_file
    )

    if save_file:
        print(f"✅ PM2.5 {output_suffix} 处理完成")
    else:
        print(f"❌ PM2.5 {output_suffix} 处理失败")

    return save_file

def main():
    """主函数"""
    print("=" * 70)
    print("PM2.5排放数据差异图批量绘制")
    print("=" * 70)

    # === 配置参数 ===
    MODEL_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"
    BOUNDARY_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"
    SAVE_DIR = "/data/workspace/GuangDong/PeopleEmission_Plots"

    print(f"PM2.5排放变量: PM2.5 (Monthly Average)")
    print(f"文件对比数量: {len(EMISSION_COMPARISON_CONFIGS)}")
    print(f"输出目录: {SAVE_DIR}")
    print(f"模型文件: {MODEL_FILE}")
    print(f"边界文件: {BOUNDARY_FILE}")

    # 处理所有配置的文件对比
    total_processed = 0
    total_successful = 0
    processed_files = []

    for file_config in EMISSION_COMPARISON_CONFIGS:
        total_processed += 1
        try:
            save_file = process_emission_comparison(
                file_config, MODEL_FILE, BOUNDARY_FILE, SAVE_DIR
            )
            if save_file:
                total_successful += 1
                processed_files.append(save_file)
        except Exception as e:
            print(f"❌ 处理 {file_config[4]} 时发生错误: {str(e)}")
            continue

    print(f"\n{'='*70}")
    print(f"PM2.5排放差值图处理完成！")
    print(f"{'='*70}")
    print(f"总处理数量: {total_processed}")
    print(f"成功数量: {total_successful}")
    print(f"失败数量: {total_processed - total_successful}")
    print(f"图像保存在: {SAVE_DIR}")
    print(f"\n生成的PM2.5排放差值图:")
    for i, file_path in enumerate(processed_files, 1):
        print(f"  {i}. {os.path.basename(file_path)}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
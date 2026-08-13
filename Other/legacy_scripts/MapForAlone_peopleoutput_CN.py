#!/usr/bin/env python
# coding: utf-8

import os
import sys
import re
from tqdm.auto import tqdm
import pandas as pd
import numpy as np
from PIL import Image

# 地图相关库
from esil.rsm_helper.model_property import model_attribute
from esil.map_helper import get_multiple_data, show_maps
import cmaps
import matplotlib.pyplot as plt

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['font.family'] = 'sans-serif'

# 确保所有元素都使用中文字体
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# 颜色映射（为不同污染物设置不同配色）
cmap_conc = cmaps.WhiteBlueGreenYellowRed
cmap_nox = cmaps.WhiteBlueGreenYellowRed  # NOX使用黄红配色
cmap_so2 = cmaps.WhiteBlueGreenYellowRed   # SO2使用蓝色系
cmap_nh3 = cmaps.WhiteBlueGreenYellowRed  # NH3使用绿色系
cmap_voc = cmaps.WhiteBlueGreenYellowRed # VOC使用紫色系


# -------------------------- 辅助函数（适配多污染物数据） --------------------------
def extract_key_period(period):
    """提取关键时期标签（仅适配指标文件中的时期）"""
    key_periods = ["DJF", "MAM", "JJA", "SON", 'Annual', 'Apr-Sep', 'top-10']
    return period if period in key_periods else None


def get_year(filename):
    """从指标文件名提取年份（适配格式：EM_{year}{month}_ALL_OnlyGuangDong.csv）"""
    match = re.search(r"EM_(\d{4})(\d{2})", filename)
    return match.group(1) if match else "2000"


def get_month(filename):
    """从指标文件名提取月份（适配格式：EM_{year}{month}_ALL_OnlyGuangDong.csv）"""
    match = re.search(r"EM_(\d{4})(\d{2})", filename)
    return match.group(2) if match else "01"


def get_month_name_cn(month_str):
    """将月份数字转换为中文月份名称"""
    month_names_cn = {
        '01': '1月', '02': '2月', '03': '3月', '04': '4月',
        '05': '5月', '06': '6月', '07': '7月', '08': '8月',
        '09': '9月', '10': '10月', '11': '11月', '12': '12月'
    }
    return month_names_cn.get(month_str, f'{month_str}月')


def get_dataset_label(variable):
    """适配多污染物数据列标签（中文版）"""
    label_map = {
        'PM2.5': "PM2.5",    # PM2.5
        'NOX': "NOX",        # NOX
        'SO2': "SO2",        # SO2
        'NH3': "NH3",        # NH3
        'VOC': "VOC",        # VOC
        'Population': "人口",   # 人口密度
        'Emission': "排放",     # 排放量
    }
    return label_map.get(variable, variable)


def get_variable_stats_type(variable):
    """从变量名提取统计类型"""
    if variable == 'PM2.5':
        return '浓度'
    elif variable in ['NOX', 'SO2', 'NH3', 'VOC']:
        return '排放速率'
    elif variable == 'Population':
        return '密度'
    elif variable == 'Emission':
        return '强度'
    return '浓度'


def collect_all_data_by_variable(root_metrics_dir, years, months, variables):
    """收集所有年月的有效数据，按变量分组用于自动计算统一图例范围"""
    variable_data = {var: [] for var in variables}

    for year in years:
        for month in months:
            # 拼接当前年月的指标文件路径（适配ALL文件）
            fusion_output_file = os.path.join(root_metrics_dir, f"EM_{year}{month}_ALL_OnlyGuangDong.csv")
            if not os.path.exists(fusion_output_file):
                print(f"警告：{year}年{month}月指标文件不存在（{fusion_output_file}），跳过该年月数据收集")
                continue

            try:
                df_data = pd.read_csv(fusion_output_file)
                # 按变量分组收集有效数据
                for var in variables:
                    if var not in df_data.columns:
                        continue
                    # 提取非空值
                    var_values = df_data[var].dropna().values
                    if len(var_values) > 0:
                        variable_data[var].extend(var_values)

            except Exception as e:
                print(f"{year}年{month}月数据收集失败：{str(e)}，跳过")
                continue

    # 检查每个变量是否有数据
    for var in variables:
        if not variable_data[var]:
            print(f"警告：变量 {var} 在所有年月中均无有效数据")

    return {var: np.array(values) if values else np.array([]) for var, values in variable_data.items()}


def calculate_variable_ranges(variable_data_dict):
    """按每个变量计算图例范围"""
    variable_ranges = {}

    for var, values in variable_data_dict.items():
        if len(values) > 0:
            # 计算0.5%和99.5%分位数（排除极端值）
            vmin = np.nanpercentile(values, 0.5)
            vmax = np.nanpercentile(values, 99.5)

            # 对于非PM2.5变量，如果最小值小于0.01，则设为0
            if var != 'PM2.5' and vmin < 0.01:
                vmin = 0

            variable_ranges[var] = (vmin, vmax)
            print(f"  {var}变量图例范围：{np.round(vmin, 6)} ~ {np.round(vmax, 6)}")
        else:
            print(f"  警告：{var}变量无有效数据，使用默认范围")
            # 设置默认范围
            if var == 'PM2.5':
                variable_ranges[var] = (0, 100)
            else:
                variable_ranges[var] = (0, 1e-6)

    return variable_ranges


def get_variable_cmap(variable):
    """获取变量对应的颜色映射"""
    cmap_map = {
        'PM2.5': cmap_conc,
        'NOX': cmap_nox,
        'SO2': cmap_so2,
        'NH3': cmap_nh3,
        'VOC': cmap_voc
    }
    return cmap_map.get(variable, cmap_conc)


# -------------------------- 核心画图函数（支持多污染物+按变量统一图例） --------------------------
def plot_multi_year_maps(
        root_metrics_dir,    # 多年指标文件根目录
        model_file,          # 模型文件（共用）
        save_root_path,      # 多年结果保存根目录
        years,               # 需要处理的年份列表
        months,              # 需要处理的月份列表（01-12）
        boundary_json_file=None,  # 边界文件（共用）
        variable_settings=None,   # 变量配置
        key_periods=None,         # 要画图的时期
        variable_unified_legend=True  # 按变量统一图例（每个变量使用自己的统一范围）
):
    # 初始化默认配置（多污染物版本）
    if variable_settings is None:
        variable_settings = {
            'variables': ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC'],  # 默认处理的污染物
            'settings': {
                'show_lonlat': True,             # 显示经纬度
                'is_wrf_out_data': True,         # 模型数据格式
                'show_original_grid': True,      # 显示网格线
                'title_fontsize': 14,            # 标题字体大小
                'xy_title_fontsize': 12,         # 经纬度标签字体大小
                'show_dependenct_colorbar': True,# 显示色条
                'show_domain_mean': True,        # 显示区域均值
                'show_grid_line': True,          # 显示网格线
                'colorbar_format': {             # 不同变量的格式
                    'PM2.5': '.2f',
                    'NOX': '.2f',
                    'SO2': '.2f',
                    'NH3': '.2f',
                    'VOC': '.2f'
                }
            }
        }
    variables = variable_settings['variables']
    plot_settings = variable_settings['settings']

    # 变量单位映射
    variable_units = {
        'PM2.5': 'μg/m³',
        'NOX': 'moles/s',
        'SO2': 'moles/s',
        'NH3': 'moles/s',
        'VOC': 'moles/s',
        'Population': '人/km²',
        'Emission': 'kg/km²·d',
    }

    # 默认时期（无指定则画所有时期）
    if key_periods is None:
        key_periods = ["DJF", "MAM", "JJA", "SON", 'Annual', 'Apr-Sep', 'top-10']

    # -------------------------- 按变量统一图例处理 --------------------------
    variable_ranges = {}
    
    if variable_unified_legend:
        # 按变量统一图例模式：为每个变量计算统一图例范围
        print("按变量统一图例模式：开始收集数据并计算各变量的图例范围...")
        variable_data_dict = collect_all_data_by_variable(root_metrics_dir, years, months, variables)
        variable_ranges = calculate_variable_ranges(variable_data_dict)

    # -------------------------- 读取模型投影和网格信息（共用，只读1次） --------------------------
    try:
        mp = model_attribute(model_file)
        proj = mp.projection
        longitudes = mp.lons  # 模型原始经度网格
        latitudes = mp.lats   # 模型原始纬度网格
        grid_shape = longitudes.shape  # 获取模型网格形状 (rows, cols)
        print(f"成功读取模型投影信息，网格形状：{grid_shape[0]} 行 × {grid_shape[1]} 列")
    except Exception as e:
        print(f"模型文件读取失败：{str(e)}，退出程序")
        return

    # -------------------------- 循环处理每个年月 --------------------------
    for year in years:
        for month in months:
            print(f"\n{'='*70}")
            print(f"开始处理 {year}年{month}月多污染物排放数据")
            print(f"{'='*70}")

            # 1. 拼接当前年月的指标文件路径（适配ALL文件）
            fusion_output_file = os.path.join(root_metrics_dir, f"EM_{year}{month}_ALL_OnlyGuangDong.csv")
            if not os.path.exists(fusion_output_file):
                print(f"警告：{year}年{month}月指标文件不存在（{fusion_output_file}），跳过该年月")
                continue

            # 2. 创建当前年份的保存目录
            save_single_path = os.path.join(save_root_path, str(year))
            if not os.path.exists(save_single_path):
                os.makedirs(save_single_path)
                print(f"自动创建 {year} 年地图保存目录：{save_single_path}")

            # 3. 读取当前年月的多污染物指标数据
            try:
                df_data = pd.read_csv(fusion_output_file)
                print(f"成功读取 {year}年{month}月多污染物指标文件（共{len(df_data)}行）")
            except Exception as e:
                print(f"{year}年{month}月指标文件读取失败：{str(e)}，跳过该年月")
                continue

            # 4. 检查关键列
            required_cols = ["ROW", "COL"] + variables
            missing_cols = [col for col in required_cols if col not in df_data.columns]
            if missing_cols:
                print(f"{year}年{month}月指标文件缺少关键列：{missing_cols}，跳过该年月")
                continue

            # 5. 验证数据长度是否匹配模型网格
            if len(df_data) != grid_shape[0] * grid_shape[1]:
                raise ValueError(f"{year}年{month}月数据长度({len(df_data)})与模型网格尺寸({grid_shape[0]}×{grid_shape[1]}={grid_shape[0]*grid_shape[1]})不匹配")

            # 6. 为每个污染物变量绘制地图
            for variable in variables:
                print(f"\n处理 {variable}...")
                
                if df_data[variable].isna().all():
                    print(f"{year}年{month}月的{variable}列全为缺失值，跳过")
                    continue

                # 数据重塑（严格匹配模型网格形状）
                df_sorted = df_data.sort_values(by=["ROW", "COL"])
                grid_data = df_sorted[variable].values.reshape(grid_shape)

                # 中文版地图标题
                dataset_label = get_dataset_label(variable)
                month_name_cn = get_month_name_cn(month)
                title = f"{month_name_cn} {dataset_label}: {year}"

                # 准备地图数据
                map_data = {}
                get_multiple_data(
                    map_data,
                    dataset_name=title,
                    variable_name="",
                    grid_x=longitudes,
                    grid_y=latitudes,
                    grid_concentration=grid_data
                )

                # -------------------------- 图例范围处理 --------------------------
                current_value_range = None
                current_unit = variable_units.get(variable, 'g/s')
                current_cmap = get_variable_cmap(variable)
                
                # 获取颜色条格式
                if isinstance(plot_settings['colorbar_format'], dict):
                    current_colorbar_format = plot_settings['colorbar_format'].get(variable, '.2f')
                else:
                    current_colorbar_format = plot_settings['colorbar_format']

                if variable_unified_legend and variable in variable_ranges:
                    # 使用该变量的统一图例范围
                    current_value_range = variable_ranges[variable]
                    print(f"  使用{variable}变量统一图例范围：{np.round(current_value_range[0], 6)} ~ {np.round(current_value_range[1], 6)} {current_unit}")
                else:
                    # 为当前文件计算独立的图例范围
                    var_data = df_sorted[variable].dropna().values
                    if len(var_data) > 0:
                        current_vmin = np.nanpercentile(var_data, 0.5)
                        current_vmax = np.nanpercentile(var_data, 99.5)

                        # 对于非PM2.5变量，如果最小值小于0.01，则设为0
                        if variable != 'PM2.5' and current_vmin < 0.01:
                            current_vmin = 0

                        current_value_range = (current_vmin, current_vmax)
                        print(f"  使用独立图例范围：{np.round(current_vmin, 6)} ~ {np.round(current_vmax, 6)} {current_unit}")
                    else:
                        # 设置默认范围
                        if variable == 'PM2.5':
                            current_value_range = (0, 100)
                        else:
                            current_value_range = (0, 1e-6)
                        print(f"  数据为空，使用默认图例范围：{current_value_range[0]} ~ {current_value_range[1]} {current_unit}")

                # 绘制并保存
                try:
                    fig = show_maps(
                        map_data,
                        unit=current_unit,
                        cmap=current_cmap,
                        show_lonlat=plot_settings['show_lonlat'],
                        projection=proj,
                        is_wrf_out_data=plot_settings['is_wrf_out_data'],
                        boundary_file=boundary_json_file,
                        show_original_grid=plot_settings['show_original_grid'],
                        title_fontsize=plot_settings['title_fontsize'],
                        xy_title_fontsize=plot_settings['xy_title_fontsize'],
                        show_dependenct_colorbar=plot_settings['show_dependenct_colorbar'],
                        value_range=current_value_range,
                        show_domain_mean=plot_settings['show_domain_mean'],
                        show_grid_line=plot_settings['show_grid_line'],
                        colorbar_ticks_value_format=current_colorbar_format
                    )

                    # 保存高清图片
                    save_file = os.path.join(save_single_path, f"{year}{month}_{variable}.png")
                    fig.savefig(save_file, dpi=300, bbox_inches='tight')
                    plt.close(fig)  # 关闭图形释放内存
                    print(f"✅ {year}年{month}月 {variable} 地图保存成功：{save_file}")
                except Exception as e:
                    print(f"❌ {year}年{month}月的{variable}地图失败：{str(e)}，跳过")


# -------------------------- 执行入口 --------------------------
if __name__ == "__main__":
    print("="*70)
    print("          开始批量绘制 多年月多污染物排放分布地图（中文版）          ")
    print("="*70)

    # -------------------------- 核心参数配置 --------------------------
    # 1. 基础路径配置
    ROOT_METRICS_DIR = "/data/workspace/GuangDong/emissionlist"  # 多年指标文件根目录
    MODEL_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"  # 模型网格文件
    BOUNDARY_JSON_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json" # 边界文件
    SAVE_ROOT_PATH = "/data/workspace/GuangDong/MultiPollutant_Plots_CN"  # 结果保存根目录

    # 2. 年份与月份配置
    TARGET_YEARS = [2023, 2000]  # 需要处理的年份
    TARGET_MONTHS = ["01", "07"]  # 需要处理的月份（01-12）

    # 3. 变量配置（指定要绘制的污染物）
    TARGET_VARIABLES = ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC']
    
    # 4. 图例配置（按变量统一图例）
    VARIABLE_UNIFIED_LEGEND = True  # 按变量统一图例

    # 5. 自定义变量设置
    variable_settings = {
        'variables': TARGET_VARIABLES,
        'settings': {
            'show_lonlat': True,
            'is_wrf_out_data': True,
            'show_original_grid': True,
            'title_fontsize': 14,
            'xy_title_fontsize': 12,
            'show_dependenct_colorbar': True,
            'show_domain_mean': True,
            'show_grid_line': True,
            'colorbar_format': {
                'PM2.5': '.2f',      # PM2.5保留1位小数
                'NOX': '.2f',        # 气体污染物使用科学计数法
                'SO2': '.2f',
                'NH3': '.2f',
                'VOC': '.2f'
            }
        }
    }

    # -------------------------- 调用批量画图函数 --------------------------
    plot_multi_year_maps(
        root_metrics_dir=ROOT_METRICS_DIR,
        model_file=MODEL_FILE,
        save_root_path=SAVE_ROOT_PATH,
        years=TARGET_YEARS,
        months=TARGET_MONTHS,
        boundary_json_file=BOUNDARY_JSON_FILE,
        variable_settings=variable_settings,
        key_periods=None,
        variable_unified_legend=VARIABLE_UNIFIED_LEGEND
    )

    print(f"\n✅ 所有年月多污染物地图绘制完成！（按变量统一图例模式）")
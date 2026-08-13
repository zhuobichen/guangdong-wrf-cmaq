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

# 颜色映射
cmap_conc = cmaps.WhiteBlueGreenYellowRed


# -------------------------- 辅助函数（适配气象数据） --------------------------
def extract_key_period(period):
    """提取关键时期标签（仅适配指标文件中的时期）"""
    key_periods = ["DJF", "MAM", "JJA", "SON", 'Annual', 'Apr-Sep', 'top-10']
    return period if period in key_periods else None


def get_year(filename):
    """从气象输出文件名提取年份（适配格式：YYYY_mcipout_MM.csv）"""
    match = re.search(r"^(\d{4})_mcipout", os.path.basename(filename))
    return match.group(1) if match else "2023"


def get_month(filename):
    """从气象输出文件名提取月份（适配格式：YYYY_mcipout_MM.csv）"""
    match = re.search(r"_(\d{2})\.csv$", os.path.basename(filename))
    return match.group(1) if match else "01"


def get_month_name_cn(month_str):
    """将月份数字转换为中文月份名称"""
    month_names_cn = {
        '01': '1月', '02': '2月', '03': '3月', '04': '4月',
        '05': '5月', '06': '6月', '07': '7月', '08': '8月',
        '09': '9月', '10': '10月', '11': '11月', '12': '12月'
    }
    return month_names_cn.get(month_str, f'{month_str}月')


def get_dataset_label(variable):
    """适配气象变量数据列标签（中文版使用简短变量名）"""
    label_map = {
        'TA_mean': 'TEMP',
        'TA_max': 'TA_Max',
        'SOL_RAD_mean': 'SOL_RAD',
        'SOL_RAD_max': 'SOL_RAD_Max',
        'PBLH_mean': 'PBLH',
        'PBLH_max': 'PBLH_Max',
        'Temp_Days_35C': 'Temp_Days_35C',  # 温度超标天数
    }
    return label_map.get(variable, variable)


def get_variable_stats_type(variable):
    """从变量名提取统计类型（Mean或Max）"""
    if '_max' in variable:
        return '最大值'
    elif '_mean' in variable:
        return '平均值'
    return '平均值'  # 默认为平均值


def collect_all_data(root_metrics_dir, years, months, variables):
    """收集所有年月的有效数据，用于自动计算统一图例范围（适配{year}_mcipout_{month}.csv格式）"""
    all_values = []
    for year in years:
        for month in months:
            # 拼接当前年月的指标文件路径
            fusion_output_file = os.path.join(root_metrics_dir, f"{year}_mcipout_{month}_land.csv")
            if not os.path.exists(fusion_output_file):
                print(f"警告：{year}年{month}月指标文件不存在（{fusion_output_file}），跳过该年月数据收集")
                continue

            try:
                df_data = pd.read_csv(fusion_output_file)
                # 直接收集所有变量的有效数据（简化格式无Period列）
                for var in variables:
                    # 使用实际的列名（可能在某些年份中变量名不同）
                    if var not in df_data.columns:
                        print(f"警告：变量 {var} 在{year}年{month}月数据中不存在，可用列：{list(df_data.columns)}")
                        continue
                    # 提取非空值
                    var_values = df_data[var].dropna().values
                    if len(var_values) > 0:
                        all_values.extend(var_values)

            except Exception as e:
                print(f"{year}年{month}月数据收集失败：{str(e)}，跳过")
                continue

    if not all_values:
        raise ValueError("所有年月均无有效数据，无法计算图例范围")
    return np.array(all_values)


def collect_all_data_by_variable(root_metrics_dir, years, months, variables):
    """收集所有年月的有效数据，按变量分组用于自动计算统一图例范围"""
    variable_data = {var: [] for var in variables}

    for year in years:
        for month in months:
            # 拼接当前年月的指标文件路径
            fusion_output_file = os.path.join(root_metrics_dir, f"{year}_mcipout_{month}.csv")
            if not os.path.exists(fusion_output_file):
                print(f"警告：{year}年{month}月指标文件不存在（{fusion_output_file}），跳过该年月数据收集")
                continue

            try:
                df_data = pd.read_csv(fusion_output_file)
                print(f"  {year}年{month}月数据列：{list(df_data.columns)}")
                
                # 按变量分组收集有效数据
                for var in variables:
                    if var not in df_data.columns:
                        continue
                    # 提取非空值
                    var_values = df_data[var].dropna().values
                    if len(var_values) > 0:
                        variable_data[var].extend(var_values)
                        print(f"    {var}: 有效数据{len(var_values)}个")

            except Exception as e:
                print(f"{year}年{month}月数据收集失败：{str(e)}，跳过")
                continue

    # 检查每个变量是否有数据
    for var in variables:
        if not variable_data[var]:
            print(f"警告：变量 {var} 在所有年月中均无有效数据")
        else:
            print(f"  {var}: 总计有效数据{len(variable_data[var])}个")

    return {var: np.array(values) if values else np.array([]) for var, values in variable_data.items()}


def get_variable_groups():
    """定义变量分组，同一组变量共用图例"""
    return {
        'temperature': ['TA_mean', 'TA_max'],
        'solar_radiation': ['SOL_RAD_mean', 'SOL_RAD_max'],
        'boundary_layer': ['PBLH_mean', 'PBLH_max'],
        'temp_exceed': ['Temp_Days_35C']  # 温度超标天数单独一组
    }


def calculate_variable_group_ranges(variable_data_dict):
    """按变量分组计算图例范围"""
    variable_groups = get_variable_groups()
    group_ranges = {}

    for group_name, group_variables in variable_groups.items():
        group_values = []

        for var in group_variables:
            if var in variable_data_dict and len(variable_data_dict[var]) > 0:
                group_values.extend(variable_data_dict[var])
                print(f"    {group_name}组-{var}: {len(variable_data_dict[var])}个数据点")

        if group_values:
            group_values = np.array(group_values)
            # 计算0.5%和99.5%分位数（排除极端值）
            vmin = np.nanpercentile(group_values, 0.5)
            vmax = np.nanpercentile(group_values, 99.5)
            group_ranges[group_name] = (vmin, vmax)
            print(f"  {group_name}组图例范围：{np.round(vmin, 2)} ~ {np.round(vmax, 2)}")
        else:
            print(f"  警告：{group_name}组无有效数据")
            group_ranges[group_name] = (0, 1)  # 默认范围

    return group_ranges


def get_variable_group(variable):
    """获取变量所属的组名"""
    variable_groups = get_variable_groups()
    for group_name, group_variables in variable_groups.items():
        if variable in group_variables:
            return group_name
    return 'default'


# -------------------------- 核心画图函数（支持多年+自动计算图例） --------------------------
def plot_multi_year_maps(
        root_metrics_dir,    # 多年指标文件根目录
        model_file,          # 模型文件（共用）
        save_root_path,      # 多年结果保存根目录
        years,               # 需要处理的年份列表
        months,              # 需要处理的月份列表（01-12）
        boundary_json_file=None,  # 边界文件（共用）
        variable_settings=None,   # 变量配置（适配气象数据）
        key_periods=None,         # 要画图的时期
        unified_value_range=None, # 所有年份共用的图例范围（可自动计算）
        unified_legend=False,     # 是否使用统一图例：True=统一计算，False=分开计算（默认）
        variable_grouped_legend=False  # 新增：是否按变量分组统一图例
):
    # 初始化默认配置（气象数据专属配置）
    if variable_settings is None:
        variable_settings = {
            # 处理输入数据中的所有气象变量
            'variables': ['TA_mean', 'SOL_RAD_mean', 'PBLH_mean', 'TA_max', 'SOL_RAD_max', 'PBLH_max'],
            'settings': {
                'unit': "°C",                  # 默认单位，温度用°C
                'cmap_conc': cmap_conc,        # 颜色映射
                'show_lonlat': True,           # 显示经纬度
                'is_wrf_out_data': True,       # 模型数据格式
                'show_original_grid': True,    # 显示网格线
                'title_fontsize': 14,          # 标题字体大小
                'xy_title_fontsize': 12,       # 经纬度标签字体大小
                'show_dependenct_colorbar': True,# 显示色条
                'show_domain_mean': True,      # 显示区域均值
                'show_grid_line': True,        # 显示网格线
                'value_range': None,           # 统一用外部传入的图例范围
                'colorbar_format': '.1f',      # 保留一位小数的格式
            },
        }
    variables = variable_settings['variables']
    plot_settings = variable_settings['settings']

    # 变量单位映射
    variable_units = {
        'TA_mean': '°C',
        'TA_max': '°C',
        'SOL_RAD_mean': 'W/m²',
        'SOL_RAD_max': 'W/m²',
        'PBLH_mean': 'm',
        'PBLH_max': 'm',
        'Temp_Days_35C': '天',
        'Heatwave_Days':'Days'
    }

    # 变量颜色条格式映射
    variable_formats = {
        'TA_mean': '.1f',        # 温度保留1位小数
        'TA_max': '.1f',         # 温度保留1位小数
        'SOL_RAD_mean': '.0f',   # 太阳辐射整数
        'SOL_RAD_max': '.0f',    # 太阳辐射整数
        'PBLH_mean': '.0f',      # 边界层高度整数
        'PBLH_max': '.0f',      # 边界层高度整数
        'Temp_Days_35C': '.0f',  # 温度超标天数整数
        'Heatwave_Days': '.0f'   # 温度超标天数整数
    }

    # 默认时期（无指定则画所有时期）
    if key_periods is None:
        key_periods = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # -------------------------- 图例范围处理（手动统一优先） --------------------------
    manual_range_valid = False
    if unified_legend and unified_value_range is not None and isinstance(unified_value_range, tuple) and len(unified_value_range) == 2:
        vmin, vmax = unified_value_range
        if isinstance(vmin, (int, float)) and isinstance(vmax, (int, float)) and vmin < vmax:
            manual_range_valid = True
            print(f"手动统一图例优先：使用传入范围 {vmin} ~ {vmax}")
        else:
            print("警告：传入的统一图例范围无效，将按后续规则计算")
            unified_value_range = None

    variable_group_ranges = {}
    if variable_grouped_legend and not manual_range_valid:
        print("按变量分组统一图例模式：开始收集数据并计算各变量组的图例范围...")
        variable_data_dict = collect_all_data_by_variable(root_metrics_dir, years, months, variables)
        variable_group_ranges = calculate_variable_group_ranges(variable_data_dict)
    elif unified_legend and not manual_range_valid:
        print("统一图例模式：开始收集所有年月数据并自动计算...")
        all_data = collect_all_data(root_metrics_dir, years, months, variables)
        vmin = np.nanpercentile(all_data, 0.5)
        vmax = np.nanpercentile(all_data, 99.5)
        unified_value_range = (vmin, vmax)
        print(f"自动计算所有年月统一图例范围：{np.round(vmin, 2)} ~ {np.round(vmax, 2)}")
    elif not manual_range_valid:
        # 分开图例模式：每个文件独立计算图例范围
        print("分开图例模式：每个文件将独立计算其图例范围")

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
            print(f"\n{'='*60}")
            print(f"开始处理 {year}年{month}月气象数据")
            print(f"{'='*60}")

            # 1. 拼接当前年月的指标文件路径
            fusion_output_file = os.path.join(root_metrics_dir, f"{year}_mcipout_{month}_land.csv")
            if not os.path.exists(fusion_output_file):
                print(f"警告：{year}年{month}月指标文件不存在（{fusion_output_file}），跳过该年月")
                continue

            # 2. 创建当前年份的保存目录
            save_single_path = os.path.join(save_root_path, str(year))
            if not os.path.exists(save_single_path):
                os.makedirs(save_single_path)
                print(f"自动创建 {year} 年地图保存目录：{save_single_path}")

            # 3. 读取当前年月的气象指标数据
            try:
                df_data = pd.read_csv(fusion_output_file)
                print(f"成功读取 {year}年{month}月气象指标文件（共{len(df_data)}行）")
                print(f"数据列：{list(df_data.columns)}")
                
                # 检查必需的列
                required_cols = ['ROW', 'COL']
                missing_cols = [col for col in required_cols if col not in df_data.columns]
                if missing_cols:
                    print(f"错误：缺少必需的列 {missing_cols}")
                    continue
                    
            except Exception as e:
                print(f"{year}年{month}月指标文件读取失败：{str(e)}，跳过该年月")
                continue

            # 4. 检查数据中的变量列
            available_vars = [var for var in variables if var in df_data.columns]
            if not available_vars:
                print(f"警告：{year}年{month}月数据中没有可处理的变量列")
                continue
            print(f"可处理的变量：{available_vars}")

            print(f"{year}年{month}月开始绘制气象变量分布图")

            for variable in available_vars:
                # 检查该变量是否有数据
                if df_data[variable].isna().all():
                    print(f"{year}年{month}月的{variable}列全为缺失值，跳过")
                    continue
                    
                # 统计有效数据
                valid_count = df_data[variable].notna().sum()
                print(f"  {variable}: 有效数据{valid_count}个，缺失数据{len(df_data)-valid_count}个")

                # 数据重塑（严格匹配模型网格形状）
                df_sorted = df_data.sort_values(by=["ROW", "COL"])
                grid_data = df_sorted[variable].values.reshape(grid_shape)  # 使用模型网格形状重塑

                # 中文版地图标题：1月 PBLH: 2000
                dataset_label = get_dataset_label(variable)
                stats_type = get_variable_stats_type(variable)
                month_name_cn = get_month_name_cn(month)
                title = f"{month_name_cn} {dataset_label}: {year}"

                # 准备地图数据（使用模型原始经纬度网格）
                map_data = {}
                get_multiple_data(
                    map_data,
                    dataset_name=title,
                    variable_name="",
                    grid_x=longitudes,  # 模型原始经度网格
                    grid_y=latitudes,   # 模型原始纬度网格
                    grid_concentration=grid_data
                )

                # -------------------------- ✅ 修复2：重构图例范围逻辑，保证手动范围最高优先级 --------------------------
                # 变量单位和格式适配
                current_unit = variable_units.get(variable, plot_settings['unit'])
                current_colorbar_format = variable_formats.get(variable, plot_settings['colorbar_format'])
                
                # 核心优先级：手动指定范围 > 分组范围 > 独立计算范围
                current_value_range = None
                if manual_range_valid:
                    # ✅ 最高优先级：强制使用手动指定的统一范围
                    current_value_range = unified_value_range
                    print(f"  ✅ 强制生效：手动指定图例范围 {np.round(current_value_range[0],2)} ~ {np.round(current_value_range[1],2)} {current_unit}")
                else:
                    # 无手动范围时，按原有逻辑执行
                    if variable_grouped_legend:
                        var_group = get_variable_group(variable)
                        if var_group in variable_group_ranges:
                            current_value_range = variable_group_ranges[var_group]
                            print(f"  使用{var_group}组统一图例范围：{np.round(current_value_range[0], 2)} ~ {np.round(current_value_range[1], 2)} {current_unit}")
                        else:
                            var_data = df_sorted[variable].dropna().values
                            current_vmin = np.nanpercentile(var_data, 0.5) if len(var_data)>0 else 0
                            current_vmax = np.nanpercentile(var_data, 99.5) if len(var_data)>0 else 1
                            current_value_range = (current_vmin, current_vmax)
                            print(f"  变量组无数据，使用独立图例范围：{np.round(current_value_range[0], 2)} ~ {np.round(current_value_range[1], 2)} {current_unit}")
                    elif unified_legend:
                        current_value_range = unified_value_range
                        print(f"  使用全局统一图例范围：{np.round(current_value_range[0], 2)} ~ {np.round(current_value_range[1], 2)} {current_unit}")
                    else:
                        var_data = df_sorted[variable].dropna().values
                        current_vmin = np.nanpercentile(var_data, 0.5) if len(var_data)>0 else 0
                        current_vmax = np.nanpercentile(var_data, 99.5) if len(var_data)>0 else 1
                        current_value_range = (current_vmin, current_vmax)
                        print(f"  使用独立图例范围：{np.round(current_vmin, 2)} ~ {np.round(current_vmax, 2)} {current_unit}")

                # 绘制并保存
                try:
                    fig = show_maps(
                        map_data,
                        unit=current_unit,
                        cmap=plot_settings['cmap_conc'],
                        show_lonlat=plot_settings['show_lonlat'],
                        projection=proj,
                        is_wrf_out_data=plot_settings['is_wrf_out_data'],
                        boundary_file=boundary_json_file,
                        show_original_grid=plot_settings['show_original_grid'],
                        title_fontsize=plot_settings['title_fontsize'],
                        xy_title_fontsize=plot_settings['xy_title_fontsize'],
                        show_dependenct_colorbar=plot_settings['show_dependenct_colorbar'],
                        value_range=current_value_range,  # 最终生效的图例范围
                        show_domain_mean=plot_settings['show_domain_mean'],
                        show_grid_line=plot_settings['show_grid_line'],
                        colorbar_format=current_colorbar_format
                    )

                    # 保存高清图片 - 中文版文件名
                    save_file = os.path.join(save_single_path, f"{year}{month}_{variable}.png")
                    fig.savefig(save_file, dpi=300, bbox_inches='tight')
                    plt.close(fig)  # 关闭图形释放内存
                    legend_mode = "按变量分组统一" if variable_grouped_legend else ("统一" if unified_legend else "独立")
                    print(f"✅ {year}年{month}月 {variable} 地图保存成功（{legend_mode}图例）：{save_file}")
                except Exception as e:
                    print(f"❌ {year}年{month}月的{variable}地图失败：{str(e)}，跳过")
                    import traceback
                    traceback.print_exc()


# -------------------------- 执行入口 --------------------------
if __name__ == "__main__":
    print("="*70)
    print("          开始批量绘制 多年月气象变量分布地图（中文版）          ")
    print("="*70)

    # -------------------------- 核心参数配置 --------------------------
    # 1. 基础路径配置
    ROOT_METRICS_DIR = "/data/workspace/GuangDong/mcipout_processed_land"  # 多年指标文件根目录
    MODEL_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"  # 模型网格文件
    BOUNDARY_JSON_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json" # 边界文件
    SAVE_ROOT_PATH = "/data/workspace/GuangDong/Mcip_Alone_Plots_CN_land"  # 结果保存根目录

    # 2. 年份与月份配置
    TARGET_YEARS = [2000]  # 需要处理的年份
    TARGET_MONTHS = ["07"]  # 需要处理的月份（01-12）

    # 3. 变量配置（处理输入数据中的所有列）
    TARGET_VARIABLES = ['SOL_RAD_mean']

    # 4. 图例配置（手动统一范围将优先生效）
    UNIFIED_VALUE_RANGE = (0, 370)
    UNIFIED_LEGEND = True # 图例模式：True=统一图例，False=分开计算（默认）
    VARIABLE_GROUPED_LEGEND = True  # 按变量分组统一图例

    # -------------------------- 调用批量画图函数 --------------------------
    custom_variable_settings = {
        'variables': TARGET_VARIABLES,
        'settings': {
            'unit': "Days",
            'cmap_conc': cmap_conc,
            'show_lonlat': True,
            'is_wrf_out_data': True,
            'show_original_grid': True,
            'title_fontsize': 14,
            'xy_title_fontsize': 12,
            'show_dependenct_colorbar': True,
            'show_domain_mean': True,
            'show_grid_line': True,
            'value_range': None,
            'colorbar_format': '.0f',
        },
    }

    plot_multi_year_maps(
        root_metrics_dir=ROOT_METRICS_DIR,
        model_file=MODEL_FILE,
        save_root_path=SAVE_ROOT_PATH,
        years=TARGET_YEARS,
        months=TARGET_MONTHS,
        boundary_json_file=BOUNDARY_JSON_FILE,
        variable_settings=custom_variable_settings,
        key_periods=None,
        unified_value_range=UNIFIED_VALUE_RANGE,
        unified_legend=UNIFIED_LEGEND,
        variable_grouped_legend=VARIABLE_GROUPED_LEGEND
    )

    if VARIABLE_GROUPED_LEGEND:
        legend_mode_text = "按变量分组统一图例"
    elif UNIFIED_LEGEND:
        legend_mode_text = "统一图例"
    else:
        legend_mode_text = "分开图例"
    print(f"\n✅ 所有年月气象变量地图绘制完成！（{legend_mode_text}模式）")
    print(f"处理的变量：{TARGET_VARIABLES}")
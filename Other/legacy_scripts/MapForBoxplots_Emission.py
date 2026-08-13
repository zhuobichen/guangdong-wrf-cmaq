#!/usr/bin/env python
# coding: utf-8

import os
import sys
import re
from tqdm.auto import tqdm
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from PIL import Image

# 地图相关库
from esil.rsm_helper.model_property import model_attribute
from esil.map_helper import get_multiple_data, show_maps
import cmaps

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['font.family'] = 'sans-serif'

# 确保所有元素都使用中文字体
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# 颜色映射（与MapForDiffrenceBetweenDatasets_emission_CN.py保持一致）
cmap_conc = cmaps.WhiteBlueGreenYellowRed  # PM2.5使用
cmap_nox = cmaps.WhiteBlueGreenYellowRed  # NOX使用
cmap_so2 = cmaps.WhiteBlueGreenYellowRed  # SO2使用
cmap_nh3 = cmaps.WhiteBlueGreenYellowRed  # NH3使用
cmap_voc = cmaps.WhiteBlueGreenYellowRed  # VOC使用

# === CASE映射配置 ===
# 与MapForDiffrenceBetweenDatasets_emission_CN.py保持一致的CASE定义
CASE_DEFINITIONS = {
    # CASE: (Emission, met, 描述)
    'CASE1': ('2000', '2000', '2000e2000m'),  # 2000 vs 2000
    'CASE2': ('2000', '2023', '2000e2023m'),  # 2000 vs 2023
    'CASE3': ('2023', '2023', '2023e2023m'),  # 2023 vs 2023
    'CASE4': ('2023', '2000', '2023e2000m'),  # 2023 vs 2000
    'CASE5': ('2060', '2060', '2060e2060m'),  # 2060 vs 2060
    'CASE6': ('2030', '2030', '2030e2030m'),  # 2030 vs 2030
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

# 指定要绘制的Case
TARGET_CASE = 'CASE1'  # 只绘制Case4
TARGET_MONTHS = ["01", "07"]  # 要绘制的月份

# -------------------------- 辅助函数（适配简化CMAQ数据） --------------------------
def extract_key_period(period):
    """提取关键时期标签（仅适配指标文件中的时期）"""
    key_periods = ["DJF", "MAM", "JJA", "SON", 'Annual', 'Apr-Sep', 'top-10']
    return period if period in key_periods else None


def get_case_filename_pattern(case_id, month):
    """根据Case ID生成对应的文件名模式"""
    if case_id not in CASE_DEFINITIONS:
        raise ValueError(f"不支持的Case ID: {case_id}")
    
    emission_year, met_year, case_key = CASE_DEFINITIONS[case_id]
    
    # 生成可能的文件名模式
    patterns = [
        f"{emission_year}_Emission[{met_year}met]_{month}.csv",
        f"{case_key}_{month}.csv",
        f"{case_id}_{month}.csv",
        f"{emission_year}e{met_year}m_{month}.csv"
    ]
    
    return patterns


def find_case_file(case_id, month, root_dir):
    """根据Case ID查找对应的文件"""
    patterns = get_case_filename_pattern(case_id, month)
    
    for pattern in patterns:
        filepath = os.path.join(root_dir, pattern)
        if os.path.exists(filepath):
            return filepath
    
    # 模糊匹配
    for file in os.listdir(root_dir):
        if file.endswith(f"_{month}.csv"):
            # 检查是否包含Case对应的年份组合
            emission_year, met_year, _ = CASE_DEFINITIONS[case_id]
            if (emission_year in file and met_year in file) or CASE_DEFINITIONS[case_id][2] in file:
                return os.path.join(root_dir, file)
    
    return None


def get_month_name_cn(month_str):
    """将月份数字转换为中文月份名称"""
    month_names_cn = {
        '01': '1月', '02': '2月', '03': '3月', '04': '4月',
        '05': '5月', '06': '6月', '07': '7月', '08': '8月',
        '09': '9月', '10': '10月', '11': '11月', '12': '12月'
    }
    return month_names_cn.get(month_str, f'{month_str}月')


def get_case_number(case_str):
    """从CASE字符串中提取数字"""
    if case_str is None:
        return "UNKNOWN"
    
    match = re.search(r'CASE(\d+)', case_str)
    if match:
        return match.group(1)
    
    return case_str


def get_dataset_label(variable):
    """适配CMAQ变量数据列标签"""
    label_map = {
        'O3': 'O3',
        'PM2.5': 'PM2.5',
        'O3_Days': 'O3≥80ppb Days',
        'PM2.5_Days': 'PM2.5≥75μg/m³ Days',
    }
    return label_map.get(variable, variable)


def collect_case_data(root_metrics_dir, case_id, months, variables):
    """收集指定Case的所有数据，用于自动计算统一图例范围"""
    # 分离超标天数变量和其他变量
    days_variables = [var for var in variables if var in ['O3_Days', 'PM2.5_Days']]
    other_variables = [var for var in variables if var not in ['O3_Days', 'PM2.5_Days']]

    days_values = []  # 超标天数变量的所有值
    other_values = []  # 其他变量的所有值

    for month in months:
        fusion_output_file = find_case_file(case_id, month, root_metrics_dir)
        
        if fusion_output_file is None:
            print(f"警告：{case_id} {month}月文件不存在，跳过该月数据收集")
            continue

        try:
            df_data = pd.read_csv(fusion_output_file)
            # 分别收集超标天数变量和其他变量的有效数据
            for var in variables:
                if var not in df_data.columns:
                    continue
                # 提取非空值
                var_values = df_data[var].dropna().values
                if len(var_values) > 0:
                    if var in ['O3_Days', 'PM2.5_Days']:
                        days_values.extend(var_values)
                    else:
                        other_values.extend(var_values)

        except Exception as e:
            print(f"{case_id} {month}月数据收集失败：{str(e)}，跳过")
            continue

    if not days_values and not other_values:
        raise ValueError(f"{case_id} 所有月份均无有效数据，无法计算图例范围")

    return np.array(days_values), np.array(other_values)


# -------------------------- 核心画图函数（支持Case反推） --------------------------
def plot_case_maps(
        root_metrics_dir,    # 指标文件根目录
        model_file,          # 模型文件（共用）
        save_root_path,      # 结果保存根目录
        case_id,             # 要绘制的Case ID
        months,              # 需要处理的月份列表（01-12）
        boundary_json_file=None,  # 边界文件（共用）
        variable_settings=None,   # 变量配置（适配CMAQ）
        key_periods=None,         # 要画图的时期
        unified_value_range=None, # 所有月份共用的图例范围（可自动计算）
        unified_legend=False      # 是否使用统一图例：True=统一计算，False=分开计算（默认）
):
    # 初始化默认配置
    if variable_settings is None:
        variable_settings = {
            'variables': ['O3', 'PM2.5','PM2.5_Days', 'O3_Days'],  # 支持的变量列表
            'settings': {
                'unit': "μg/m³",                # 默认单位，O3和PM2.5用μg/m³
                'cmap_conc': cmap_conc,          # 颜色映射
                'show_lonlat': True,             # 显示经纬度
                'is_wrf_out_data': True,         # 模型数据格式
                'show_original_grid': True,      # 显示网格线
                'title_fontsize': 14,            # 标题字体大小
                'xy_title_fontsize': 12,         # 经纬度标签字体大小
                'show_dependenct_colorbar': True,# 显示色条
                'show_domain_mean': True,        # 显示区域均值
                'show_grid_line': True,          # 显示网格线
                'value_range': None, # 统一用外部传入的图例范围
                'colorbar_format': '.0f',  # 超标天数不保留小数
            }
        }
    variables = variable_settings['variables']
    plot_settings = variable_settings['settings']

    # 变量单位映射
    variable_units = {
        'O3': 'ppb',
        'PM2.5': 'μg/m³',
        'O3_Days': 'days',
        'PM2.5_Days': 'days'
    }

    # 变量颜色条格式映射
    variable_formats = {
        'O3': '.1f',        # 浓度保留1位小数
        'PM2.5': '.1f',     # 浓度保留1位小数
        'O3_Days': '.0f',   # 超标天数不保留小数
        'PM2.5_Days': '.0f' # 超标天数不保留小数
    }

    # 获取Case信息
    if case_id not in CASE_DEFINITIONS:
        raise ValueError(f"不支持的Case ID: {case_id}，仅支持CASE1到CASE6")
    
    emission_year, met_year, case_key = CASE_DEFINITIONS[case_id]
    case_num = get_case_number(case_id)
    case_label = f"Case{case_num}"
    
    print(f"\n{'='*60}")
    print(f"开始处理 {case_label} ({case_key})")
    print(f"排放年份: {emission_year}, 气象年份: {met_year}")
    print(f"{'='*60}")

    # 默认时期
    if key_periods is None:
        key_periods = ["DJF", "MAM", "JJA", "SON", 'Annual', 'Apr-Sep', 'top-10']

    # -------------------------- 图例范围处理 --------------------------
    if unified_legend:
        # 统一图例模式：预先计算该Case所有数据的图例范围
        if unified_value_range is None or (unified_value_range[0] is None and unified_value_range[1] is None):
            print(f"{case_label} 统一图例模式：开始收集所有月份数据并自动计算...")
            days_data, other_data = collect_case_data(root_metrics_dir, case_id, months, variables)

            # 分别计算超标天数变量和其他变量的图例范围
            days_vmin = days_vmax = None
            other_vmin = other_vmax = None

            if len(days_data) > 0:
                # 超标天数使用最大最小值
                days_vmin = np.nanmin(days_data)
                days_vmax = np.nanmax(days_data)
                print(f"{case_label} 超标天数变量统一图例范围：{np.round(days_vmin, 2)} ~ {np.round(days_vmax, 2)} days")

            if len(other_data) > 0:
                # 其他变量使用百分位数
                other_vmin = np.nanpercentile(other_data, 0.5)
                other_vmax = np.nanpercentile(other_data, 99.5)
                print(f"{case_label} 其他变量统一图例范围：{np.round(other_vmin, 2)} ~ {np.round(other_vmax, 2)}")

            # 存储两种类型的图例范围
            unified_value_range = {
                'days': (0, 15) if days_vmin is None else (days_vmin, days_vmax),
                'other': (other_vmin, other_vmax) if other_vmin is not None else (0, 100)
            }
        else:
            print(f"{case_label} 统一图例模式：使用手动指定的图例范围")

    # -------------------------- 读取模型投影和网格信息 --------------------------
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

    # -------------------------- 创建保存目录 --------------------------
    save_case_path = os.path.join(save_root_path, case_label)
    if not os.path.exists(save_case_path):
        os.makedirs(save_case_path)
        print(f"自动创建 {case_label} 保存目录：{save_case_path}")

    # -------------------------- 循环处理每个月份 --------------------------
    for month in months:
        print(f"\n{'='*40}")
        print(f"{case_label} {month}月")
        print(f"{'='*40}")

        # 查找当前月份的Case文件
        fusion_output_file = find_case_file(case_id, month, root_metrics_dir)
        
        if fusion_output_file is None:
            print(f"警告：{case_label} {month}月文件不存在，跳过该月")
            continue

        print(f"找到文件：{os.path.basename(fusion_output_file)}")

        # 读取数据
        try:
            df_data = pd.read_csv(fusion_output_file)
            print(f"成功读取 {case_label} {month}月数据（共{len(df_data)}行）")
        except Exception as e:
            print(f"{case_label} {month}月数据读取失败：{str(e)}，跳过该月")
            continue

        # 检查关键列
        required_cols = ["ROW", "COL"] + variables
        missing_cols = [col for col in required_cols if col not in df_data.columns]
        if missing_cols:
            print(f"{case_label} {month}月数据缺少关键列：{missing_cols}，跳过该月")
            continue

        print(f"{case_label} {month}月开始绘制变量分布图")

        for variable in variables:
            if variable not in df_data.columns:
                print(f"{case_label} {month}月的{variable}列不存在，跳过")
                continue
                
            if df_data[variable].isna().all():
                print(f"{case_label} {month}月的{variable}列全为缺失值，跳过")
                continue

            # 数据重塑
            df_sorted = df_data.sort_values(by=["ROW", "COL"])
            grid_data = df_sorted[variable].values.reshape(grid_shape)

            # 地图标题
            dataset_label = get_dataset_label(variable)
            month_name_cn = get_month_name_cn(month)
            title = f"{month_name_cn} {dataset_label} ({case_label})"

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
            current_unit = variable_units.get(variable, plot_settings['unit'])
            current_colorbar_format = variable_formats.get(variable, '.1f')

            # 统一图例模式下，根据变量类型选择合适的图例范围
            if unified_legend and isinstance(unified_value_range, dict):
                if variable in ['O3_Days', 'PM2.5_Days']:
                    current_value_range = unified_value_range['days']
                else:
                    current_value_range = unified_value_range['other']
            elif unified_legend and isinstance(unified_value_range, tuple):
                current_value_range = unified_value_range

            if not unified_legend or current_value_range is None:
                # 分开图例模式
                var_data = df_sorted[variable].dropna().values
                if len(var_data) > 0:
                    if variable in ['O3_Days', 'PM2.5_Days']:
                        current_vmin = np.nanmin(var_data)
                        current_vmax = np.nanmax(var_data)
                    else:
                        current_vmin = np.nanpercentile(var_data, 1.5)
                        current_vmax = np.nanpercentile(var_data, 98.5)
                    current_value_range = (current_vmin, current_vmax)
                    print(f"  {case_label} {month}月 {variable} 图例范围：{np.round(current_vmin, 2)} ~ {np.round(current_vmax, 2)} {current_unit}")
                else:
                    current_value_range = (0, 1)

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
                    value_range=current_value_range,
                    show_domain_mean=plot_settings['show_domain_mean'],
                    show_grid_line=plot_settings['show_grid_line'],
                    colorbar_format=current_colorbar_format
                )

                # 保存图片
                save_file = os.path.join(save_case_path, f"{case_label}_{month}_{variable}.png")
                fig.savefig(save_file, dpi=300, bbox_inches='tight')
                plt.close(fig)
                
                legend_mode = "统一" if unified_legend else "独立"
                print(f"✅ {case_label} {month}月 {variable} 地图保存成功（{legend_mode}图例）")
            except Exception as e:
                print(f"❌ {case_label} {month}月的{variable}地图失败：{str(e)}，跳过")
                import traceback
                traceback.print_exc()


# -------------------------- 执行入口 --------------------------
if __name__ == "__main__":
    print("="*70)
    print(f"          开始绘制 {TARGET_CASE} 变量分布地图（中文版）          ")
    print("="*70)

    # -------------------------- 核心参数配置 --------------------------
    ROOT_METRICS_DIR = "/data/workspace/GuangDong/cmaqout_processed"
    MODEL_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"
    BOUNDARY_JSON_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"
    SAVE_ROOT_PATH = "/data/workspace/GuangDong/Emission_Alone_Plots_CN"

    # 图例配置
    UNIFIED_VALUE_RANGE = (None, None)
    UNIFIED_LEGEND = False

    # 显示CASE信息
    emission_year, met_year, case_key = CASE_DEFINITIONS[TARGET_CASE]
    print(f"\n目标Case: {TARGET_CASE} ({case_key})")
    print(f"排放年份: {emission_year}, 气象年份: {met_year}")
    print(f"绘制月份: {TARGET_MONTHS}")

    # -------------------------- 调用画图函数 --------------------------
    plot_case_maps(
        root_metrics_dir=ROOT_METRICS_DIR,
        model_file=MODEL_FILE,
        save_root_path=SAVE_ROOT_PATH,
        case_id=TARGET_CASE,
        months=TARGET_MONTHS,
        boundary_json_file=BOUNDARY_JSON_FILE,
        key_periods=None,
        unified_value_range=UNIFIED_VALUE_RANGE,
        unified_legend=UNIFIED_LEGEND
    )

    legend_mode_text = "统一图例" if UNIFIED_LEGEND else "分开图例"
    print(f"\n✅ {TARGET_CASE} 变量地图绘制完成！（{legend_mode_text}模式）")
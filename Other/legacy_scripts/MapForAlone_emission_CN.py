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

# -------------------------- 辅助函数（适配简化CMAQ数据） --------------------------
def extract_key_period(period):
    """提取关键时期标签（仅适配指标文件中的时期）"""
    key_periods = ["DJF", "MAM", "JJA", "SON", 'Annual', 'Apr-Sep', 'top-10']
    return period if period in key_periods else None


def get_year(filename):
    """从CMAQ输出文件名提取年份（适配格式：YYYY_Emission[YYYYmet]_MM.csv）"""
    match = re.search(r"^(\d{4})_Emission\[", os.path.basename(filename))
    return match.group(1) if match else "2023"


def get_month(filename):
    """从CMAQ输出文件名提取月份（适配格式：YYYY_Emission[YYYYmet]_MM.csv）"""
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


def get_case_from_filename(filename):
    """从文件名中提取CASE信息（修正版）"""
    match = re.search(r'(\d{4})_Emission\[(\d{4})met\]', filename)
    if match:
        emission = match.group(1)
        met = match.group(2)
        case_key = f"{emission}e{met}m"
        case_name = CASE_MAPPING.get(case_key, case_key)
        print(f"文件名解析: {filename} -> emission={emission}, met={met}, case_key={case_key}, case_name={case_name}")
        return case_name
    
    # 备用匹配：直接从文件名提取年份组合
    match_simple = re.search(r'(\d{4})_(\d{4})', filename)
    if match_simple:
        emission = match_simple.group(1)
        met = match_simple.group(2)
        case_key = f"{emission}e{met}m"
        return CASE_MAPPING.get(case_key, f"CASE_{emission}e{met}m")
    
    return None


def get_case_number(case_str):
    """从CASE字符串中提取数字（修正版）"""
    if case_str is None:
        return "UNKNOWN"
    
    match = re.search(r'CASE(\d+)', case_str)
    if match:
        return match.group(1)
    
    # 如果没有找到CASE数字，尝试从描述中提取
    match_desc = re.search(r'(\d{4})e(\d{4})m', case_str)
    if match_desc:
        # 根据年份组合映射到CASE编号
        case_key = f"{match_desc.group(1)}e{match_desc.group(2)}m"
        case_name = CASE_MAPPING.get(case_key)
        if case_name:
            return get_case_number(case_name)
    
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


def get_variable_stats_type(variable):
    """从变量名提取统计类型（Mean或Max）"""
    if '_Days' in variable:
        return '超标天'
    return '浓度'  # 默认为浓度


def collect_all_data(root_metrics_dir, years, months, variables):
    """收集所有年月的有效数据，用于自动计算统一图例范围"""
    # 分离超标天数变量和其他变量
    days_variables = [var for var in variables if var in ['O3_Days', 'PM2.5_Days']]
    other_variables = [var for var in variables if var not in ['O3_Days', 'PM2.5_Days']]

    days_values = []  # 超标天数变量的所有值
    other_values = []  # 其他变量的所有值

    for year in years:
        for month in months:
            # 尝试不同的文件名格式
            filename_patterns = [
                f"{year}_Emission[{year}met]_{month}.csv",
                f"{year}_Emission_0{month}.csv" if int(month) < 10 else f"{year}_Emission_{month}.csv"
            ]
            
            fusion_output_file = None
            for pattern in filename_patterns:
                filepath = os.path.join(root_metrics_dir, pattern)
                if os.path.exists(filepath):
                    fusion_output_file = filepath
                    break
            
            if fusion_output_file is None:
                # 如果找不到，尝试遍历目录匹配
                for file in os.listdir(root_metrics_dir):
                    if file.startswith(f"{year}_Emission") and file.endswith(f"_{month}.csv"):
                        fusion_output_file = os.path.join(root_metrics_dir, file)
                        break
            
            if fusion_output_file is None:
                print(f"警告：{year}年{month}月指标文件不存在，跳过该年月数据收集")
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
                print(f"{year}年{month}月数据收集失败：{str(e)}，跳过")
                continue

    if not days_values and not other_values:
        raise ValueError("所有年月均无有效数据，无法计算图例范围")

    return np.array(days_values), np.array(other_values)


# -------------------------- 核心画图函数（支持多年+自动计算图例） --------------------------
def plot_multi_year_maps(
        root_metrics_dir,    # 多年指标文件根目录
        model_file,          # 模型文件（共用）
        save_root_path,      # 多年结果保存根目录
        years,               # 需要处理的年份列表
        months,              # 需要处理的月份列表（01-12）
        boundary_json_file=None,  # 边界文件（共用）
        variable_settings=None,   # 变量配置（适配CMAQ）
        key_periods=None,         # 要画图的时期
        unified_value_range=None, # 所有年份共用的图例范围（可自动计算）
        unified_legend=False      # 是否使用统一图例：True=统一计算，False=分开计算（默认）
):
    # 初始化默认配置（与MapForDiffrenceBetweenDatasets_emission_CN.py保持一致）
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

    # 默认时期（无指定则画所有时期）
    if key_periods is None:
        key_periods = ["DJF", "MAM", "JJA", "SON", 'Annual', 'Apr-Sep', 'top-10']

    # -------------------------- 图例范围处理（支持统一和分开两种模式） --------------------------
    if unified_legend:
        # 统一图例模式：预先计算所有数据的图例范围
        if unified_value_range is None or (unified_value_range[0] is None and unified_value_range[1] is None):
            print("统一图例模式：开始收集所有年月数据并自动计算...")
            days_data, other_data = collect_all_data(root_metrics_dir, years, months, variables)

            # 分别计算超标天数变量和其他变量的图例范围
            days_vmin = days_vmax = None
            other_vmin = other_vmax = None

            if len(days_data) > 0:
                # 超标天数使用最大最小值
                days_vmin = np.nanmin(days_data)
                days_vmax = np.nanmax(days_data)
                print(f"超标天数变量统一图例范围：{np.round(days_vmin, 2)} ~ {np.round(days_vmax, 2)} days")

            if len(other_data) > 0:
                # 其他变量使用百分位数
                other_vmin = np.nanpercentile(other_data, 0.5)
                other_vmax = np.nanpercentile(other_data, 99.5)
                print(f"其他变量统一图例范围：{np.round(other_vmin, 2)} ~ {np.round(other_vmax, 2)}")

            # 存储两种类型的图例范围，后续根据变量类型选择使用
            unified_value_range = {
                'days': (0, 15) if days_vmin is None else (days_vmin, days_vmax),
                'other': (other_vmin, other_vmax) if other_vmin is not None else (0, 100)
            }
        else:
            # 检查手动指定的范围有效性
            if isinstance(unified_value_range, tuple) and (len(unified_value_range) != 2 or unified_value_range[0] >= unified_value_range[1]):
                print("错误：图例范围需满足 vmin < vmax（如(0, 150)），退出程序")
                return
            print(f"统一图例模式：使用手动指定的图例范围：{unified_value_range[0]} ~ {unified_value_range[1]}")
    else:
        # 分开图例模式：每个文件独立计算图例范围
        print("分开图例模式：每个文件将独立计算其图例范围")
        unified_value_range = None

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
            print(f"开始处理 {year}年{month}月CMAQ数据")
            print(f"{'='*60}")

            # 1. 查找当前年月的指标文件
            fusion_output_file = None
            # 尝试标准格式
            standard_pattern = os.path.join(root_metrics_dir, f"{year}_Emission[{year}met]_{month}.csv")
            if os.path.exists(standard_pattern):
                fusion_output_file = standard_pattern
            else:
                # 尝试其他可能的格式
                for file in os.listdir(root_metrics_dir):
                    if (file.startswith(f"{year}_Emission") and 
                        file.endswith(f"_{month}.csv") and 
                        'met' in file):
                        fusion_output_file = os.path.join(root_metrics_dir, file)
                        break
            
            if fusion_output_file is None:
                print(f"警告：{year}年{month}月指标文件不存在，跳过该年月")
                continue

            print(f"找到文件：{os.path.basename(fusion_output_file)}")

            # 2. 创建当前年份的保存目录
            save_single_path = os.path.join(save_root_path, str(year))
            if not os.path.exists(save_single_path):
                os.makedirs(save_single_path)
                print(f"自动创建 {year} 年地图保存目录：{save_single_path}")

            # 3. 读取当前年月的CMAQ指标数据
            try:
                df_data = pd.read_csv(fusion_output_file)
                print(f"成功读取 {year}年{month}月CMAQ指标文件（共{len(df_data)}行）")
            except Exception as e:
                print(f"{year}年{month}月指标文件读取失败：{str(e)}，跳过该年月")
                continue

            # 4. 检查关键列
            required_cols = ["ROW", "COL"] + variables
            missing_cols = [col for col in required_cols if col not in df_data.columns]
            if missing_cols:
                print(f"{year}年{month}月指标文件缺少关键列：{missing_cols}，跳过该年月")
                continue

            # 5. 获取CASE信息（关键修正）
            case_info = get_case_from_filename(fusion_output_file)
            if case_info is None:
                # 如果无法从文件名解析，尝试手动映射
                if year == '2000' or str(year) == '2000':
                    case_info = 'CASE1'  # 2000e2000m
                elif year == '2023' or str(year) == '2023':
                    case_info = 'CASE3'  # 2023e2023m
                elif year == '2030' or str(year) == '2030':
                    case_info = 'CASE6'  # 2030e2030m
                elif year == '2060' or str(year) == '2060':
                    case_info = 'CASE5'  # 2060e2060m
                else:
                    case_info = f"CASE_{year}"
            
            case_num = get_case_number(case_info)
            case_label = f"Case{case_num}"
            
            print(f"CASE信息：{case_info} -> {case_label}")

            # -------------------------- 网格数据处理 --------------------------
            # 验证数据长度是否匹配模型网格
            if len(df_data) != grid_shape[0] * grid_shape[1]:
                print(f"警告：数据长度({len(df_data)})与模型网格尺寸({grid_shape[0]}×{grid_shape[1]}={grid_shape[0]*grid_shape[1]})不匹配")
                # 尝试调整
                min_len = min(len(df_data), grid_shape[0] * grid_shape[1])
                df_data = df_data.iloc[:min_len]

            print(f"{year}年{month}月开始绘制CMAQ变量分布图（{case_label}）")

            for variable in variables:
                if variable not in df_data.columns:
                    print(f"{case_label} {month}月的{variable}列不存在，跳过")
                    continue
                    
                if df_data[variable].isna().all():
                    print(f"{case_label} {month}月的{variable}列全为缺失值，跳过")
                    continue

                # 数据重塑（严格匹配模型网格形状）
                df_sorted = df_data.sort_values(by=["ROW", "COL"])
                grid_data = df_sorted[variable].values.reshape(grid_shape)  # 使用模型网格形状重塑

                # 中文版地图标题
                dataset_label = get_dataset_label(variable)
                month_name_cn = get_month_name_cn(month)

                if '_Days' in variable:
                    title = f"{month_name_cn} {dataset_label} ({case_label})"
                else:
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
                    # 分开图例模式：为当前文件计算独立的图例范围
                    var_data = df_sorted[variable].dropna().values
                    if len(var_data) > 0:
                        if variable in ['O3_Days', 'PM2.5_Days']:
                            current_vmin = np.nanmin(var_data)
                            current_vmax = np.nanmax(var_data)
                        else:
                            current_vmin = np.nanpercentile(var_data, 1.5)
                            current_vmax = np.nanpercentile(var_data, 98.5)
                        current_value_range = (current_vmin, current_vmax)
                        print(f"  {case_label} {month}月 {variable} 独立图例范围：{np.round(current_vmin, 2)} ~ {np.round(current_vmax, 2)} {current_unit}")
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

                    # 保存高清图片（使用Case编号）
                    save_file = os.path.join(save_single_path, f"{case_label}_{month}_{variable}.png")
                    fig.savefig(save_file, dpi=300, bbox_inches='tight')
                    plt.close(fig)
                    
                    legend_mode = "统一" if unified_legend else "独立"
                    print(f"✅ {case_label} {month}月 {variable} 地图保存成功（{legend_mode}图例）：{os.path.basename(save_file)}")
                except Exception as e:
                    print(f"❌ {case_label} {month}月的{variable}地图失败：{str(e)}，跳过")
                    import traceback
                    traceback.print_exc()


# -------------------------- 执行入口 --------------------------
if __name__ == "__main__":
    print("="*70)
    print("          开始批量绘制 多年月CMAQ变量分布地图（中文版）          ")
    print("="*70)

    # -------------------------- 核心参数配置 --------------------------
    ROOT_METRICS_DIR = "/data/workspace/GuangDong/cmaqout_processed"
    MODEL_FILE = "/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"
    BOUNDARY_JSON_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"
    SAVE_ROOT_PATH = "/data/workspace/GuangDong/Emission_Alone_Plots_CN"

    # 年份与月份配置
    TARGET_YEARS = [2030]
    TARGET_MONTHS = ["01", "07"]

    # 图例配置
    UNIFIED_VALUE_RANGE = (None, None)
    UNIFIED_LEGEND = False

    # 显示CASE映射规则
    print(f"CASE映射规则:")
    for case, (emission, met, desc) in CASE_DEFINITIONS.items():
        print(f"  {case}: {emission}排放, {met}气象 ({desc})")

    # -------------------------- 调用批量画图函数 --------------------------
    plot_multi_year_maps(
        root_metrics_dir=ROOT_METRICS_DIR,
        model_file=MODEL_FILE,
        save_root_path=SAVE_ROOT_PATH,
        years=TARGET_YEARS,
        months=TARGET_MONTHS,
        boundary_json_file=BOUNDARY_JSON_FILE,
        key_periods=None,
        unified_value_range=UNIFIED_VALUE_RANGE,
        unified_legend=UNIFIED_LEGEND
    )

    legend_mode_text = "统一图例" if UNIFIED_LEGEND else "分开图例"
    print(f"\n✅ 所有年月CMAQ变量地图绘制完成！（{legend_mode_text}模式）")
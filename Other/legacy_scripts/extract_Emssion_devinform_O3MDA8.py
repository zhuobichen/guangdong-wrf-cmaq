#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合数据提取脚本（多文件版）：
1. 从多个CMAQ Daily COMBINE ACONC文件中提取O3、PM2.5和气象变量
2. 统计O3和PM2.5超标天数
3. 支持多文件输入和多文件输出
4. 可选惠州区域过滤功能（非惠州网格设为NaN）
5. 输出文件可自定义命名，支持_HuiZhou后缀
"""
import netCDF4 as nc
import pandas as pd
import numpy as np
import datetime as dt
import re
import os
import sys
import xarray as xr
from collections import defaultdict

# --------------------------------------------------
# 配置参数
# --------------------------------------------------
# 污染物超标标准（单位：μg/m³）
PM25_STANDARD = 75.0    # PM2.5日均值超标标准（中国二级标准：75 μg/m³）
O3_STANDARD = 80.0     # O3日最大8小时均值超标标准（简化处理：日均值160 μg/m³）

# 温度超标标准（单位：°C）
TEMP_STANDARD = 35.0    # 温度超标标准（高温预警：35 °C）

# 惠州区域过滤配置
HUIZHOU_FLAG_FILE = "/data/workspace/GuangDong/HuiZhou_2000121_GuangDongD3.nc"  # 惠州Flag文件路径

# --------------------------------------------------
# 文件配置类
# --------------------------------------------------
class FileConfig:
    """文件配置类，用于定义输入输出文件"""
    def __init__(self, input_nc_file, output_emission_name, output_meteo_name,
                 year=2000, month=7, apply_huizhou_filter=False):
        self.input_nc_file = input_nc_file          # 输入NC文件路径
        self.output_emission_name = output_emission_name  # 输出排放数据文件名（不含路径和扩展名）
        self.output_meteo_name = output_meteo_name      # 输出气象数据文件名（不含路径和扩展名）
        self.year = year
        self.month = month
        self.apply_huizhou_filter = apply_huizhou_filter

# --------------------------------------------------
# 示例文件配置 - 用户可以在这里添加更多文件配置
# --------------------------------------------------
# 2000vs.2023配置 7月
FILE_CONFIGS = [
    # 基础配置 - 应用惠州过滤（非惠州网格设为NaN）
    #Case2 2000e2023met
    FileConfig(
        input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2023met_2000emis_GD_layer_1_2023-06-26_2023-07-31_18species.nc",
        output_emission_name="2000_Emission[2023met]_07",
        output_meteo_name="2023_mcipout_07",
        year=2000, month=7, apply_huizhou_filter=True
    ),
    # 惠州区域配置 - 应用惠州过滤（非惠州网格设为NaN）
    FileConfig(
        input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2023met_2000emis_GD_layer_1_2022-12-27_2023-01-31_18species.nc",
        output_emission_name="2000_Emission[2023met]_01",
        output_meteo_name="2023_mcipout_01",
        year=2000, month=1, apply_huizhou_filter=True
    ),
    #Case4 2023e2000m
    FileConfig(
        input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2000met_2023emis_GD_layer_1_2000-06-26_2000-07-31_18species.nc",
        output_emission_name="2023_Emission[2000met]_07",
        output_meteo_name="2000_mcipout_07_2023Emission",
        year=2023, month=7, apply_huizhou_filter=True
    ),

    FileConfig(
        input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2000met_2023emis_GD_layer_1_1999-12-27_2000-01-31_18species.nc",
        output_emission_name="2023_Emission[2000met]_01",
        output_meteo_name="2000_mcipout_01_2023Emission",
        year=2023, month=1, apply_huizhou_filter=True
    ),
]


# 2000vs.2023配置 1月
# FILE_CONFIGS = [
    # 基础配置 - 应用惠州过滤（非惠州网格设为NaN）
    # FileConfig(
    #     input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2000_GD_layer_1_2000-06-26_2000-07-31_18species.nc",
    #     output_emission_name="2000_Emission[2000met]_07",
    #     output_meteo_name="2000_mcipout_07",
    #     year=2000, month=7, apply_huizhou_filter=True
    # ),
    # 惠州区域配置 - 应用惠州过滤（非惠州网格设为NaN）
    # FileConfig(
    #     input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2023met_2000emis_GD_layer_1_2022-12-27_2023-01-31_18species.nc",
    #     output_emission_name="2000_Emission[2023met]_01",
    #     output_meteo_name="2023_mcipout_01",
    #     year=2023, month=1, apply_huizhou_filter=True
    # ),
    # FileConfig(
    #     input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2000met_2023emis_GD_layer_1_1999-12-27_2000-01-31_18species.nc",
    #     output_emission_name="2023_Emission[2000met]_01",
    #     output_meteo_name="2000_mcipout_01",
    #     year=2000, month=1, apply_huizhou_filter=True
    # ),
# ]

# 2030配置,2060配置
# FILE_CONFIGS = [
#     # 基础配置 - 应用惠州过滤（非惠州网格设为NaN）
#     FileConfig(
#         input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2000_GD_layer_1_1999-12-27_2000-01-31_18species.nc",
#         output_emission_name="2000_Emission[2000met]_01",
#         output_meteo_name="2000_mcipout_01",
#         year=2000, month=1, apply_huizhou_filter=True
#     ),
#     # 惠州区域配置 - 应用惠州过滤（非惠州网格设为NaN）
#     FileConfig(
#         input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2000_GD_layer_1_2000-06-26_2000-07-31_18species.nc",
#         output_emission_name="2000_Emission[2000met]_07",
#         output_meteo_name="2000_mcipout_07",
#         year=2000, month=7, apply_huizhou_filter=True
#     ),
#     FileConfig(
#         input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2023_GD_layer_1_2022-12-27_2023-01-31_18species.nc",
#         output_emission_name="2023_Emission[2023met]_01",
#         output_meteo_name="2023_mcipout_01",
#         year=2023, month=1, apply_huizhou_filter=True
#     ),
#     # # 惠州区域配置 - 应用惠州过滤（非惠州网格设为NaN）
#     FileConfig(
#         input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2023_GD_layer_1_2023-06-26_2023-07-31_18species.nc",
#         output_emission_name="2023_Emission[2023met]_07",
#         output_meteo_name="2023_mcipout_07",
#         year=2023, month=7, apply_huizhou_filter=True
#     ),
#     FileConfig(
#         input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2030_GD_layer_1_2029-12-27_2030-01-31_18species.nc",
#         output_emission_name="2030_Emission[2030met]_01",
#         output_meteo_name="2030_mcipout_01",
#         year=2030, month=1, apply_huizhou_filter=True
#     ),
#     # 惠州区域配置 - 应用惠州过滤（非惠州网格设为NaN）
#     FileConfig(
#         input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2030_GD_layer_1_2030-06-26_2030-07-31_18species.nc",
#         output_emission_name="2030_Emission[2030met]_07",
#         output_meteo_name="2030_mcipout_07",
#         year=2030, month=7, apply_huizhou_filter=True
#     ),
#     FileConfig(
#         input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2060_GD_layer_1_2059-12-27_2060-01-31_18species.nc",
#         output_emission_name="2060_Emission[2060met]_01",
#         output_meteo_name="2060_mcipout_01",
#         year=2060, month=1, apply_huizhou_filter=True
#     ),

#     FileConfig(
#         input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2060_GD_layer_1_2060-06-26_2060-07-31_18species.nc",
#         output_emission_name="2060_Emission[2060met]_07",
#         output_meteo_name="2060_mcipout_07",
#         year=2060, month=7, apply_huizhou_filter=True
#     ),
# ]


#2060配置

# --------------------------------------------------
# 工具函数
# --------------------------------------------------
def parse_dates_from_filename(filename):
    """从 CMAQ 标准文件名里抠出起止日期"""
    pattern = r'(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})'
    matches = re.findall(pattern, filename)

    if matches:
        start_year, start_month, start_day, end_year, end_month, end_day = matches[0]
        start_date = dt.datetime(int(start_year), int(start_month), int(start_day))
        end_date = dt.datetime(int(end_year), int(end_month), int(end_day))
        return start_date, end_date
    else:
        raise ValueError(f"无法从文件名中解析日期: {filename}")


def create_emission_data_structure(n_rows, n_cols):
    """创建污染物数据存储结构"""
    grid_data = {}
    for r in range(1, n_rows + 1):
        for c in range(1, n_cols + 1):
            key = (r, c)
            grid_data[key] = {
                'o3_values': [],
                'pm25_values': [],
                'o3_exceed_days': 0,
                'pm25_exceed_days': 0
            }
    return grid_data


def create_meteo_data_structure(n_rows, n_cols):
    """创建气象数据存储结构"""
    grid_data = {}
    for r in range(1, n_rows + 1):
        for c in range(1, n_cols + 1):
            key = (r, c)
            grid_data[key] = {
                'ta_values': [],
                'sol_rad_values': [],
                'pblh_values': [],
                'temp_exceed_days': 0  # 温度超标天数（>35°C）
            }
    return grid_data


def load_huizhou_flag():
    """加载惠州区域标志"""
    if not os.path.exists(HUIZHOU_FLAG_FILE):
        print(f"⚠️ 惠州标志文件不存在: {HUIZHOU_FLAG_FILE}")
        return None

    try:
        flag_ds = xr.open_dataset(HUIZHOU_FLAG_FILE)
        flag = flag_ds["Flag"].values  # shape = [nrows, ncols]
        flag_ds.close()
        print(f"✅ 惠州标志文件加载成功，网格形状: {flag.shape}")
        return flag
    except Exception as e:
        print(f"❌ 加载惠州标志文件失败: {str(e)}")
        return None


def apply_huizhou_filter_to_grid_data(emission_grid_data, meteo_grid_data, flag):
    """应用惠州区域过滤到网格数据（非惠州网格设为NaN）"""
    print("应用惠州区域过滤（非惠州网格设为NaN）...")

    filtered_emission = emission_grid_data.copy()
    filtered_meteo = meteo_grid_data.copy()

    # 处理排放数据
    for (r, c), data in filtered_emission.items():
        r_idx, c_idx = r - 1, c - 1  # 转换为0基索引
        if not (r_idx < flag.shape[0] and c_idx < flag.shape[1] and flag[r_idx, c_idx] == 1):
            # 非惠州区域设为NaN
            filtered_emission[(r, c)]['o3_values'] = [np.nan] * len(data['o3_values'])
            filtered_emission[(r, c)]['pm25_values'] = [np.nan] * len(data['pm25_values'])
            filtered_emission[(r, c)]['o3_exceed_days'] = np.nan
            filtered_emission[(r, c)]['pm25_exceed_days'] = np.nan

    # 处理气象数据
    for (r, c), data in filtered_meteo.items():
        r_idx, c_idx = r - 1, c - 1  # 转换为0基索引
        if not (r_idx < flag.shape[0] and c_idx < flag.shape[1] and flag[r_idx, c_idx] == 1):
            # 非惠州区域设为NaN
            filtered_meteo[(r, c)]['ta_values'] = [np.nan] * len(data['ta_values'])
            filtered_meteo[(r, c)]['sol_rad_values'] = [np.nan] * len(data['sol_rad_values'])
            filtered_meteo[(r, c)]['pblh_values'] = [np.nan] * len(data['pblh_values'])
            filtered_meteo[(r, c)]['temp_exceed_days'] = np.nan

    print(f"惠州区域过滤完成，保留全部网格（非惠州区域设为NaN）")
    return filtered_emission, filtered_meteo


# --------------------------------------------------
# 数据提取函数
# --------------------------------------------------
def extract_all_data_from_cmaq(cmaq_file, target_month=7):
    """从单个CMAQ文件中提取所有数据"""
    filename = os.path.basename(cmaq_file)
    start_date, end_date = parse_dates_from_filename(filename)
    print(f'【CMAQ文件】数据跨度 {start_date.date()} ~ {end_date.date()}')

    ds = nc.Dataset(cmaq_file)

    # 读取所有需要的变量
    print("读取污染物和气象变量...")
    try:
        o3_data = ds.variables['O3_MDA8'][:, 0, :, :]          # O3_MDA8_CN浓度
    except:
        print("警告：未找到O3_MDA8数据，使用零值填充")
        o3_data = np.zeros_like(ds.variables['PM25_TOT'][:, 0, :, :])

    pm25_data = ds.variables['PM25_TOT'][:, 0, :, :]      # PM2.5浓度
    ta_data = ds.variables['SFC_TMP'][:, 0, :, :]         # 2m温度
    sol_rad_data = ds.variables['SOL_RAD'][:, 0, :, :]    # 太阳辐射
    pblh_data = ds.variables['PBLH'][:, 0, :, :]         # 边界层高度

    n_t, n_row, n_col = o3_data.shape
    print(f"数据维度: {n_t}天 × {n_row}行 × {n_col}列")

    # 创建数据存储结构
    emission_grid_data = create_emission_data_structure(n_row, n_col)
    meteo_grid_data = create_meteo_data_structure(n_row, n_col)

    # 处理每一天的数据
    valid_days = 0
    for t in range(n_t):
        date = start_date + dt.timedelta(days=t)
        if date.month != target_month:
            continue

        valid_days += 1
        print(f"处理 {date.strftime('%Y-%m-%d')} 的数据...")

        for r in range(n_row):
            for c in range(n_col):
                key = (r + 1, c + 1)  # 转换为1-based索引

                # 污染物数据
                pm25_val = float(pm25_data[t, r, c])
                o3_val = float(o3_data[t, r, c])

                # 存储浓度值
                emission_grid_data[key]['pm25_values'].append(pm25_val)
                emission_grid_data[key]['o3_values'].append(o3_val)

                # 气象数据
                # 温度已经是摄氏度，无需转换
                ta_val = float(ta_data[t, r, c])
                sol_rad_val = float(sol_rad_data[t, r, c])
                pblh_val = float(pblh_data[t, r, c])

                # 统计超标天数
                if pm25_val > PM25_STANDARD:
                    emission_grid_data[key]['pm25_exceed_days'] += 1
                if o3_val > O3_STANDARD:
                    emission_grid_data[key]['o3_exceed_days'] += 1

                meteo_grid_data[key]['ta_values'].append(ta_val)
                meteo_grid_data[key]['sol_rad_values'].append(sol_rad_val)
                meteo_grid_data[key]['pblh_values'].append(pblh_val)

                # 统计温度超标天数（>35°C）
                if ta_val > TEMP_STANDARD:
                    meteo_grid_data[key]['temp_exceed_days'] += 1

    ds.close()
    print(f"成功处理了 {valid_days} 天的{target_month}月数据")

    return emission_grid_data, meteo_grid_data


def create_emission_csv(grid_data, output_file, year, month):
    """创建排放数据CSV文件（保留所有网格，非惠州区域为NaN）"""
    rows = []

    for (r, c), data in grid_data.items():
        # 无论是否有数据都保留行，无数据时均值为NaN
        if data['pm25_values']:
            pm25_avg = np.mean(data['pm25_values'])
            o3_avg = np.mean(data['o3_values'])
        else:
            pm25_avg = np.nan
            o3_avg = np.nan

        rows.append({
            'ROW': r,
            'COL': c,
            'O3': o3_avg,
            'PM2.5': pm25_avg,
            'O3_Days': data['o3_exceed_days'],
            'PM2.5_Days': data['pm25_exceed_days']
        })

    if not rows:
        print("警告：没有找到排放数据")
        return

    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    print(f'✅ 排放数据已保存 → {output_file}')

    # 统计时排除NaN值
    valid_o3 = df['O3'].dropna()
    valid_pm25 = df['PM2.5'].dropna()
    valid_o3_days = df['O3_Days'].dropna()
    valid_pm25_days = df['PM2.5_Days'].dropna()

    if len(valid_o3) > 0:
        print(f'   O3均值范围: {valid_o3.min():.2f} ~ {valid_o3.max():.2f} ppbv')
    else:
        print(f'   O3均值范围: 无有效数据')

    if len(valid_pm25) > 0:
        print(f'   PM2.5均值范围: {valid_pm25.min():.2f} ~ {valid_pm25.max():.2f} μg/m³')
    else:
        print(f'   PM2.5均值范围: 无有效数据')

    if len(valid_o3_days) > 0:
        print(f'   O3超标天数范围: 0 ~ {valid_o3_days.max()} 天')
    else:
        print(f'   O3超标天数范围: 无有效数据')

    if len(valid_pm25_days) > 0:
        print(f'   PM2.5超标天数范围: 0 ~ {valid_pm25_days.max()} 天')
    else:
        print(f'   PM2.5超标天数范围: 无有效数据')


def create_meteo_csv(grid_data, output_file):
    """创建气象数据CSV文件（保留所有网格，非惠州区域为NaN）"""
    rows = []

    for (r, c), data in grid_data.items():
        # 无论是否有数据都保留行，无数据时统计值为NaN
        if data['ta_values']:
            ta_mean = np.mean(data['ta_values'])
            sol_rad_mean = np.mean(data['sol_rad_values'])
            pblh_mean = np.mean(data['pblh_values'])
            ta_max = np.max(data['ta_values'])
            sol_rad_max = np.max(data['sol_rad_values'])
            pblh_max = np.max(data['pblh_values'])
            temp_exceed_days = data['temp_exceed_days']
        else:
            ta_mean = sol_rad_mean = pblh_mean = ta_max = sol_rad_max = pblh_max = np.nan
            temp_exceed_days = np.nan

        rows.append({
            'ROW': r,
            'COL': c,
            'TA_mean': ta_mean,
            'SOL_RAD_mean': sol_rad_mean,
            'PBLH_mean': pblh_mean,
            'TA_max': ta_max,
            'SOL_RAD_max': sol_rad_max,
            'PBLH_max': pblh_max,
            'Temp_Days_35C': data['temp_exceed_days']  # 温度>35°C超标天数
        })

    if not rows:
        print("警告：没有找到气象数据")
        return

    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    print(f'✅ 气象数据已保存 → {output_file}')

    # 统计时排除NaN值
    valid_ta = df['TA_mean'].dropna()
    valid_sol_rad = df['SOL_RAD_mean'].dropna()
    valid_pblh = df['PBLH_mean'].dropna()
    valid_temp_days = df['Temp_Days_35C'].dropna()

    if len(valid_ta) > 0:
        print(f'   温度均值范围: {valid_ta.min():.2f} ~ {valid_ta.max():.2f} °C')
    else:
        print(f'   温度均值范围: 无有效数据')

    if len(valid_sol_rad) > 0:
        print(f'   太阳辐射均值范围: {valid_sol_rad.min():.2f} ~ {valid_sol_rad.max():.2f} W/m²')
    else:
        print(f'   太阳辐射均值范围: 无有效数据')

    if len(valid_pblh) > 0:
        print(f'   边界层高度均值范围: {valid_pblh.min():.2f} ~ {valid_pblh.max():.2f} m')
    else:
        print(f'   边界层高度均值范围: 无有效数据')

    if len(valid_temp_days) > 0:
        print(f'   温度>35°C超标天数范围: 0 ~ {valid_temp_days.max()} 天')
    else:
        print(f'   温度>35°C超标天数范围: 无有效数据')


# --------------------------------------------------
# 主处理函数
# --------------------------------------------------
def process_file_config(file_config, base_dir):
    """处理单个文件配置"""
    print(f"\n{'='*80}")
    print(f"处理文件配置: {file_config.input_nc_file}")
    print(f"年份: {file_config.year}, 月份: {file_config.month}")
    print(f"惠州过滤: {'启用（非惠州网格设为NaN）' if file_config.apply_huizhou_filter else '禁用'}")
    print(f"{'='*80}")

    # 创建输出目录
    emission_dir = os.path.join(base_dir, "cmaqout_processed")
    meteo_dir = os.path.join(base_dir, "mcipout_processed")
    emission_huizhou_dir = os.path.join(base_dir, "cmaqout_processed_HuiZhou")
    meteo_huizhou_dir = os.path.join(base_dir, "mcipout_processed_HuiZhou")

    os.makedirs(emission_dir, exist_ok=True)
    os.makedirs(meteo_dir, exist_ok=True)
    os.makedirs(emission_huizhou_dir, exist_ok=True)
    os.makedirs(meteo_huizhou_dir, exist_ok=True)

    # 从CMAQ文件提取所有数据
    print(f"\n【步骤1】从CMAQ文件提取污染物和气象数据...")
    emission_grid_data, meteo_grid_data = extract_all_data_from_cmaq(
        file_config.input_nc_file, file_config.month)

    processed_files = []

    # 总是输出原本的全区域文件
    print(f"\n【步骤2】生成全区域数据文件...")
    emission_output = os.path.join(emission_dir, f"{file_config.output_emission_name}.csv")
    meteo_output = os.path.join(meteo_dir, f"{file_config.output_meteo_name}.csv")

    # 生成排放数据CSV
    create_emission_csv(emission_grid_data, emission_output, file_config.year, file_config.month)

    # 生成气象数据CSV
    create_meteo_csv(meteo_grid_data, meteo_output)

    processed_files.extend([emission_output, meteo_output])
    print(f"✅ 全区域文件已生成")

    # 如果启用惠州过滤，生成惠州版本（非惠州网格设为NaN）
    if file_config.apply_huizhou_filter:
        print(f"\n【步骤3】应用惠州区域过滤并生成惠州版本...")
        huizhou_flag = load_huizhou_flag()
        if huizhou_flag is not None:
            # 应用惠州过滤（非惠州网格设为NaN）
            emission_huizhou_data, meteo_huizhou_data = apply_huizhou_filter_to_grid_data(
                emission_grid_data, meteo_grid_data, huizhou_flag)

            # 生成惠州版本文件
            emission_huizhou_output = os.path.join(emission_huizhou_dir, f"{file_config.output_emission_name}_HuiZhou.csv")
            meteo_huizhou_output = os.path.join(meteo_huizhou_dir, f"{file_config.output_meteo_name}_HuiZhou.csv")

            # 生成惠州版本排放数据CSV
            create_emission_csv(emission_huizhou_data, emission_huizhou_output, file_config.year, file_config.month)

            # 生成惠州版本气象数据CSV
            create_meteo_csv(meteo_huizhou_data, meteo_huizhou_output)

            processed_files.extend([emission_huizhou_output, meteo_huizhou_output])
            print(f"✅ 惠州区域文件已生成（非惠州网格设为NaN）")
        else:
            print("⚠️ 无法应用惠州过滤，只生成全区域文件")

    print(f"\n✅ 文件配置处理完成！")
    print(f"生成的文件:")
    for i, file_path in enumerate(processed_files, 1):
        print(f"  {i}. {file_path}")

    return processed_files


def main():
    """主函数"""
    print("="*80)
    print("开始综合数据提取（多文件版）")
    print("="*80)

    base_dir = "/data/workspace/GuangDong"

    # 预加载惠州标志（如果需要）
    huizhou_flag = None
    need_huizhou = any(config.apply_huizhou_filter for config in FILE_CONFIGS)
    if need_huizhou:
        print("预加载惠州区域标志...")
        huizhou_flag = load_huizhou_flag()

    # 处理所有文件配置
    all_processed_files = []
    for i, file_config in enumerate(FILE_CONFIGS):
        try:
            print(f"\n处理第 {i+1}/{len(FILE_CONFIGS)} 个文件配置...")
            processed_files = process_file_config(file_config, base_dir)
            all_processed_files.extend(processed_files)
        except Exception as e:
            print(f"❌ 处理文件配置失败: {str(e)}")
            continue

    # 输出处理结果摘要
    print(f"\n{'='*80}")
    print("数据提取完成！")
    print(f"总共生成文件数量: {len(all_processed_files)}")
    print("\n生成的文件:")
    for i, file_path in enumerate(all_processed_files, 1):
        file_type = "排放数据" if "Emission" in file_path else "气象数据"
        region = "惠州（非惠州网格NaN）" if "_HuiZhou" in file_path else "全区域"
        print(f"  {i}. {file_type} ({region}): {file_path}")
    print(f"{'='*80}")


# --------------------------------------------------
# 命令行入口
# --------------------------------------------------
if __name__ == '__main__':
    main()
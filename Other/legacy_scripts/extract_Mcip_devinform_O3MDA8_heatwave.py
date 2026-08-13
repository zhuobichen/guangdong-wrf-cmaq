#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
气象数据提取脚本（热浪分析版）：
1. 从CMAQ Daily COMBINE ACONC文件中提取气象变量
2. 统计热浪天数（连续3天最高气温超过35°C）
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
from typing import List

# --------------------------------------------------
# 配置参数
# --------------------------------------------------
# 温度超标标准（单位：°C）
TEMP_STANDARD = 35.0    # 温度超标标准（高温预警：35 °C）
HEATWAVE_DAYS = 3       # 热浪定义：连续HEATWAVE_DAYS天最高气温超过TEMP_STANDARD

# 惠州区域过滤配置
HUIZHOU_FLAG_FILE = "/data/workspace/GuangDong/HuiZhou_2000121_GuangDongD3.nc"  # 惠州Flag文件路径

# --------------------------------------------------
# 文件配置类
# --------------------------------------------------
from typing import List

class FileConfig:
    """文件配置类，用于定义输入输出文件"""
    def __init__(self, input_nc_file, output_meteo_name,
                 year=2000, month=7, apply_huizhou_filter=False):
        self.input_nc_file = input_nc_file          # 输入NC文件路径
        self.output_meteo_name = output_meteo_name  # 输出气象数据文件名（不含路径和扩展名）
        self.year = year
        self.month = month
        self.apply_huizhou_filter = apply_huizhou_filter


def generate_file_configs(year: int, months: List[int]) -> List[FileConfig]:
    """
    根据指定年份和月份列表生成 FileConfig 列表。

    - 1月特殊处理：使用前一年12月27日 → 当年1月31日
    - 其他月份：使用 (month-1)月26日 → month月31日
      （例如7月 → 6月26日 到 7月31日）

    文件命名规则：
      - 2000年：...2000met_2023emis...
      - 2023年：...2023met_2000emis...
      - 其他年份：...ssp126_{year}...

    Args:
        year (int): 目标年份（即输出月份所属年份）
        months (List[int]): 要生成配置的月份列表（1-12）

    Returns:
        List[FileConfig]
    """
    configs = []
    for month in months:
        if month == 1:
            # 跨年：前一年12月27日 → 当年1月31日
            start_year = year - 1
            start_month = 12
            start_day = 27
            end_year = year
            end_month = 1
            end_day = 31
        else:
            # 非1月：(month-1)月26日 → month月31日
            start_year = year
            start_month = month - 1
            start_day = 26
            end_year = year
            end_month = month
            end_day = 31

        start_date = f"{start_year}-{start_month:02d}-{start_day}"
        end_date = f"{end_year}-{end_month:02d}-{end_day}"

        # 构建 input_nc_file 路径
        if year == 2000:
            input_nc = f"/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_{year}met_2023emis_GD_layer_1_{start_date}_{end_date}_18species.nc"
        elif year == 2023:
            input_nc = f"/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_{year}met_2000emis_GD_layer_1_{start_date}_{end_date}_18species.nc"
        else:
            input_nc = f"/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_{year}_GD_layer_1_{start_date}_{end_date}_18species.nc"

        output_name = f"{year}_mcipout_{month:02d}"
        config = FileConfig(
            input_nc_file=input_nc,
            output_meteo_name=output_name,
            year=year,
            month=month,
            apply_huizhou_filter=True
        )
        configs.append(config)

    return configs


# --------------------------------------------------
# 示例配置
# --------------------------------------------------
FILE_CONFIGS = []
# FILE_CONFIGS.extend(generate_file_configs(2000, [7])) 
FILE_CONFIGS.extend(generate_file_configs(2023, [7])) 
FILE_CONFIGS.extend(generate_file_configs(2030, [7])) 
FILE_CONFIGS.extend(generate_file_configs(2060, [7])) 



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


def create_meteo_data_structure(n_rows, n_cols):
    """创建气象数据存储结构"""
    grid_data = {}
    for r in range(1, n_rows + 1):
        for c in range(1, n_cols + 1):
            key = (r, c)
            grid_data[key] = {
                'ta_values': [],
                'ta_max_values': [],  # 每日最高气温
                'sol_rad_values': [],
                'pblh_values': [],
                'temp_exceed_days': 0,  # 温度超标天数（>35°C）
                'heatwave_days': 0      # 热浪天数（连续3天高温）
            }
    return grid_data


def calculate_heatwave_days(ta_max_series):
    """
    计算热浪天数（连续3天最高气温超过35°C）
    Args:
        ta_max_series: 每日最高气温序列
    Returns:
        heatwave_days: 热浪天数
    """
    if len(ta_max_series) < HEATWAVE_DAYS:
        return 0

    # 标记哪些天的最高气温超过阈值
    hot_days = np.array(ta_max_series) > TEMP_STANDARD

    heatwave_days = 0
    consecutive_count = 0

    for i in range(len(hot_days)):
        if hot_days[i]:
            consecutive_count += 1
            if consecutive_count >= HEATWAVE_DAYS:
                # 当连续3天或更多时，每增加一天就算一个热浪天
                heatwave_days += 1
        else:
            consecutive_count = 0

    return heatwave_days


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


def apply_huizhou_filter_to_meteo_data(meteo_grid_data, flag):
    """应用惠州区域过滤到气象网格数据（非惠州网格设为NaN）"""
    print("应用惠州区域过滤（非惠州网格设为NaN）...")

    filtered_meteo = meteo_grid_data.copy()

    # 处理气象数据
    for (r, c), data in filtered_meteo.items():
        r_idx, c_idx = r - 1, c - 1  # 转换为0基索引
        if not (r_idx < flag.shape[0] and c_idx < flag.shape[1] and flag[r_idx, c_idx] == 1):
            # 非惠州区域设为NaN
            filtered_meteo[(r, c)]['ta_values'] = [np.nan] * len(data['ta_values'])
            filtered_meteo[(r, c)]['ta_max_values'] = [np.nan] * len(data['ta_max_values'])
            filtered_meteo[(r, c)]['sol_rad_values'] = [np.nan] * len(data['sol_rad_values'])
            filtered_meteo[(r, c)]['pblh_values'] = [np.nan] * len(data['pblh_values'])
            filtered_meteo[(r, c)]['temp_exceed_days'] = np.nan
            filtered_meteo[(r, c)]['heatwave_days'] = np.nan

    print(f"惠州区域过滤完成，保留全部网格（非惠州区域设为NaN）")
    return filtered_meteo


# --------------------------------------------------
# 数据提取函数
# --------------------------------------------------
def extract_meteo_data_from_cmaq(cmaq_file, target_month=7):
    """从CMAQ文件中提取气象数据"""
    filename = os.path.basename(cmaq_file)
    start_date, end_date = parse_dates_from_filename(filename)
    print(f'【CMAQ文件】数据跨度 {start_date.date()} ~ {end_date.date()}')

    ds = nc.Dataset(cmaq_file)

    # 读取气象变量
    print("读取气象变量...")
    ta_data = ds.variables['SFC_TMP'][:, 0, :, :]         # 2m温度
    sol_rad_data = ds.variables['SOL_RAD'][:, 0, :, :]    # 太阳辐射
    pblh_data = ds.variables['PBLH'][:, 0, :, :]         # 边界层高度

    n_t, n_row, n_col = ta_data.shape
    print(f"数据维度: {n_t}天 × {n_row}行 × {n_col}列")

    # 创建数据存储结构
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

                # 气象数据
                # 温度已经是摄氏度，无需转换
                ta_val = float(ta_data[t, r, c])
                sol_rad_val = float(sol_rad_data[t, r, c])
                pblh_val = float(pblh_data[t, r, c])

                # 存储温度值
                meteo_grid_data[key]['ta_values'].append(ta_val)
                meteo_grid_data[key]['ta_max_values'].append(ta_val)  # 对于日数据，假设是日均值，这里简化处理
                meteo_grid_data[key]['sol_rad_values'].append(sol_rad_val)
                meteo_grid_data[key]['pblh_values'].append(pblh_val)

                # 统计温度超标天数（>35°C）
                if ta_val > TEMP_STANDARD:
                    meteo_grid_data[key]['temp_exceed_days'] += 1

    # 在处理完所有天后，计算热浪天数
    print("计算热浪天数...")
    for (r, c), data in meteo_grid_data.items():
        key = (r, c)
        if len(data['ta_max_values']) >= HEATWAVE_DAYS:
            meteo_grid_data[key]['heatwave_days'] = calculate_heatwave_days(data['ta_max_values'])

    ds.close()
    print(f"成功处理了 {valid_days} 天的{target_month}月数据")

    return meteo_grid_data


def create_meteo_csv(grid_data, output_file):
    """创建气象数据CSV文件（保留所有网格，非惠州区域为NaN）"""
    rows = []

    for (r, c), data in grid_data.items():
        # 无论是否有数据都保留行，无数据时统计值为NaN
        if data['ta_values']:
            ta_mean = np.mean(data['ta_values'])
            sol_rad_mean = np.mean(data['sol_rad_values'])
            pblh_mean = np.mean(data['pblh_values'])
            ta_max = np.max(data['ta_max_values'])
            sol_rad_max = np.max(data['sol_rad_values'])
            pblh_max = np.max(data['pblh_values'])
            temp_exceed_days = data['temp_exceed_days']
            heatwave_days = data['heatwave_days']
        else:
            ta_mean = sol_rad_mean = pblh_mean = ta_max = sol_rad_max = pblh_max = np.nan
            temp_exceed_days = np.nan
            heatwave_days = np.nan

        rows.append({
            'ROW': r,
            'COL': c,
            'TA_mean': ta_mean,
            'SOL_RAD_mean': sol_rad_mean,
            'PBLH_mean': pblh_mean,
            'TA_max': ta_max,
            'SOL_RAD_max': sol_rad_max,
            'PBLH_max': pblh_max,
            'Temp_Days_35C': temp_exceed_days,  # 温度>35°C超标天数
            'Heatwave_Days': heatwave_days      # 热浪天数（连续3天高温）
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
    valid_heatwave_days = df['Heatwave_Days'].dropna()

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

    if len(valid_heatwave_days) > 0:
        print(f'   热浪天数范围: 0 ~ {valid_heatwave_days.max()} 天')
    else:
        print(f'   热浪天数范围: 无有效数据')


# --------------------------------------------------
# 主处理函数
# --------------------------------------------------
def process_file_config(file_config, base_dir):
    """处理单个文件配置"""
    print(f"\n{'='*80}")
    print(f"处理文件配置: {file_config.input_nc_file}")
    print(f"年份: {file_config.year}, 月份: {file_config.month}")
    print(f"惠州过滤: {'启用（非惠州网格设为NaN）' if file_config.apply_huizhou_filter else '禁用'}")
    print(f"热浪定义: 连续{HEATWAVE_DAYS}天最高气温超过{TEMP_STANDARD}°C")
    print(f"{'='*80}")

    # 创建输出目录
    meteo_dir = os.path.join(base_dir, "mcipout_processed")
    meteo_huizhou_dir = os.path.join(base_dir, "mcipout_processed_HuiZhou")

    os.makedirs(meteo_dir, exist_ok=True)
    os.makedirs(meteo_huizhou_dir, exist_ok=True)

    # 从CMAQ文件提取气象数据
    print(f"\n【步骤1】从CMAQ文件提取气象数据...")
    meteo_grid_data = extract_meteo_data_from_cmaq(
        file_config.input_nc_file, file_config.month)

    processed_files = []

    # 总是输出原本的全区域文件
    print(f"\n【步骤2】生成全区域数据文件...")
    meteo_output = os.path.join(meteo_dir, f"{file_config.output_meteo_name}.csv")

    # 生成气象数据CSV
    create_meteo_csv(meteo_grid_data, meteo_output)

    processed_files.append(meteo_output)
    print(f"✅ 全区域文件已生成")

    # 如果启用惠州过滤，生成惠州版本（非惠州网格设为NaN）
    if file_config.apply_huizhou_filter:
        print(f"\n【步骤3】应用惠州区域过滤并生成惠州版本...")
        huizhou_flag = load_huizhou_flag()
        if huizhou_flag is not None:
            # 应用惠州过滤（非惠州网格设为NaN）
            meteo_huizhou_data = apply_huizhou_filter_to_meteo_data(
                meteo_grid_data, huizhou_flag)

            # 生成惠州版本文件
            meteo_huizhou_output = os.path.join(meteo_huizhou_dir, f"{file_config.output_meteo_name}_HuiZhou.csv")

            # 生成惠州版本气象数据CSV
            create_meteo_csv(meteo_huizhou_data, meteo_huizhou_output)

            processed_files.append(meteo_huizhou_output)
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
    print("开始气象数据提取（热浪分析版）")
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
    print("气象数据提取完成！")
    print(f"总共生成文件数量: {len(all_processed_files)}")
    print("\n生成的文件:")
    for i, file_path in enumerate(all_processed_files, 1):
        region = "惠州（非惠州网格NaN）" if "_HuiZhou" in file_path else "全区域"
        print(f"  {i}. 气象数据 ({region}): {file_path}")
    print(f"{'='*80}")


# --------------------------------------------------
# 命令行入口
# --------------------------------------------------
if __name__ == '__main__':
    main()
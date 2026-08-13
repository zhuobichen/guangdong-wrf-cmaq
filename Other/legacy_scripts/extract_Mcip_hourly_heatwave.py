#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
气象数据提取脚本（小时级热浪分析版）：
1. 从CMAQ COMBINE_ACONC小时文件中提取气象变量
2. 基于小时级数据统计高温天和热浪天数
3. 高温天定义：某个网格某天中任何小时最高温度 > 35°C
4. 热浪天定义：连续3天都为高温天，其中一天算作热浪天
5. 支持多文件输入和多文件输出
6. 可选惠州区域过滤功能（非惠州网格设为NaN）
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
HEATWAVE_DAYS = 3       # 热浪定义：连续HEATWAVE_DAYS天高温

# 时区配置
UTC_OFFSET_HOURS = 8    # 北京时间比UTC快8小时
USE_LOCAL_TIME = True   # 是否使用本地时间（中国时区）进行高温判断

# 惠州区域过滤配置
HUIZHOU_FLAG_FILE = "/data/workspace/GuangDong/HuiZhou_2000121_GuangDongD3.nc"  # 惠州Flag文件路径

# 小时数据完整性控制
ALLOW_NON_24H = False   # 若为 False，则总小时数必须是24的整数倍，否则报错


# --------------------------------------------------
# 文件配置类
# --------------------------------------------------
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
      - 2000年：COMBINE_ACONC_v54_D3_2000met_2023emis...
      - 2023年：COMBINE_ACONC_v54_D3_2023met_2000emis...
      - 其他年份：COMBINE_ACONC_v54_D3_ssp126_{year}...

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
            # 正常月份：前一个月26日 → 当月31日
            start_year = year
            start_month = month - 1
            start_day = 26
            end_year = year
            end_month = month
            end_day = 31

        start_date = f"{start_year}-{start_month:02d}-{start_day}"
        end_date = f"{end_year}-{end_month:02d}-{end_day}"

        if year == 2000:
            input_nc = f"/data/workspace/GuangDong/cmaqout/COMBINE_ACONC_v54_D3_2000met_2023emis_GD_layer_1_{start_date}_{end_date}_18species.nc"
        elif year == 2023:
            input_nc = f"/data/workspace/GuangDong/cmaqout/COMBINE_ACONC_v54_D3_2023met_2000emis_GD_layer_1_{start_date}_{end_date}_18species.nc"
        else:
            input_nc = f"/data/workspace/GuangDong/cmaqout/COMBINE_ACONC_v54_D3_ssp126_{year}_GD_layer_1_{start_date}_{end_date}_18species.nc"

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
# 示例文件配置
# --------------------------------------------------
# 测试配置 - 只处理一个文件
FILE_CONFIGS = []
FILE_CONFIGS.extend(generate_file_configs(2023, [7]))  # 只测试2023年7月
FILE_CONFIGS.extend(generate_file_configs(2030, [7]))  # 只测试2030年7月
FILE_CONFIGS.extend(generate_file_configs(2060, [7]))  # 只测试2060年7月

# 完整配置 - 处理所有年份
# FILE_CONFIGS = []
# FILE_CONFIGS.extend(generate_file_configs(2000, [1, 7]))
# FILE_CONFIGS.extend(generate_file_configs(2023, [1, 7]))
# FILE_CONFIGS.extend(generate_file_configs(2030, [1, 7]))
# FILE_CONFIGS.extend(generate_file_configs(2060, [1, 7]))

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
                'daily_max_temp': [],      # 每日最高气温（从小时数据中提取）
                'sol_rad_values': [],      # 太阳辐射小时数据
                'pblh_values': [],         # 边界层高度小时数据
                'hot_days': 0,             # 高温天数（某天任何小时>35°C）
                'heatwave_days': 0,        # 热浪天数（连续3天高温；旧口径：每段长度L贡献L-2）
                'heatwave_days_coverage': 0  # 热浪覆盖天数（推荐口径：每段长度L贡献L）
            }
    return grid_data


def calculate_heatwave_days(hot_days_series):
    """
    计算热浪天数（连续3天高温）
    Args:
        hot_days_series: 每日是否为高温天的布尔序列
    Returns:
        heatwave_days: 热浪天数
    """
    if len(hot_days_series) < HEATWAVE_DAYS:
        return 0

    heatwave_days = 0
    consecutive_count = 0

    for is_hot_day in hot_days_series:
        if is_hot_day:
            consecutive_count += 1
            if consecutive_count >= HEATWAVE_DAYS:
                # 当连续3天或更多时，每增加一天就算一个热浪天
                heatwave_days += 1
        else:
            consecutive_count = 0

    return heatwave_days


def calculate_heatwave_days_coverage(hot_days_series):
    """计算热浪覆盖天数（连续HEATWAVE_DAYS天高温段内的所有天数都计入）"""
    if len(hot_days_series) < HEATWAVE_DAYS:
        return 0

    coverage_days = 0
    run_len = 0
    for is_hot_day in hot_days_series:
        if is_hot_day:
            run_len += 1
        else:
            if run_len >= HEATWAVE_DAYS:
                coverage_days += run_len
            run_len = 0

    if run_len >= HEATWAVE_DAYS:
        coverage_days += run_len

    return coverage_days


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
            filtered_meteo[(r, c)]['daily_max_temp'] = [np.nan] * len(data['daily_max_temp'])
            filtered_meteo[(r, c)]['sol_rad_values'] = [np.nan] * len(data['sol_rad_values'])
            filtered_meteo[(r, c)]['pblh_values'] = [np.nan] * len(data['pblh_values'])
            filtered_meteo[(r, c)]['hot_days'] = np.nan
            filtered_meteo[(r, c)]['heatwave_days'] = np.nan
            filtered_meteo[(r, c)]['heatwave_days_coverage'] = np.nan

    print(f"惠州区域过滤完成，保留全部网格（非惠州区域设为NaN）")
    return filtered_meteo


# --------------------------------------------------
# 数据提取函数
# --------------------------------------------------
def extract_meteo_data_from_cmaq(cmaq_file, target_month=7):
    """从CMAQ小时文件中提取气象数据（考虑时区转换和25小时情况）"""
    filename = os.path.basename(cmaq_file)
    start_date, end_date = parse_dates_from_filename(filename)
    print(f'【CMAQ文件】数据跨度 {start_date.date()} ~ {end_date.date()}')

    if USE_LOCAL_TIME:
        print(f'📍 时区转换：UTC → 北京时间 (UTC+{UTC_OFFSET_HOURS})')

    ds = nc.Dataset(cmaq_file)

    # 读取气象变量（小时级数据）
    print("读取气象变量...")
    ta_data = ds.variables['SFC_TMP'][:, 0, :, :]         # 2m温度（小时级，UTC时间）
    sol_rad_data = ds.variables['SOL_RAD'][:, 0, :, :]    # 太阳辐射（小时级，UTC时间）
    pblh_data = ds.variables['PBLH'][:, 0, :, :]         # 边界层高度（小时级，UTC时间）

    n_t, n_row, n_col = ta_data.shape
    print(f"数据维度: {n_t}小时 × {n_row}行 × {n_col}列")

    # --- 新增：严格校验小时数是否为24的整数倍 ---
    complete_24h_days = n_t // 24
    remaining_hours = n_t % 24

    print(f"总小时数: {n_t} (完整24小时天数: {complete_24h_days}, 剩余小时: {remaining_hours})")

    if remaining_hours != 0:
        if not ALLOW_NON_24H:
            raise ValueError(
                f"❌ 输入文件小时数 ({n_t}) 不是24的整数倍，且 ALLOW_NON_24H=False。\n"
                f"请确保CMAQ输出为完整日（每天24小时）。文件: {cmaq_file}"
            )
        else:
            print(f"⚠️  ALLOW_NON_24H=True：忽略最后 {remaining_hours} 小时（非完整天）")
            usable_hours = complete_24h_days * 24
    else:
        usable_hours = n_t

    print(f"将使用前 {usable_hours} 小时（{usable_hours // 24} 完整天）进行分析")

    # 创建数据存储结构
    meteo_grid_data = create_meteo_data_structure(n_row, n_col)

    start_idx = 0
    end_idx = usable_hours

    # 第一遍：收集目标月份的所有本地日期
    processed_local_dates = set()
    for utc_hour_idx in range(start_idx, end_idx):
        utc_datetime = start_date + dt.timedelta(hours=utc_hour_idx)
        local_datetime = utc_datetime + dt.timedelta(hours=UTC_OFFSET_HOURS) if USE_LOCAL_TIME else utc_datetime

        if local_datetime.month == target_month:
            local_date_str = local_datetime.strftime('%Y-%m-%d')
            processed_local_dates.add(local_date_str)

    valid_days = len(processed_local_dates)
    print(f"发现 {valid_days} 天目标月份的数据")

    # 第二遍：按本地日期分组处理
    for local_date_str in sorted(processed_local_dates):
        local_date = dt.datetime.strptime(local_date_str, '%Y-%m-%d')

        # 计算该本地日对应的UTC起止时间
        local_start_utc = local_date - dt.timedelta(hours=UTC_OFFSET_HOURS)
        local_end_utc = local_start_utc + dt.timedelta(hours=24)

        start_hour_idx = int((local_start_utc - start_date).total_seconds() // 3600)
        end_hour_idx = int((local_end_utc - start_date).total_seconds() // 3600)

        # 限制在可用范围内
        start_hour_idx = max(start_idx, start_hour_idx)
        end_hour_idx = min(end_idx, end_hour_idx)

        if end_hour_idx - start_hour_idx != 24:
            print(f"⚠️  跳过 {local_date_str}：只有 {end_hour_idx - start_hour_idx} 小时数据（不足24小时）")
            continue

        # 提取当天24小时数据
        daily_temps = ta_data[start_hour_idx:end_hour_idx, :, :]
        daily_sol_rad = sol_rad_data[start_hour_idx:end_hour_idx, :, :]
        daily_pblh = pblh_data[start_hour_idx:end_hour_idx, :, :]

        for r in range(n_row):
            for c in range(n_col):
                key = (r + 1, c + 1)

                temps = daily_temps[:, r, c]
                is_hot_day = np.any(temps > TEMP_STANDARD)

                meteo_grid_data[key]['daily_max_temp'].append(np.max(temps))
                if is_hot_day:
                    meteo_grid_data[key]['hot_days'] += 1

                meteo_grid_data[key]['sol_rad_values'].extend(daily_sol_rad[:, r, c])
                meteo_grid_data[key]['pblh_values'].extend(daily_pblh[:, r, c])

    # 计算热浪天数
    print("计算热浪天数...")
    for (r, c), data in meteo_grid_data.items():
        if len(data['daily_max_temp']) >= HEATWAVE_DAYS:
            hot_days_series = [temp > TEMP_STANDARD for temp in data['daily_max_temp']]
            data['heatwave_days'] = calculate_heatwave_days(hot_days_series)
            data['heatwave_days_coverage'] = calculate_heatwave_days_coverage(hot_days_series)

    ds.close()

    time_str = "本地时间" if USE_LOCAL_TIME else "UTC时间"
    print(f"成功处理了 {valid_days} 天的{target_month}月小时数据（{time_str}）")
    return meteo_grid_data


def create_meteo_csv(grid_data, output_file):
    """创建气象数据CSV文件（保留所有网格，非惠州区域为NaN）"""
    rows = []

    for (r, c), data in grid_data.items():
        if data['daily_max_temp']:
            max_temp_month = np.max(data['daily_max_temp'])

            sol_rad_mean = np.mean(data['sol_rad_values']) if data['sol_rad_values'] else np.nan
            sol_rad_max = np.max(data['sol_rad_values']) if data['sol_rad_values'] else np.nan
            pblh_mean = np.mean(data['pblh_values']) if data['pblh_values'] else np.nan
            pblh_max = np.max(data['pblh_values']) if data['pblh_values'] else np.nan

            hot_days = data['hot_days']
            heatwave_days = data['heatwave_days']
            heatwave_days_coverage = data.get('heatwave_days_coverage', np.nan)
        else:
            max_temp_month = sol_rad_mean = sol_rad_max = pblh_mean = pblh_max = np.nan
            hot_days = heatwave_days = np.nan
            heatwave_days_coverage = np.nan

        rows.append({
            'ROW': r,
            'COL': c,
            'TA_max_month': max_temp_month,
            'SOL_RAD_mean': sol_rad_mean,
            'PBLH_mean': pblh_mean,
            'SOL_RAD_max': sol_rad_max,
            'PBLH_max': pblh_max,
            'Hot_Days_35C': hot_days,
            'Heatwave_Days': heatwave_days,
            'Heatwave_Days_Coverage': heatwave_days_coverage
        })

    if not rows:
        print("警告：没有找到气象数据")
        return

    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    print(f'✅ 气象数据已保存 → {output_file}')

    # 统计摘要
    for col, name, unit in [
        ('TA_max_month', '月最高气温', '°C'),
        ('SOL_RAD_mean', '太阳辐射小时均值', 'W/m²'),
        ('PBLH_mean', '边界层高度小时均值', 'm'),
        ('Hot_Days_35C', '高温天数', '天'),
        ('Heatwave_Days_Coverage', '热浪覆盖天数', '天'),
        ('Heatwave_Days', '热浪天数(旧口径)', '天')
    ]:
        series = df[col].dropna()
        if len(series) > 0:
            if '天' in unit:
                print(f'   {name}范围: 0 ~ {int(series.max())} {unit}')
            else:
                print(f'   {name}范围: {series.min():.2f} ~ {series.max():.2f} {unit}')
        else:
            print(f'   {name}范围: 无有效数据')


# --------------------------------------------------
# 主处理函数
# --------------------------------------------------
def process_file_config(file_config, base_dir):
    """处理单个文件配置"""
    print(f"\n{'='*80}")
    print(f"处理文件配置: {file_config.input_nc_file}")
    print(f"年份: {file_config.year}, 月份: {file_config.month}")
    print(f"惠州过滤: {'启用（非惠州网格设为NaN）' if file_config.apply_huizhou_filter else '禁用'}")
    print(f"高温定义: 某天任何小时温度超过{TEMP_STANDARD}°C")
    print(f"热浪定义: 连续{HEATWAVE_DAYS}天高温")
    print(f"ALLOW_NON_24H: {ALLOW_NON_24H}")
    print(f"{'='*80}")

    meteo_dir = os.path.join(base_dir, "mcipout_processed_hourly")
    meteo_huizhou_dir = os.path.join(base_dir, "mcipout_processed_hourly_HuiZhou")
    os.makedirs(meteo_dir, exist_ok=True)
    os.makedirs(meteo_huizhou_dir, exist_ok=True)

    # 提取数据
    print(f"\n【步骤1】从CMAQ小时文件提取气象数据...")
    meteo_grid_data = extract_meteo_data_from_cmaq(file_config.input_nc_file, file_config.month)

    processed_files = []

    # 全区域输出
    print(f"\n【步骤2】生成全区域数据文件...")
    meteo_output = os.path.join(meteo_dir, f"{file_config.output_meteo_name}.csv")
    create_meteo_csv(meteo_grid_data, meteo_output)
    processed_files.append(meteo_output)
    print(f"✅ 全区域文件已生成")

    # 惠州过滤输出
    if file_config.apply_huizhou_filter:
        print(f"\n【步骤3】应用惠州区域过滤并生成惠州版本...")
        huizhou_flag = load_huizhou_flag()
        if huizhou_flag is not None:
            meteo_huizhou_data = apply_huizhou_filter_to_meteo_data(meteo_grid_data, huizhou_flag)
            meteo_huizhou_output = os.path.join(meteo_huizhou_dir, f"{file_config.output_meteo_name}_HuiZhou.csv")
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
    print("开始气象数据提取（小时级热浪分析版）")
    print("="*80)

    base_dir = "/data/workspace/GuangDong"

    all_processed_files = []
    for i, file_config in enumerate(FILE_CONFIGS):
        try:
            print(f"\n处理第 {i+1}/{len(FILE_CONFIGS)} 个文件配置...")
            processed_files = process_file_config(file_config, base_dir)
            all_processed_files.extend(processed_files)
        except Exception as e:
            print(f"❌ 处理文件配置失败: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

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
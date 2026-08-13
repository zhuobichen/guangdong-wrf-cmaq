#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2030年污染物数据提取脚本：
1. 从CMAQ Daily COMBINE ACONC文件中提取PM2.5、NOX、VOC、SO2、NH3、O3_MDA8
2. 提取1月和7月数据
3. 汇总为一个CSV数据表
4. 支持惠州区域过滤功能（非惠州网格设为NaN）
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
import json
from shapely.geometry import Point
from shapely.geometry import shape
from shapely.prepared import prep
from pyproj import CRS, Transformer

# --------------------------------------------------
# 配置参数
# --------------------------------------------------
# 惠州区域过滤配置
HUIZHOU_FLAG_FILE = "/data/workspace/GuangDong/HuiZhou_2000121_GuangDongD3.nc"  # 惠州 Flag文件路径

# 广东省边界（用于计算“广东区域平均”）
GUANGDONG_PROVINCES_JSON = "/data/workspace/GuangDong/China_provinces.json"


# --------------------------------------------------
# 文件配置类
# --------------------------------------------------
class FileConfig:
    """文件配置类，用于定义输入输出文件"""
    def __init__(self, input_nc_file, year, month):
        self.input_nc_file = input_nc_file          # 输入NC文件路径
        self.year = year
        self.month = month

# --------------------------------------------------
# 2030年1月和7月配置
# --------------------------------------------------
FILE_CONFIGS = [
    FileConfig(
        input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2030_GD_layer_1_2029-12-27_2030-01-31_18species.nc",
        year=2030, month=1
    ),
    FileConfig(
        input_nc_file="/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2030_GD_layer_1_2030-06-26_2030-07-31_18species.nc",
        year=2030, month=7
    ),
]


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


def create_pollutant_data_structure(n_rows, n_cols):
    """创建污染物数据存储结构"""
    grid_data = {}
    for r in range(1, n_rows + 1):
        for c in range(1, n_cols + 1):
            key = (r, c)
            grid_data[key] = {
                'pm25_values': [],
                'nox_values': [],
                'voc_values': [],
                'so2_values': [],
                'nh3_values': [],
                'o3_mda8_values': [],
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


def apply_huizhou_filter_to_grid_data(pollutant_grid_data, flag):
    """应用惠州区域过滤到网格数据（非惠州网格设为NaN）"""
    print("应用惠州区域过滤（非惠州网格设为NaN）...")

    filtered_data = pollutant_grid_data.copy()

    # 处理污染物数据
    for (r, c), data in filtered_data.items():
        r_idx, c_idx = r - 1, c - 1  # 转换为0基索引
        if not (r_idx < flag.shape[0] and c_idx < flag.shape[1] and flag[r_idx, c_idx] == 1):
            # 非惠州区域设为NaN
            filtered_data[(r, c)]['pm25_values'] = [np.nan] * len(data['pm25_values'])
            filtered_data[(r, c)]['nox_values'] = [np.nan] * len(data['nox_values'])
            filtered_data[(r, c)]['voc_values'] = [np.nan] * len(data['voc_values'])
            filtered_data[(r, c)]['so2_values'] = [np.nan] * len(data['so2_values'])
            filtered_data[(r, c)]['nh3_values'] = [np.nan] * len(data['nh3_values'])
            filtered_data[(r, c)]['o3_mda8_values'] = [np.nan] * len(data['o3_mda8_values'])

    print(f"惠州区域过滤完成，保留全部网格（非惠州区域设为NaN）")
    return filtered_data


def load_guangdong_boundary(provinces_json_path: str):
    """从 China_provinces.json 中加载广东省边界（adcode=440000）。"""
    if not os.path.exists(provinces_json_path):
        raise FileNotFoundError(f"广东省边界文件不存在: {provinces_json_path}")

    with open(provinces_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for feature in data.get('features', []):
        props = feature.get('properties', {})
        if props.get('adcode') == 440000:
            return shape(feature.get('geometry'))

    raise ValueError("未在 China_provinces.json 中找到广东省(adcode=440000)边界")


def create_guangdong_mask_from_ioapi(cmaq_file: str, guangdong_boundary):
    """基于 IOAPI 投影参数与网格信息，构建广东省掩码（True=广东省内）。

    优先假设文件为 IOAPI / LCC 投影：使用 XORIG/YORIG/XCELL/YCELL + P_ALP/P_BET/P_GAM/XCENT/YCENT。
    """
    with nc.Dataset(cmaq_file) as ds:
        required_attrs = ["XORIG", "YORIG", "XCELL", "YCELL", "P_ALP", "P_BET", "P_GAM", "XCENT", "YCENT"]
        missing = [a for a in required_attrs if a not in ds.ncattrs()]
        if missing:
            raise ValueError(f"文件缺少 IOAPI 投影/网格属性 {missing}，无法生成广东掩码: {cmaq_file}")

        xorig = float(ds.getncattr("XORIG"))
        yorig = float(ds.getncattr("YORIG"))
        xcell = float(ds.getncattr("XCELL"))
        ycell = float(ds.getncattr("YCELL"))
        p_alp = float(ds.getncattr("P_ALP"))
        p_bet = float(ds.getncattr("P_BET"))
        p_gam = float(ds.getncattr("P_GAM"))
        xcent = float(ds.getncattr("XCENT"))
        ycent = float(ds.getncattr("YCENT"))

        nrows = int(ds.getncattr("NROWS")) if "NROWS" in ds.ncattrs() else int(len(ds.dimensions["ROW"]))
        ncols = int(ds.getncattr("NCOLS")) if "NCOLS" in ds.ncattrs() else int(len(ds.dimensions["COL"]))

    # 网格中心点投影坐标
    x_coords = xorig + (np.arange(ncols) + 0.5) * xcell
    y_coords = yorig + (np.arange(nrows) + 0.5) * ycell
    x_2d, y_2d = np.meshgrid(x_coords, y_coords)

    proj_lcc = CRS.from_string(
        f"+proj=lcc +lat_1={p_alp} +lat_2={p_bet} +lat_0={ycent} +lon_0={p_gam} "
        f"+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    proj_wgs84 = CRS.from_epsg(4326)
    transformer = Transformer.from_crs(proj_lcc, proj_wgs84, always_xy=True)

    # 批量投影到经纬度（numpy 数组）
    lon_2d, lat_2d = transformer.transform(x_2d, y_2d)

    # 逐点判定是否在广东省内
    gd_prepared = prep(guangdong_boundary)
    mask = np.zeros((nrows, ncols), dtype=bool)
    for i in range(nrows):
        for j in range(ncols):
            if gd_prepared.contains(Point(float(lon_2d[i, j]), float(lat_2d[i, j]))):
                mask[i, j] = True

    print(f"✅ 广东掩码生成完成：广东网格数={int(mask.sum())} / 总网格数={mask.size}")
    return mask


# --------------------------------------------------
# 数据提取函数
# --------------------------------------------------
def extract_pollutant_data_from_cmaq(cmaq_file, target_month):
    """从单个CMAQ文件中提取污染物数据"""
    filename = os.path.basename(cmaq_file)
    start_date, end_date = parse_dates_from_filename(filename)
    print(f'【CMAQ文件】数据跨度 {start_date.date()} ~ {end_date.date()}')

    ds = nc.Dataset(cmaq_file)

    # 读取所有需要的污染物变量
    print("读取污染物变量...")
    pm25_data = ds.variables['PM25_TOT'][:, 0, :, :]      # PM2.5浓度
    nox_data = ds.variables['NOX'][:, 0, :, :]             # NOX浓度
    voc_data = ds.variables['VOC'][:, 0, :, :]             # VOC浓度
    so2_data = ds.variables['SO2'][:, 0, :, :]             # SO2浓度
    nh3_data = ds.variables['NH3'][:, 0, :, :]             # NH3浓度
    o3_data = ds.variables['O3'][:, 0, :, :]               # O3浓度（用于计算MDA8）

    n_t, n_row, n_col = pm25_data.shape
    print(f"数据维度: {n_t}天 × {n_row}行 × {n_col}列")

    # 创建数据存储结构
    pollutant_grid_data = create_pollutant_data_structure(n_row, n_col)
    
    # 存储每个网格的逐日O3浓度（用于计算MDA8）
    daily_o3_by_grid = {}
    for r in range(n_row):
        for c in range(n_col):
            key = (r + 1, c + 1)
            daily_o3_by_grid[key] = []  # 存储逐日的O3浓度数组

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
                nox_val = float(nox_data[t, r, c])
                voc_val = float(voc_data[t, r, c])
                so2_val = float(so2_data[t, r, c])
                nh3_val = float(nh3_data[t, r, c])
                o3_val = float(o3_data[t, r, c])

                # 存储浓度值
                pollutant_grid_data[key]['pm25_values'].append(pm25_val)
                pollutant_grid_data[key]['nox_values'].append(nox_val)
                pollutant_grid_data[key]['voc_values'].append(voc_val)
                pollutant_grid_data[key]['so2_values'].append(so2_val)
                pollutant_grid_data[key]['nh3_values'].append(nh3_val)
                
                # 存储O3逐日浓度（后续计算MDA8）
                daily_o3_by_grid[key].append(o3_val)
    
    # 计算O3_MDA8（月平均值）
    print("计算O3_MDA8（取逐日最大值后求月平均）...")
    for key in pollutant_grid_data.keys():
        daily_o3_list = daily_o3_by_grid[key]
        if daily_o3_list:
            # 简化处理：直接使用逐日O3浓度作为MDA8（CMAQ输出已是日均值）
            # 如果需要更精确的MDA8计算，需要小时数据
            o3_mda8_avg = np.mean(daily_o3_list)
            pollutant_grid_data[key]['o3_mda8_values'] = [o3_mda8_avg]  # 存储月平均MDA8

    ds.close()
    print(f"成功处理了 {valid_days} 天的{target_month}月数据")

    return pollutant_grid_data


def create_combined_pollutant_csv(all_month_data, output_file, apply_huizhou_filter=False):
    """创建汇总污染物数据CSV文件（包含1月和7月）
    
    all_month_data: {month: grid_data}
    """
    rows = []

    # 获取所有网格点（从第一个月份获取）
    first_month_data = list(all_month_data.values())[0]
    
    for (r, c) in first_month_data.keys():
        row_data = {
            'ROW': r,
            'COL': c,
        }
        
        # 添加每个月份的数据
        for month, grid_data in sorted(all_month_data.items()):
            data = grid_data[(r, c)]
            
            # 计算各污染物均值
            if data['pm25_values']:
                pm25_avg = np.mean(data['pm25_values'])
                nox_avg = np.mean(data['nox_values'])
                voc_avg = np.mean(data['voc_values'])
                so2_avg = np.mean(data['so2_values'])
                nh3_avg = np.mean(data['nh3_values'])
                o3_mda8_avg = np.mean(data['o3_mda8_values']) if data['o3_mda8_values'] else np.nan
            else:
                pm25_avg = nox_avg = voc_avg = so2_avg = nh3_avg = o3_mda8_avg = np.nan
            
            # 使用月份后缀命名列
            month_suffix = f"_{month:02d}月"
            row_data[f'PM2.5{month_suffix}'] = pm25_avg
            row_data[f'NOX{month_suffix}'] = nox_avg
            row_data[f'VOC{month_suffix}'] = voc_avg
            row_data[f'SO2{month_suffix}'] = so2_avg
            row_data[f'NH3{month_suffix}'] = nh3_avg
            row_data[f'O3_MDA8{month_suffix}'] = o3_mda8_avg
        
        rows.append(row_data)

    if not rows:
        print("警告：没有找到污染物数据")
        return

    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    print(f'✅ 2030年污染物数据已保存 → {output_file}')
    
    # 统计每个变量的范围（排除NaN）
    print(f'\n数据概况：')
    for col in df.columns:
        if col not in ['ROW', 'COL']:
            valid_data = df[col].dropna()
            if len(valid_data) > 0:
                print(f'   {col}: {valid_data.min():.2f} ~ {valid_data.max():.2f}')
            else:
                print(f'   {col}: 无有效数据')


def create_regional_average_csv(all_month_data, output_file, apply_huizhou_filter=False, region_mask=None, region_name=None):
    """创建区域平均浓度CSV文件（所有网格求平均）
    
    all_month_data: {month: grid_data}
    """
    region_label = region_name or "全区域"
    print(f"\n计算区域平均浓度（{region_label}）...")
    
    avg_data = {}
    
    for month, grid_data in sorted(all_month_data.items()):
        # 收集所有网格的浓度值
        all_pm25 = []
        all_nox = []
        all_voc = []
        all_so2 = []
        all_nh3 = []
        all_o3_mda8 = []
        
        for (r, c), data in grid_data.items():
            if region_mask is not None:
                r_idx, c_idx = r - 1, c - 1
                if not (0 <= r_idx < region_mask.shape[0] and 0 <= c_idx < region_mask.shape[1]):
                    continue
                if not bool(region_mask[r_idx, c_idx]):
                    continue

            if data['pm25_values']:  # 如果有数据
                pm25_avg = np.mean(data['pm25_values'])
                nox_avg = np.mean(data['nox_values'])
                voc_avg = np.mean(data['voc_values'])
                so2_avg = np.mean(data['so2_values'])
                nh3_avg = np.mean(data['nh3_values'])
                o3_mda8_avg = np.mean(data['o3_mda8_values']) if data['o3_mda8_values'] else np.nan
                
                # 跳过NaN值
                if not np.isnan(pm25_avg):
                    all_pm25.append(pm25_avg)
                if not np.isnan(nox_avg):
                    all_nox.append(nox_avg)
                if not np.isnan(voc_avg):
                    all_voc.append(voc_avg)
                if not np.isnan(so2_avg):
                    all_so2.append(so2_avg)
                if not np.isnan(nh3_avg):
                    all_nh3.append(nh3_avg)
                if not np.isnan(o3_mda8_avg):
                    all_o3_mda8.append(o3_mda8_avg)
        
        # 计算区域平均值
        month_suffix = f"{month:02d}月"
        avg_data[f'PM2.5_{month_suffix}'] = np.mean(all_pm25) if all_pm25 else np.nan
        avg_data[f'NOX_{month_suffix}'] = np.mean(all_nox) if all_nox else np.nan
        avg_data[f'VOC_{month_suffix}'] = np.mean(all_voc) if all_voc else np.nan
        avg_data[f'SO2_{month_suffix}'] = np.mean(all_so2) if all_so2 else np.nan
        avg_data[f'NH3_{month_suffix}'] = np.mean(all_nh3) if all_nh3 else np.nan
        avg_data[f'O3_MDA8_{month_suffix}'] = np.mean(all_o3_mda8) if all_o3_mda8 else np.nan
        
        print(f"  {month}月: {len(all_pm25)}个有效网格")
    
    # 创建单行DataFrame
    df = pd.DataFrame([avg_data])
    df.to_csv(output_file, index=False)
    print(f'✅ {region_label}平均浓度已保存 → {output_file}')
    
    # 打印平均值
    print(f'\n区域平均浓度：')
    for col in df.columns:
        val = df[col].iloc[0]
        if not np.isnan(val):
            print(f'   {col}: {val:.4f}')
        else:
            print(f'   {col}: 无有效数据')


# --------------------------------------------------
# 主处理函数
# --------------------------------------------------
def main():
    """主函数"""
    print("="*80)
    print("开始提取2030年1月和7月污染物数据")
    print("="*80)

    base_dir = "/data/workspace/GuangDong"
    output_dir = os.path.join(base_dir, "cmaqout_processed")
    output_huizhou_dir = os.path.join(base_dir, "cmaqout_processed_HuiZhou")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(output_huizhou_dir, exist_ok=True)

    # 存储所有月份的数据
    all_month_data = {}

    # 提取每个月份的数据
    for i, file_config in enumerate(FILE_CONFIGS):
        try:
            print(f"\n{'='*80}")
            print(f"处理第 {i+1}/{len(FILE_CONFIGS)} 个文件配置...")
            print(f"文件: {file_config.input_nc_file}")
            print(f"年份: {file_config.year}, 月份: {file_config.month}")
            print(f"{'='*80}")

            # 提取污染物数据
            pollutant_data = extract_pollutant_data_from_cmaq(
                file_config.input_nc_file, file_config.month)
            
            # 存储数据
            all_month_data[file_config.month] = pollutant_data
            
        except Exception as e:
            print(f"❌ 处理文件配置失败: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    if not all_month_data:
        print("❌ 没有成功提取任何数据")
        return

    # 生成全区域汇总 CSV
    print(f"\n{'='*80}")
    print("生成全区域汇总CSV文件...")
    print(f"{'='*80}")
    
    output_file = os.path.join(output_dir, "2030_Pollutants_01_07.csv")
    create_combined_pollutant_csv(all_month_data, output_file, apply_huizhou_filter=False)
    
    # 生成全区域平均浓度 CSV
    output_avg_file = os.path.join(output_dir, "2030_Pollutants_01_07_RegionalAverage.csv")
    create_regional_average_csv(all_month_data, output_avg_file, apply_huizhou_filter=False)

    # 生成广东区域平均浓度 CSV（省界裁剪）
    print(f"\n{'='*80}")
    print("生成广东区域平均浓度CSV文件（省界裁剪）...")
    print(f"{'='*80}")
    try:
        gd_boundary = load_guangdong_boundary(GUANGDONG_PROVINCES_JSON)
        # 用第一个配置文件生成广东掩码（假设同一域网格一致）
        gd_mask = create_guangdong_mask_from_ioapi(FILE_CONFIGS[0].input_nc_file, gd_boundary)
        output_gd_avg_file = os.path.join(output_dir, "2030_Pollutants_01_07_RegionalAverage_GuangDong.csv")
        create_regional_average_csv(
            all_month_data,
            output_gd_avg_file,
            apply_huizhou_filter=False,
            region_mask=gd_mask,
            region_name="广东"
        )
    except Exception as e:
        print(f"⚠️ 生成广东区域平均失败：{e}")

    # 生成惠州区域汇总 CSV（应用过滤）
    print(f"\n{'='*80}")
    print("应用惠州区域过滤并生成惠州版本CSV文件...")
    print(f"{'='*80}")
    
    huizhou_flag = load_huizhou_flag()
    if huizhou_flag is not None:
        # 应用惠州过滤到每个月份的数据
        all_month_data_huizhou = {}
        for month, data in all_month_data.items():
            all_month_data_huizhou[month] = apply_huizhou_filter_to_grid_data(data, huizhou_flag)
        
        output_huizhou_file = os.path.join(output_huizhou_dir, "2030_Pollutants_01_07_HuiZhou.csv")
        create_combined_pollutant_csv(all_month_data_huizhou, output_huizhou_file, apply_huizhou_filter=True)
        
        # 生成惠州区域平均浓度 CSV
        output_huizhou_avg_file = os.path.join(output_huizhou_dir, "2030_Pollutants_01_07_HuiZhou_RegionalAverage.csv")
        create_regional_average_csv(all_month_data_huizhou, output_huizhou_avg_file, apply_huizhou_filter=True)
    else:
        print("⚠️ 无法应用惠州过滤，只生成全区域文件")

    # 输出处理结果摘要
    print(f"\n{'='*80}")
    print("数据提取完成！")
    print(f"\n生成的文件:")
    print(f"  1. 全区域逐网格数据: {output_file}")
    print(f"  2. 全区域平均浓度: {output_avg_file}")
    if huizhou_flag is not None:
        print(f"  3. 惠州区域逐网格数据: {output_huizhou_file}")
        print(f"  4. 惠州区域平均浓度: {output_huizhou_avg_file}")
    print(f"{'='*80}")


# --------------------------------------------------
# 命令行入口
# --------------------------------------------------
if __name__ == '__main__':
    main()
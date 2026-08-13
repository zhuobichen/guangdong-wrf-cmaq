#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""process_GDEI_ALL_TrueUnit

自动检测和处理 GD 排放清单中的多污染物数据。

处理污染物：PM2.5、NOX(NO+NO2)、SO2、NH3、VOC 等。

文件选择：根据目标月份自动识别并读取对应的第一个周五、周六、周日文件。

统计口径（重要）：
- 输入文件每小时为排放速率（默认假设单位为 g/s 或 mol/s）。
- 计算“月总量”而不是“月平均速率”：
    先对样本日做逐小时累积：sum(rate_h * 3600)，得到日总量；
    再按该月工作日/周六/周日天数加权求和，得到月总量。

输出：
- EM_{年份}{月份}_ALL_OnlyGuangDong.csv：广东省综合数据表
- EM_{年份}{月份}_ALL_HuiZhou.csv：惠州专属数据表
"""

import os
import sys
import netCDF4 as nc
import numpy as np
import pandas as pd
import datetime as dt
import re
from collections import defaultdict
import glob
import json
from pathlib import Path
from shapely.geometry import Polygon, Point
from shapely.geometry import shape
import xarray as xr
from pyproj import Transformer, CRS

# 配置参数
BASE_DATA_DIR = "/data/workspace/GuangDong/emissionlist"
OUTPUT_DIR = "/data/workspace/GuangDong/emissionlist"
OUTPUT_DIR_HUIZHOU = "/data/workspace/GuangDong/emissionlist_HuiZhou"
PROVINCES_JSON = "/data/workspace/GuangDong/China_provinces.json"
HUIZHOU_FLAG_FILE = "/data/workspace/GuangDong/HuiZhou_2000121_GuangDongD3.nc"

# 2030年特殊配置 - 从2000年文件夹读取
SPECIAL_2030_DIR = "GD2000"

# 统计口径配置
SECONDS_PER_HOUR = 3600.0
GRAMS_PER_TON = 1_000_000.0
OUTPUT_MASS_UNIT = 'ton/month'  # 输出月总量单位（基于 g/s 速率换算）

# 是否对"广东省外"网格做掩码：
# True  -> OnlyGuangDong 仅保留广东省内（省外设为 NaN）
# False -> OnlyGuangDong 实际包含整个 Domain（不做省界裁剪）
APPLY_GUANGDONG_MASK = False

# 分子量来源：优先从 LabEIScript/GC_SPC.EXT 解析；并用下方 BASE_SPECIES_MW_G_PER_MOL 覆盖关键物种。
GC_SPC_EXT_PATH = Path(__file__).resolve().parent / 'LabEIScript' / 'GC_SPC.EXT'

def load_mw_from_gc_spc_ext(file_path: Path) -> dict:
    """从 GC_SPC.EXT 解析物种分子量表（g/mol）。

    典型行格式：
        DATA  GC_SPC(  2), GC_MOLWT(  2) / 'NO              ', 30.0 /
    """
    if not file_path or not Path(file_path).exists():
        return {}

    text = Path(file_path).read_text(encoding='utf-8', errors='ignore')
    mw_map = {}

    # 捕获 / 'SPECIES', 30.0 / 结构
    pattern = re.compile(r"/\s*'([^']+)'\s*,\s*([0-9.+\-Ee]+)\s*/")
    for m in pattern.finditer(text):
        sp_raw = (m.group(1) or '').strip()
        mw_raw = m.group(2)
        if not sp_raw:
            continue
        try:
            mw = float(mw_raw)
        except Exception:
            continue

        sp = sp_raw.strip().upper()
        mw_map[sp] = mw

    return mw_map


# 最终使用的分子量表（g/mol）
_mw_from_gc = load_mw_from_gc_spc_ext(GC_SPC_EXT_PATH)
if not _mw_from_gc:
    print(f"⚠️  未找到或无法解析 GC_SPC.EXT: {GC_SPC_EXT_PATH}；mol/s 物种可能无法转换")

# GC_SPC.EXT 中的值作为唯一来源
SPECIES_MW_G_PER_MOL = dict(_mw_from_gc)

# 遇到无法识别/无法转换的单位时如何处理：'error' 或 'skip'
UNKNOWN_UNITS_POLICY = 'error'

# 污染物配置（已删除CH4）
POLLUTANT_CONFIGS = {
    'PM2.5': {
        'species': [
            'PEC',      # 元素碳
            'POC',      # 有机碳
            'PNO3',     # 硝酸盐
            'PSO4',     # 硫酸盐
            'PCL',      # 氯化物
            'PNH4',     # 铵盐
            'PNA',      # 钠
            'PMG',      # 镁
            'PK',       # 钾
            'PCA',      # 钙
            'PNCOM',    # 其他氮化合物
            'PFE',      # 铁
            'PAL',      # 铝
            'PSI',      # 硅
            'PTI',      # 钛
            'PMN',      # 锰
            'PH2O',     # 水
            'PMOTHR'    # 其他
        ],
        'unit': 'g/s'
    },
    'VOC': {
        'species': [
            'PAR',      # Paraffins
            'OLE',      # Olefins
            'TOL',      # Toluene
            'XYLMN',    # Xylene + m-xylene + n-xylene
            'FORM',     # Formaldehyde
            'ALD2',     # Other aldehydes
            'ETH',      # Ethane
            'ISOP',     # Isoprene
            'MEOH',     # Methanol
            'ETOH',     # Ethanol
            'UNR',      # Unreactive organics
            # 'CH4',      # Methane (已删除)
            'ETHA',     # Ethene
            'IOLE',     # Internal olefins
            'ALDX',     # Aldehydes
            'TERP',     # Terpenes
            'PRPA',     # Propane
            'BENZ',     # Benzene
            'ETHY',     # Ethylene
            'ACET',     # Acetone
            'KET',      # Ketones
            'NAPH',     # Naphthalene
            'SOAALK',   # SOA alkanes
            #新加入的物种
            'APIN',
            'NR',
            'XYL',
            'AACD'
        ],
        'unit': 'g/s',
        'allow_missing': False,  # 允许部分物种缺失
        'min_required': 5       # 至少需要5个物种存在
    },   
    'NOX': {
        'species': ['NO', 'NO2'],  # NOX = NO + NO2
        'unit': 'g/s',
        'calc_method': 'sum'
    },
    'SO2': {
        'species': ['SO2'],
        'unit': 'g/s'
    },
    'NH3': {
        'species': ['NH3'],
        'unit': 'g/s'
    },
}

def load_guangdong_boundary(provinces_json_path):
    """
    从China_provinces.json中加载广东省边界
    """
    with open(provinces_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for feature in data['features']:
        if feature['properties']['adcode'] == 440000:  # 广东省adcode
            return shape(feature['geometry'])

    raise ValueError("广东省边界信息未找到")

def load_huizhou_flag(huizhou_flag_file):
    """
    加载惠州标识文件
    """
    print(f"正在加载惠州标识文件: {huizhou_flag_file}")
    if not os.path.exists(huizhou_flag_file):
        raise FileNotFoundError(f"惠州标识文件不存在: {huizhou_flag_file}")

    with xr.open_dataset(huizhou_flag_file) as ds:
        flag = ds["Flag"].values
        print(f"惠州标识文件加载成功，网格尺寸: {flag.shape}")
        return flag

def get_grid_coordinates(nc_file):
    """
    从NetCDF文件获取网格坐标信息，处理IOAPI格式的Lambert投影
    """
    with xr.open_dataset(nc_file) as ds:
        # 获取维度信息
        rows = len(ds.ROW)
        cols = len(ds.COL)

        # 获取IOAPI格式的坐标参数
        xorig = ds.attrs.get('XORIG', 0)
        yorig = ds.attrs.get('YORIG', 0)
        xcell = ds.attrs.get('XCELL', 1)
        ycell = ds.attrs.get('YCELL', 1)

        # 计算网格中心点坐标（在投影坐标系中）
        x_coords = xorig + (np.arange(cols) + 0.5) * xcell
        y_coords = yorig + (np.arange(rows) + 0.5) * ycell

        # 创建2D坐标网格
        x_2d, y_2d = np.meshgrid(x_coords, y_coords)

        return x_2d, y_2d, rows, cols

def create_guangdong_mask(nc_file, guangdong_boundary):
    """
    创建广东省掩码数组，广东省内为True，省外为False
    """
    print(f"正在创建广东省掩码...")

    # 获取网格坐标（在投影坐标系中）
    x_2d, y_2d, rows, cols = get_grid_coordinates(nc_file)

    # 创建掩码数组
    mask_array = np.zeros((rows, cols), dtype=bool)  # 默认为False（省外）

    # 获取NetCDF文件的投影参数
    with xr.open_dataset(nc_file) as ds:
        # 显式校验 IOAPI / LCC 相关投影参数是否存在且数值合理
        required_attrs = ["P_ALP", "P_BET", "P_GAM", "XCENT", "YCENT"]
        missing = [k for k in required_attrs if k not in ds.attrs]
        if missing:
            raise ValueError(
                f"文件 {nc_file} 缺少投影属性 {missing}，请用 'ncdump -h {nc_file}' 检查并确认投影配置。"
            )

        try:
            p_alp = float(ds.attrs["P_ALP"])
            p_bet = float(ds.attrs["P_BET"])
            p_gam = float(ds.attrs["P_GAM"])
            xcent = float(ds.attrs["XCENT"])
            ycent = float(ds.attrs["YCENT"])
        except Exception as e:
            raise ValueError(f"文件 {nc_file} 的投影属性无法转换为浮点数: {e}")

        for name, value in [("P_ALP", p_alp), ("P_BET", p_bet), ("P_GAM", p_gam), ("XCENT", xcent), ("YCENT", ycent)]:
            if not np.isfinite(value):
                raise ValueError(
                    f"文件 {nc_file} 的投影属性 {name} = {value} 非有限数值，请用 'ncdump -h {nc_file}' 检查。"
                )

        print("使用的投影参数:")
        print(f"  P_ALP = {p_alp}, P_BET = {p_bet}, P_GAM = {p_gam}")
        print(f"  XCENT = {xcent}, YCENT = {ycent}")

        # 使用文件中提供的 LCC 投影参数
        proj_lcc = CRS.from_string(
            f"+proj=lcc +lat_1={p_alp} +lat_2={p_bet} +lat_0={ycent} +lon_0={p_gam} "
            f"+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
        )
        proj_wgs84 = CRS.from_epsg(4326)  # WGS84地理坐标系

        # 创建投影转换器（从投影坐标到经纬度）
        transformer_to_wgs84 = Transformer.from_crs(proj_lcc, proj_wgs84, always_xy=True)

    # 检查每个网格是否在广东省内
    print("正在检查网格是否在广东省内...")
    guangdong_count = 0

    for i in range(rows):
        if i % 50 == 0:  # 每50行打印一次进度
            print(f"正在检查第 {i}/{rows} 行...")

        for j in range(cols):
            # 将投影坐标转换为经纬度
            try:
                lon, lat = transformer_to_wgs84.transform(x_2d[i, j], y_2d[i, j])
                point = Point(lon, lat)
                if guangdong_boundary.contains(point):
                    mask_array[i, j] = True  # 广东省内为True
                    guangdong_count += 1
            except Exception as e:
                # 如果转换失败，保持为省外
                continue

    print(f"广东省内网格数量: {guangdong_count}")
    print(f"广东省外网格数量: {np.sum(~mask_array)}")

    return mask_array

def find_emission_files(year, month, pollutant_name=None):
    """
    查找指定年份和月份的所有排放文件
    2023年的NOX和VOC从特殊目录提取
    2030年从2000年文件夹读取（特殊情况）
    返回匹配的文件列表和对应的日期信息
    """
    if year == 2030:
        # 2030年特殊处理：从2000年文件夹读取
        data_dir = os.path.join(BASE_DATA_DIR, SPECIAL_2030_DIR)
        print(f"\n查找 {year}年{month}月的排放文件（特殊情况：从2000年文件夹读取 {data_dir}）...")
    else:
        # 根据年份选择数据目录
        if year == 2000:
            data_dir = os.path.join(BASE_DATA_DIR, "GD2000")
        elif year == 2023:
            data_dir = os.path.join(BASE_DATA_DIR, "GD2023")
        elif year == 2060:
            data_dir = os.path.join(BASE_DATA_DIR, "GD2060")
        else:
            data_dir = os.path.join(BASE_DATA_DIR, f"GD{year}")
        print(f"\n查找 {year}年{month}月的排放文件（目录: {data_dir}）...")

    # 构建目标文件名模式
    # 约定：2023 年使用 EM_CC_YYYYDDD，其余年份默认 EM_AV_YYYYDDD
    prefix = 'CC' if year == 2023 else 'AV'
    pattern = f"EM_{prefix}_{year}*"
    files = glob.glob(os.path.join(data_dir, pattern))

    valid_files = []

    for filepath in files:
        filename = os.path.basename(filepath)
        # 从文件名提取日期信息 (EM_AV_YYYYDDD)
        try:
            match = re.match(r"EM_(?:AV|CC)_(\d{4})(\d{3})", filename)
            if match:
                year_val = int(match.group(1))
                day_of_year = int(match.group(2))

                if year_val == year:
                    date_obj = dt.datetime(year_val, 1, 1) + dt.timedelta(days=day_of_year - 1)

                    valid_files.append({
                        'filepath': filepath,
                        'dates': [date_obj],
                        'filename': filename
                    })
                    print(f"  找到文件: {filename} -> {date_obj.strftime('%Y-%m-%d')}")

        except Exception as e:
            print(f"    错误：无法解析文件名 {filename}: {str(e)}")
            continue

    # 按日期排序
    valid_files.sort(key=lambda x: x['dates'][0])
    return valid_files

def select_target_dates(files_info, target_year, target_month):
    """
    选择目标月份的第一个周五、周六、周日
    返回对应的文件和日期信息
    """
    print(f"\n选择 {target_year}年{target_month}月的特定日期...")

    target_dates = {
        'friday': None,
        'saturday': None,
        'sunday': None
    }

    target_files = {
        'friday': None,
        'saturday': None,
        'sunday': None
    }

    # 遍历所有文件，寻找目标日期
    for file_info in files_info:
        for date_obj in file_info['dates']:
            if date_obj.year == target_year and date_obj.month == target_month:
                weekday = date_obj.weekday()  # 0=周一, 1=周二, ..., 4=周五, 5=周六, 6=周日

                if weekday == 4 and target_dates['friday'] is None:  # 周五
                    target_dates['friday'] = date_obj
                    target_files['friday'] = file_info
                    print(f"    找到第一个周五: {date_obj.strftime('%Y-%m-%d')} (文件: {file_info['filename']})")
                elif weekday == 5 and target_dates['saturday'] is None:  # 周六
                    target_dates['saturday'] = date_obj
                    target_files['saturday'] = file_info
                    print(f"    找到第一个周六: {date_obj.strftime('%Y-%m-%d')} (文件: {file_info['filename']})")
                elif weekday == 6 and target_dates['sunday'] is None:  # 周日
                    target_dates['sunday'] = date_obj
                    target_files['sunday'] = file_info
                    print(f"    找到第一个周日: {date_obj.strftime('%Y-%m-%d')} (文件: {file_info['filename']})")

        # 如果三个目标日期都找到了，停止搜索
        if all(target_dates.values()):
            break

    # 检查是否找到了所有目标日期
    missing_days = [day for day, date in target_dates.items() if date is None]
    if missing_days:
        print(f"  ⚠️  警告：未找到目标日期 {missing_days}")

    return target_dates, target_files

def check_required_variables(ds, filepath, pollutant_name):
    """检查特定污染物的必需变量是否存在"""
    config = POLLUTANT_CONFIGS[pollutant_name]
    species = config['species']
    missing_vars = []
    existing_vars = []

    for sp in species:
        if sp in ds.variables:
            existing_vars.append(sp)
        else:
            missing_vars.append(sp)

    print(f"    {pollutant_name}变量检查结果:")
    print(f"      存在的变量 ({len(existing_vars)}): {', '.join(existing_vars)}")

    if missing_vars:
        print(f"      ⚠️  缺失的变量 ({len(missing_vars)}): {', '.join(missing_vars)}")

        # 对于允许部分缺失的污染物，检查是否满足最小要求
        if config.get('allow_missing', False):
            min_required = config.get('min_required', 1)
            if len(existing_vars) >= min_required:
                print(f"      ✅ 满足最小要求（至少{min_required}个物种），继续计算")
                return True, existing_vars
            else:
                print(f"      ❌ 不满足最小要求（需要至少{min_required}个物种）")
                return False, existing_vars
        else:
            return False, existing_vars
    else:
        print(f"      ✅ 所有{pollutant_name}变量都存在")
        return True, existing_vars


def _normalize_units(units: str) -> str:
    u = (units or '').strip().lower()
    # normalize common time tokens
    u = u.replace('seconds', 'sec')
    u = u.replace('second', 'sec')
    # unify sec -> s (so moles/sec -> moles/s)
    u = u.replace('sec', 's')
    # normalize exponent spellings
    u = u.replace('^-1', '-1')
    return u


def _get_mass_rate_factor(ds_var, species: str):
    """Return multiplicative factor to convert ds_var values to g/s.

    - If units already in g/s (or equivalent), factor=1.
    - If units in mol/s (or equivalent), factor=MW(g/mol).
    - Otherwise: return None.
    """
    u = _normalize_units(getattr(ds_var, 'units', ''))

    # common mass-rate spellings
    if 'g/s' in u or 'g s-1' in u or u == 'g/s' or u == 'g s^-1':
        return 1.0
    # some inventories store as grams per second but with spaces
    if u.replace(' ', '') == 'g/s':
        return 1.0

    # molar-rate (IOAPI/CMAQ 常见写法: mol/s, mole/s, moles/s, moles/sec, mol s-1, moles s-1 ...)
    u_compact = u.replace(' ', '')
    is_molar_token = ('mol' in u_compact) or ('mole' in u_compact)
    is_per_second = ('/s' in u_compact) or ('s-1' in u_compact) or ('s**-1' in u_compact) or ('1/s' in u_compact)

    if is_molar_token and is_per_second:
        mw = SPECIES_MW_G_PER_MOL.get((species or '').strip().upper())
        if mw is None:
            return None
        return float(mw)

    return None

def process_pollutant_individual(target_year, target_month, pollutant_name, guangdong_mask, huizhou_flag, nrows, ncols):
    """单独处理每个污染物的数据（支持2023年特殊目录和2030年特殊情况）"""
    print(f"\n{'='*60}")
    print(f"处理 {target_year}年{target_month}月 {pollutant_name} 数据")
    print(f"{'='*60}")

    # 查找该污染物的排放文件
    files_info = find_emission_files(target_year, target_month, pollutant_name)

    if not files_info:
        print(f"警告：未找到{target_year}年{target_month}月{pollutant_name}的排放文件")
        return None, None

    # 选择目标日期和文件
    target_dates, target_files = select_target_dates(files_info, target_year, target_month)

    # 检查是否找到所有目标文件
    if not any(target_files.values()):
        print(f"警告：未找到{target_year}年{target_month}月{pollutant_name}的任何目标文件")
        return None, None

    # 初始化数据存储
    pollutant_data = {
        0: defaultdict(lambda: defaultdict(list)),  # 工作日
        1: defaultdict(lambda: defaultdict(list)),  # 周六
        2: defaultdict(lambda: defaultdict(list))   # 周日
    }

    huizhou_pollutant_data = {
        0: defaultdict(lambda: defaultdict(list)),  # 工作日
        1: defaultdict(lambda: defaultdict(list)),  # 周六
        2: defaultdict(lambda: defaultdict(list))   # 周日
    }

    day_type_names = {'friday': '周五', 'saturday': '周六', 'sunday': '周日'}

    for day_name, file_info in target_files.items():
        if file_info is None:
            print(f"  跳过{day_type_names[day_name]}（无对应文件）")
            continue

        target_date = target_dates[day_name]
        if target_date is None:
            print(f"  跳过{day_type_names[day_name]}（无对应日期）")
            continue

        print(f"  处理{day_type_names[day_name]}数据 ({target_date.strftime('%Y-%m-%d')})...")

        try:
            with nc.Dataset(file_info['filepath'], 'r') as ds:
                # 获取时间步数量
                ntimes = len(ds.dimensions['TSTEP'])
                print(f"    文件包含{ntimes}个时间步")

                if ntimes < 24:
                    raise ValueError(
                        f"{file_info['filename']} has ntimes={ntimes}, expected >=24 (need full 24 hours for daily total)"
                    )

                # 确定日期类型编号
                weekday = target_date.weekday()
                if weekday < 5:  # 周一到周五
                    day_type = 0
                elif weekday == 5:  # 周六
                    day_type = 1
                else:  # 周日
                    day_type = 2

                # 检查变量是否存在（每个文件只检查一次）
                vars_ok, existing_species = check_required_variables(ds, file_info['filepath'], pollutant_name)

                if not vars_ok:
                    # 如果变量检查不通过，该污染物设为NaN
                    pollutant_total_masked = np.full((nrows, ncols), np.nan)
                    huizhou_pollutant_total_masked = np.full((nrows, ncols), np.nan)

                    # 仍然写入 24 小时占位，保持数据结构一致
                    for _ in range(min(ntimes, 24)):
                        for row in range(nrows):
                            for col in range(ncols):
                                pollutant_data[day_type][row+1][col+1].append(pollutant_total_masked[row, col])
                                huizhou_pollutant_data[day_type][row+1][col+1].append(huizhou_pollutant_total_masked[row, col])
                else:
                    # 预先计算单位换算因子（转成 g/s），避免把 mol/s 误当 g/s
                    conv_factor = {}
                    for species in existing_species:
                        ds_var = ds.variables.get(species)
                        if ds_var is None:
                            continue
                        factor = _get_mass_rate_factor(ds_var, species)
                        if factor is None:
                            u = _normalize_units(getattr(ds_var, 'units', ''))
                            msg = (
                                f"单位无法识别或缺少分子量，无法转换为 g/s: pollutant={pollutant_name}, "
                                f"species={species}, units='{u}'. "
                                f"请在 SPECIES_MW_G_PER_MOL 中补充分子量，或调整输出口径。"
                            )
                            if UNKNOWN_UNITS_POLICY == 'skip':
                                print(f"    ⚠️  {msg} -> 跳过该物种")
                                continue
                            raise ValueError(msg)
                        conv_factor[species] = factor

                    # 处理所有小时数据（24小时）
                    for t in range(min(ntimes, 24)):
                        try:
                            pollutant_total = np.zeros((nrows, ncols))
                            for species in existing_species:
                                if species not in ds.variables:
                                    continue
                                if species not in conv_factor:
                                    continue
                                species_data = ds.variables[species][t, 0, :, :]
                                pollutant_total += species_data * conv_factor[species]

                            # 仅在启用广东省掩码时裁剪；否则保留整个 Domain
                            if APPLY_GUANGDONG_MASK:
                                pollutant_total_masked = np.where(guangdong_mask, pollutant_total, np.nan)
                            else:
                                pollutant_total_masked = pollutant_total

                            # 惠州区域：广东省内且惠州标识为1的网格
                            huizhou_mask = guangdong_mask & (huizhou_flag == 1)
                            huizhou_pollutant_total_masked = np.where(huizhou_mask, pollutant_total, np.nan)

                            # 存储该小时值（广东省数据）
                            for row in range(nrows):
                                for col in range(ncols):
                                    pollutant_data[day_type][row+1][col+1].append(pollutant_total_masked[row, col])
                                    huizhou_pollutant_data[day_type][row+1][col+1].append(huizhou_pollutant_total_masked[row, col])

                        except Exception as e:
                            print(f"    警告：处理时间步 {t} 时出错: {str(e)}")
                            continue

                print(f"    处理完成：共处理{min(ntimes, 24)}小时数据")

        except Exception as e:
            print(f"  ❌ 处理{day_type_names[day_name]}文件时出错: {str(e)}")
            continue

    return pollutant_data, huizhou_pollutant_data

def calculate_pollutant_monthly_total(pollutant_data, target_year, target_month, nrows, ncols):
    """计算单个污染物的月总量（默认输出 ton/month）

    输入：pollutant_data 为样本日逐小时“排放速率”（假设 g/s）。
    计算：先求样本日逐小时总量（rate×3600 累加），再按该月同类日天数加权求和。
    """
    if pollutant_data is None:
        return np.full((nrows, ncols), np.nan)

    # 结果矩阵（初始化为NaN）
    monthly_total = np.full((nrows, ncols), np.nan)

    import calendar
    # 获取目标月份的日历信息
    cal = calendar.monthcalendar(target_year, target_month)

    # 统计各类型天数
    weekday_count = 0
    saturday_count = 0
    sunday_count = 0

    # calendar.monthcalendar() 默认 firstweekday=0，即周一为 0，...，周日为 6
    for week in cal:
        for i, day in enumerate(week):
            if day == 0:
                continue
            if i <= 4:          # Mon-Fri
                weekday_count += 1
            elif i == 5:        # Sat
                saturday_count += 1
            else:               # i == 6, Sun
                sunday_count += 1

    # 为每个网格计算月平均值
    for row in range(1, nrows+1):
        for col in range(1, ncols+1):
            # 收集各类型的“日总量”（单位：g/day）
            weekday_total_g = None
            saturday_total_g = None
            sunday_total_g = None

            # 从工作日样本计算“日总量”
            if 0 in pollutant_data and row in pollutant_data[0] and col in pollutant_data[0][row]:
                hourly_values = pollutant_data[0][row][col]
                if hourly_values and not all(np.isnan(v) for v in hourly_values):
                    weekday_total_g = float(np.nansum(hourly_values)) * SECONDS_PER_HOUR

            # 从周六样本计算“日总量”
            if 1 in pollutant_data and row in pollutant_data[1] and col in pollutant_data[1][row]:
                hourly_values = pollutant_data[1][row][col]
                if hourly_values and not all(np.isnan(v) for v in hourly_values):
                    saturday_total_g = float(np.nansum(hourly_values)) * SECONDS_PER_HOUR

            # 从周日样本计算“日总量”
            if 2 in pollutant_data and row in pollutant_data[2] and col in pollutant_data[2][row]:
                hourly_values = pollutant_data[2][row][col]
                if hourly_values and not all(np.isnan(v) for v in hourly_values):
                    sunday_total_g = float(np.nansum(hourly_values)) * SECONDS_PER_HOUR

            # 计算月总量（基于有限的样本）
            totals_g = []
            weights = []

            if weekday_total_g is not None and not np.isnan(weekday_total_g):
                totals_g.append(weekday_total_g)
                weights.append(weekday_count)
            if saturday_total_g is not None and not np.isnan(saturday_total_g):
                totals_g.append(saturday_total_g)
                weights.append(saturday_count)
            if sunday_total_g is not None and not np.isnan(sunday_total_g):
                totals_g.append(sunday_total_g)
                weights.append(sunday_count)

            if totals_g:
                monthly_total_g = float(np.sum(np.array(totals_g) * np.array(weights)))
                # 输出单位换算
                if OUTPUT_MASS_UNIT == 'ton/month':
                    monthly_total[row-1, col-1] = monthly_total_g / GRAMS_PER_TON
                else:
                    # 默认不换算（g/month）
                    monthly_total[row-1, col-1] = monthly_total_g

    return monthly_total

def process_single_year_month(target_year, target_month):
    """处理单个年份和月份的多污染物数据"""
    print(f"\n{'='*80}")
    print(f"处理 {target_year}年{target_month}月 多污染物数据")
    print(f"{'='*80}")

    print(f"目标参数: {target_year}年{target_month}月")

    # 获取网格尺寸，并按需创建广东省掩码/惠州掩码（使用第一个污染物的文件）
    nrows = None
    ncols = None
    guangdong_mask = None
    huizhou_flag = None

    # 先查找任意一个文件来获取网格信息
    test_files = find_emission_files(target_year, target_month)
    if test_files:
        try:
            with nc.Dataset(test_files[0]['filepath'], 'r') as ds:
                nrows = len(ds.dimensions['ROW'])
                ncols = len(ds.dimensions['COL'])
                print(f"网格尺寸: {nrows} × {ncols}")

                if APPLY_GUANGDONG_MASK:
                    # 加载广东省边界
                    print("加载广东省边界...")
                    guangdong_boundary = load_guangdong_boundary(PROVINCES_JSON)

                    # 创建广东省掩码
                    print("创建广东省掩码...")
                    guangdong_mask = create_guangdong_mask(test_files[0]['filepath'], guangdong_boundary)
                else:
                    # 不做省界裁剪时，使用全 True 掩码（整个 Domain）
                    print("不启用广东省掩码，使用整个 Domain")
                    guangdong_mask = np.ones((nrows, ncols), dtype=bool)

                # 加载惠州标识（始终可以用于输出惠州子集）
                print("加载惠州标识...")
                huizhou_flag = load_huizhou_flag(HUIZHOU_FLAG_FILE)

        except Exception as e:
            print(f"获取网格信息时出错: {e}")
            return False

    if nrows is None or ncols is None:
        print("错误：无法获取网格信息")
        return False

    if guangdong_mask is None:
        print("错误：无法创建或初始化广东省掩码/Domain 掩码")
        return False

    if huizhou_flag is None:
        print("错误：无法加载惠州标识")
        return False

    # 逐个处理每个污染物
    monthly_avg_all = {}
    monthly_avg_huizhou_all = {}

    for pollutant_name in POLLUTANT_CONFIGS.keys():
        # 处理单个污染物数据（同时返回广东和惠州数据）
        pollutant_data, huizhou_pollutant_data = process_pollutant_individual(
            target_year, target_month, pollutant_name, guangdong_mask, huizhou_flag, nrows, ncols)

        # 计算该污染物的月总量
        monthly_total = calculate_pollutant_monthly_total(pollutant_data, target_year, target_month, nrows, ncols)
        monthly_avg_all[pollutant_name] = monthly_total

        # 计算惠州该污染物的月总量
        monthly_total_huizhou = calculate_pollutant_monthly_total(huizhou_pollutant_data, target_year, target_month, nrows, ncols)
        monthly_avg_huizhou_all[pollutant_name] = monthly_total_huizhou

    # 保存综合结果（广东省）
    csv_file = os.path.join(OUTPUT_DIR, f"EM_{target_year}{target_month:02d}_ALL_OnlyGuangDong.csv")
    save_combined_csv(monthly_avg_all, csv_file, target_year, target_month)

    # 保存惠州综合结果
    csv_huizhou_file = os.path.join(OUTPUT_DIR_HUIZHOU, f"EM_{target_year}{target_month:02d}_ALL_HuiZhou.csv")
    save_combined_csv(monthly_avg_huizhou_all, csv_huizhou_file, target_year, target_month)

    # 输出统计信息
    print(f"\n{'='*50}")
    print(f"最终{target_year}年{target_month}月总量统计结果（广东省），单位: {OUTPUT_MASS_UNIT}")
    print(f"{'='*50}")

    for pollutant_name in POLLUTANT_CONFIGS.keys():
        data = monthly_avg_all[pollutant_name]
        # 只统计广东省内的有效数据
        valid_data = data[np.isfinite(data)]

        if len(valid_data) > 0:
            print(f"{pollutant_name}月总量统计:")
            print(f"  有效数据网格数: {len(valid_data)}")
            print(f"  整体平均值: {np.mean(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  最大值: {np.max(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  最小值: {np.min(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  中位数: {np.median(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  标准差: {np.std(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  非零网格数: {np.sum(valid_data > 0)}")
        else:
            print(f"{pollutant_name}: 无有效数据")
        print()

    # 输出惠州统计信息
    print(f"\n{'='*50}")
    print(f"最终{target_year}年{target_month}月总量统计结果（惠州市），单位: {OUTPUT_MASS_UNIT}")
    print(f"{'='*50}")

    for pollutant_name in POLLUTANT_CONFIGS.keys():
        data = monthly_avg_huizhou_all[pollutant_name]
        # 只统计惠州区域的有效数据
        valid_data = data[np.isfinite(data)]

        if len(valid_data) > 0:
            print(f"{pollutant_name}月总量统计:")
            print(f"  惠州有效数据网格数: {len(valid_data)}")
            print(f"  整体平均值: {np.mean(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  最大值: {np.max(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  最小值: {np.min(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  中位数: {np.median(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  标准差: {np.std(valid_data):.6f} {OUTPUT_MASS_UNIT}")
            print(f"  非零网格数: {np.sum(valid_data > 0)}")
        else:
            print(f"{pollutant_name}: 无有效数据")
        print()

    print(f"✅ {target_year}年{target_month}月处理完成！")
    print(f"  广东省综合CSV输出文件: {csv_file}")
    print(f"  惠州市综合CSV输出文件: {csv_huizhou_file}")

    return True

def save_combined_csv(monthly_avg, output_file, year, month):
    """保存所有污染物数据到一个综合CSV文件"""
    print(f"正在保存综合CSV到: {output_file}")

    rows, cols = next(iter(monthly_avg.values())).shape  # 获取行列数
    pollutant_names = list(monthly_avg.keys())

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        # 写入标题行
        header = ['ROW', 'COL'] + pollutant_names
        f.write(','.join(header) + '\n')

        # 写入数据
        for row in range(1, rows+1):
            for col in range(1, cols+1):
                values = [str(row), str(col)]

                for pollutant_name in pollutant_names:
                    value = monthly_avg[pollutant_name][row-1, col-1]
                    # 将NaN转换为空字符串或'NaN'
                    if np.isnan(value):
                        values.append('')  # 空字符串，方便后续处理
                    else:
                        values.append(f"{value:.6f}")  # 保留6位小数

                f.write(','.join(values) + '\n')

    print(f"✅ 综合CSV数据已保存到: {output_file}")

def print_species_inventory():
    """输出清单的总物种量统计"""
    print("\n📋 清单物种总量统计")
    print("=" * 50)

    total_species = 0
    for pollutant_name, config in POLLUTANT_CONFIGS.items():
        species_count = len(config['species'])
        total_species += species_count
        print(f"{pollutant_name}: {species_count} 个物种 - {', '.join(config['species'])}")

    print("=" * 50)
    print(f"总计: {len(POLLUTANT_CONFIGS)} 类污染物，{total_species} 个物种")
    print()

def main():
    """主函数"""
    print("=" * 80)
    print("GD排放清单多污染物数据处理（自动检测版本）")
    print("自动识别第一个周五、周六、周日文件并计算月平均值")
    print("处理PM2.5、NOX、SO2、NH3、VOC等污染物，广东省外数据设为NaN")
    print("2023年文件前缀使用 EM_CC_YYYYDDD（其余年份默认 EM_AV_YYYYDDD）")
    print("2030年从2000年文件夹读取（特殊情况）")
    print("同时输出广东省和惠州市的综合数据")
    print("=" * 80)

    # 输出清单物种统计
    print_species_inventory()

    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR_HUIZHOU, exist_ok=True)

    # 检查必要文件是否存在
    if not os.path.exists(PROVINCES_JSON):
        print(f"错误: 省份边界文件不存在: {PROVINCES_JSON}")
        return

    if not os.path.exists(HUIZHOU_FLAG_FILE):
        print(f"错误: 惠州标识文件不存在: {HUIZHOU_FLAG_FILE}")
        return

    # 配置要处理的年份和月份（内部参数）
    processing_configs = [
        (year, month) 
        for year in [2000, 2023] 
        for month in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        # for month in [7]
]

    print(f"\n配置的处理参数:")
    for year, month in processing_configs:
        special_note = "（特殊情况：从2000年文件夹读取）" if year == 2030 else ""
        print(f"  {year}年{month}月{special_note}")
    print(f"\n总共需要处理 {len(processing_configs)} 个年月组合")

    # 统计处理结果
    success_count = 0
    failed_configs = []

    # 逐个处理每个年月组合
    for i, (year, month) in enumerate(processing_configs, 1):
        print(f"\n{'*'*60}")
        print(f"进度: {i}/{len(processing_configs)} - 处理 {year}年{month}月")
        print(f"{'*'*60}")

        try:
            success = process_single_year_month(year, month)
            if success:
                success_count += 1
            else:
                failed_configs.append((year, month))
        except Exception as e:
            print(f"❌ 处理 {year}年{month}月时发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
            failed_configs.append((year, month))

    # 输出最终总结
    print(f"\n{'='*80}")
    print(f"所有处理任务完成！")
    print(f"{'='*80}")
    print(f"成功处理: {success_count}/{len(processing_configs)} 个年月组合")

    if success_count == len(processing_configs):
        print("🎉 所有处理任务都成功完成！")
    else:
        print(f"⚠️  失败的组合: {len(failed_configs)} 个")
        for year, month in failed_configs:
            print(f"  - {year}年{month}月")

    print(f"\n输出文件保存在:")
    print(f"  广东省数据: {OUTPUT_DIR}")
    print(f"  惠州市数据: {OUTPUT_DIR_HUIZHOU}")
    print(f"文件命名格式:")
    print(f"  广东省: EM_YYYYMM_ALL_OnlyGuangDong.csv")
    print(f"  惠州市: EM_YYYYMM_ALL_HuiZhou.csv")
    print(f"注意：广东省外和惠州市外数据已设为NaN（CSV中为空字符串）")
    print(f"注意：输出为月总量，单位: {OUTPUT_MASS_UNIT}（基于输入速率 g/s 换算）")
    print(f"注意：2030年数据从2000年文件夹读取（特殊情况）")

if __name__ == "__main__":
    main()
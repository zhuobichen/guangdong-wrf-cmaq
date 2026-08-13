# GuangDong 项目架构规范

> 目标：对 GuangDong 项目进行 Core+Run 分层重构，消除混乱，建立可维护的模块化架构
> 版本: 2026-05 (v1 - 初始架构设计)
> 基准参考: `DataFusion_China_CleanAir/docs/DataFusion项目架构规范_Core+Run分层设计.md`
> 项目路径: `/data/workspace/GuangDong`

---

## 一、项目概述

GuangDong 项目是一个**广东区域 CMAQ 空气质量情景对比分析**项目，核心任务包括：

| 功能域 | 描述 |
|--------|------|
| 数据提取 | 从 CMAQ Daily COMBINE ACONC NC 文件中提取 PM2.5、O3（MDA8）及气象变量（温度、太阳辐射、边界层高度），统计超标天数 |
| 排放清单处理 | 处理 GD 排放清单中 PM2.5 多物种数据，按工作日/周末模式计算月均值 |
| 区域掩膜 | 生成广东、惠州、陆地掩膜，将非目标区域网格置为 NaN |
| 空间分布地图 | 多年/多月/多 CASE 的污染物浓度和超标天数空间分布图（单独+差异对比） |
| PDF 分布图 | KDE 核密度估计对比图，多年份 vs 基准年（2023）分布变化 |
| 统计图表 | 柱状图（面积*天数）、箱线图（CASE 对比） |

**数据维度**：
- 年份：2000、2023、2030、2060
- 月份：01（1月）、07（7月）
- 污染物：O3、PM2.5、O3_Days（超标天）、PM2.5_Days（超标天）
- 气象：TA_mean/max、SOL_RAD_mean/max、PBLH_mean/max
- 区域：广东全省、惠州、陆地
- CASE：CASE1-CASE6（不同排放清单×气象年份组合）

---

## 二、现状问题诊断

### 2.1 核心问题一览

| # | 问题 | 当前状态 | 影响 |
|---|------|----------|------|
| 1 | 无 Core/Run 分层 | 60+ Python 文件平铺在根目录，每个脚本同时含逻辑+配置 | 逻辑重复，修改困难 |
| 2 | 数据目录混乱 | `cmaqout_processed/`, `_GuangDong/`, `_HuiZhou/`, `_land/` 平铺 | 难以判断数据来源与用途 |
| 3 | 图片输出散落 | `Emission_Comparison_Plots_CN/`, `Emission_Comparison_Plots_PDF_CN/`, `Mcip_Comparison_Plots_CN/` 等 10+ 个平级目录 | 找图困难 |
| 4 | esil 重复 | 根目录同时存在 `esil/` 和 `esil_2/` | 工具库版本不一致风险 |
| 5 | 废弃代码堆积 | `1_codenotuse/` 含 8 个子目录、30+ 旧脚本 | 混淆当前工作代码 |
| 6 | 废弃图片/数据 | `1_PictureAndDatenotuse/` 含 10 个子目录 | 占用空间，混淆当前成果 |
| 7 | 无统一顶层目录 | 没有 `Data/`、`Picture/`、`docs/` | 新成员无从下手 |
| 8 | 命名不一致 | CASE1/Case1 混用，中英混合命名 | 检索困难 |
| 9 | 大量功能重复脚本 | 如 `MapForDiffrenceBetweenDatasets_*.py` 有 10+ 个变体 | 维护噩梦 |

### 2.2 脚本分类统计

| 类别 | 数量 | 代表脚本 |
|------|------|----------|
| 数据提取 | ~10 | `extract_Emssion_devinform_O3MDA8.py` |
| 区域掩膜 | ~6 | `mask_cmaqout_processed_to_GuangDong.py` |
| 单独空间地图 | ~8 | `MapForAlone_emission_CN.py` |
| 差异对比地图 | ~10 | `MapForDiffrenceBetweenDatasets_emission_CN.py` |
| PDF/KDE 分布 | ~8 | `PDF_emssion_kde_simply.py` |
| 柱状图 | ~8 | `BarChartsForPM2.5O3_Case_面积*天数_emission.py` |
| 箱线图 | ~3 | `BoxplotsForPM2.5O3_Case.py` |
| 工具/辅助 | ~8 | `filter_guangdong_weather.py` |
| 废弃脚本 | 30+ | `1_codenotuse/` 下全部 |

---

## 三、目标顶层目录结构

```
GuangDong/
├── Core_Extract.py         # 核心模块：数据提取（NC→CSV）
├── Core_Mask.py            # 核心模块：区域掩膜生成与应用
├── Core_Map.py             # 核心模块：空间地图绘制（单独+差异）
├── Core_PDF.py             # 核心模块：KDE 概率密度分布图
├── Core_Charts.py          # 核心模块：柱状图 + 箱线图
│
├── Run_Extract.py          # 入口：数据提取配置
├── Run_Mask.py             # 入口：区域掩膜配置
├── Run_Map_Single.py       # 入口：单独空间分布图
├── Run_Map_Diff.py         # 入口：差异对比地图
├── Run_PDF.py              # 入口：PDF 分布图
├── Run_BarCharts.py        # 入口：柱状图
├── Run_BoxPlots.py         # 入口：箱线图
│
├── Data/                   # 所有输入/处理数据
│   ├── Raw/                #   原始 NC 输入文件
│   │   ├── CMAQ/           #     CMAQ Daily COMBINE ACONC NC
│   │   ├── MCIP/           #     MCIP METCRO2D/3D NC
│   │   └── Emission/       #     排放清单 NC（EM_AV_YYYYDDD.nc）
│   ├── Processed/          #   提取后的逐网格 CSV（全区域）
│   │   ├── CMAQ/           #     {year}_Emission[{year}met]_{month}.csv
│   │   ├── MCIP/           #     {year}_mcipout_{month}.csv
│   │   └── Emission/       #     EM_{year}{month}_PM2.5.csv
│   ├── Masked/             #   区域掩膜后 CSV
│   │   ├── GuangDong/      #     *_GuangDong.csv
│   │   ├── HuiZhou/        #     *_HuiZhou.csv
│   │   └── Land/           #     *_land.csv
│   ├── Boundary/           #   边界/网格文件
│   │   ├── GRIDCRO2D_2000121_GuangDongD3
│   │   ├── GRIDCRO2D_2000121_GuangDongD1
│   │   ├── GRIDCRO2D_Huizhou_Flag.nc
│   │   ├── HuiZhou_2000121_GuangDongD3.nc
│   │   ├── China_Provinces_2000121_GuangDongD3.nc
│   │   ├── China_provinces.json
│   │   ├── huizhou.json
│   │   ├── huizhou_boundary.json
│   │   ├── china.json
│   │   └── china_cities.json
│   ├── Station/            #   站点观测数据
│   ├── Hourly/             #   小时级数据
│   └── Statistics/         #   统计输出 CSV
│
├── Picture/                # 所有可视化输出（仅 PNG）
│   ├── Map_Single/         #   单独空间分布图
│   │   ├── CMAQ/           #     {year}/{Case}{N}_{month}_{var}.png
│   │   ├── MCIP/           #     {year}/{var}_{month}.png
│   │   └── Emission/       #     {year}/PM2.5_{month}.png
│   ├── Map_Diff/           #   差异对比地图
│   │   ├── CMAQ/           #     {var}_{CaseX-CaseY}_{month}.png
│   │   ├── MCIP/           #     {var}_{year1}vs{year2}_{month}.png
│   │   └── Emission/       #     PM2.5_{year1}_minus_{year2}_{month}.png
│   ├── PDF/                #   KDE 分布对比图
│   │   ├── CMAQ/           #     {var}_{year}vs2023_{month}_{region}.png
│   │   ├── MCIP/           #     {var}_{year}vs2023_{month}_{region}.png
│   │   └── Emission/       #     PM2.5_{year}vs2023_{month}_{region}.png
│   ├── BarCharts/          #   柱状图
│   ├── BoxPlots/           #   箱线图
│   ├── CaseComparison/     #   CASE 对比汇总图
│   ├── Hourly/             #   小时级图表
│   └── Station/            #   站点校验图
│
├── docs/                   # 流程文档
│   ├── GuangDong项目架构规范_Core+Run分层设计.md  # 本文档
│   └── GuangDong_November_CodeAndDataExplanation.md
│
├── Other/                  # 归档废弃代码
│   ├── legacy_scripts/     #   旧版脚本（从 1_codenotuse/ 迁移）
│   └── legacy_outputs/     #   旧版输出（从 1_PictureAndDatenotuse/ 迁移）
│
├── esil/                   # 共享工具库（仅保留一份）
│   ├── __init__.py
│   ├── date_helper.py
│   ├── map_helper.py
│   ├── panelayout_helper.py
│   └── rsm_helper/
│       └── model_property.py
│
├── .gitignore
└── CLAUDE.md
```

---

## 四、Core+Run 分层架构

### 4.1 核心原则

```
┌──────────────────────────────────────────────┐
│  Run_*.py                                    │
│  - 硬编码路径配置（BASE_DIR, DATA_DIR 等）      │
│  - 硬编码年份/月份/变量/区域参数                 │
│  - 仅调用 Core_ 模块的函数                      │
│  - 不超过 50 行有效逻辑                         │
├──────────────────────────────────────────────┤
│  Core_*.py                                   │
│  - 纯函数，所有路径/参数通过函数签名传入          │
│  - 可被多个 Run_* 复用                         │
│  - 包含上层管道函数（接受 years/base_dir 等）     │
│  - 无 if __name__ == "__main__"               │
│  - 每个模块不超过 500 行                        │
├──────────────────────────────────────────────┤
│  esil/                                        │
│  - 底层工具库，无项目特定路径                    │
│  - 通过 import 或 sys.path 加载                │
│  - 仅保留一份，删除 esil_2/                     │
└──────────────────────────────────────────────┘
```

### 4.2 Run 入口脚本模板

```python
#!/usr/bin/env python3
"""
Run_Map_Diff.py - CMAQ/MCIP/Emission 差异对比地图
================================================
输入: Data/Processed/ 或 Data/Masked/
输出: Picture/Map_Diff/

使用方式:
    python Run_Map_Diff.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Core_Map import run_diff_map_pipeline

# ====== 配置 ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data", "Processed", "CMAQ")
OUTPUT_DIR = os.path.join(BASE_DIR, "Picture", "Map_Diff", "CMAQ")
MODEL_FILE = os.path.join(BASE_DIR, "Data", "Boundary", "GRIDCRO2D_2000121_GuangDongD3")
BOUNDARY_FILE = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"

DATA_SOURCE = "cmaq"       # "cmaq" | "mcip" | "emission"
VARIABLES = ["O3", "PM2.5", "O3_Days", "PM2.5_Days"]
COMPARISON_PAIRS = [
    # (文件1, 文件2, 输出标签)
    ("2000_Emission[2000met]_01.csv", "2023_Emission[2000met]_01.csv", "CASE1-CASE4_Jan"),
    ("2000_Emission[2000met]_07.csv", "2023_Emission[2000met]_07.csv", "CASE1-CASE4_Jul"),
]

# ====== 执行 ======
if __name__ == "__main__":
    run_diff_map_pipeline(
        data_dir=DATA_DIR,
        output_dir=OUTPUT_DIR,
        model_file=MODEL_FILE,
        boundary_file=BOUNDARY_FILE,
        data_source=DATA_SOURCE,
        variables=VARIABLES,
        comparison_pairs=COMPARISON_PAIRS,
    )
```

### 4.3 Core 模块模板

```python
"""
Core_Map.py - 空间地图绘制
===========================
提供函数:
  - plot_single_map(): 单独空间分布图
  - plot_difference_map(): 差异对比地图
  - run_single_map_pipeline(): 单独地图管道
  - run_diff_map_pipeline(): 差异地图管道

数据源: cmaq / mcip / emission
"""

from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from esil.rsm_helper.model_property import model_attribute
from esil.map_helper import get_multiple_data, show_maps


# === 数据源配置（纯配置字典，无路径） ===
DATA_SOURCE_CONFIGS = {
    "cmaq": {
        "variables": ["O3", "PM2.5", "O3_Days", "PM2.5_Days"],
        "variable_units": {"O3": "ppb", "PM2.5": "μg/m³", "O3_Days": "days", "PM2.5_Days": "days"},
        "file_pattern": "{year}_Emission[{year}met]_{month}",
        "default_cmap": "WhiteBlueGreenYellowRed",
    },
    "mcip": {
        "variables": ["TA_mean", "TA_max", "SOL_RAD_mean", "SOL_RAD_max", "PBLH_mean", "PBLH_max"],
        "variable_units": {"TA_mean": "°C", "TA_max": "°C", "SOL_RAD_mean": "W/m²", "SOL_RAD_max": "W/m²", "PBLH_mean": "m", "PBLH_max": "m"},
        "file_pattern": "{year}_mcipout_{month}",
    },
    "emission": {
        "variables": ["PM2.5"],
        "variable_units": {"PM2.5": "g/s"},
        "file_pattern": "EM_{year}{month}_PM2.5",
    },
}


def load_grid_data(csv_path: str, variable: str, grid_shape: Tuple[int, int]) -> np.ndarray:
    """加载 CSV 并重塑为网格数组。"""
    df = pd.read_csv(csv_path)
    df_sorted = df.sort_values(by=["ROW", "COL"])
    if variable not in df_sorted.columns:
        raise ValueError(f"列 '{variable}' 不存在于 {csv_path}")
    return df_sorted[variable].values.reshape(grid_shape)


def plot_single_map(
    grid_data: np.ndarray,
    longitudes: np.ndarray,
    latitudes: np.ndarray,
    projection,
    title: str,
    unit: str,
    output_path: str,
    boundary_file: Optional[str] = None,
    value_range: Optional[Tuple[float, float]] = None,
    cmap=None,
) -> str:
    """绘制单张空间分布图，保存为 PNG。"""
    ...


def plot_difference_map(
    data1: pd.DataFrame,
    data2: pd.DataFrame,
    variable: str,
    grid_shape: Tuple[int, int],
    longitudes: np.ndarray,
    latitudes: np.ndarray,
    projection,
    title: str,
    unit: str,
    output_path: str,
    boundary_file: Optional[str] = None,
    legend_range: Optional[Tuple[float, float]] = None,
    delta_cmap=None,
) -> str:
    """绘制差异对比地图（文件1 - 文件2），保存为 PNG。"""
    ...


def run_single_map_pipeline(
    data_dir: str,
    output_dir: str,
    model_file: str,
    boundary_file: str,
    years: List[str],
    months: List[str],
    data_source: str = "cmaq",
    variables: Optional[List[str]] = None,
    unified_legend: bool = False,
) -> Dict:
    """单独空间分布图管道函数。"""
    ...


def run_diff_map_pipeline(
    data_dir: str,
    output_dir: str,
    model_file: str,
    boundary_file: str,
    data_source: str = "cmaq",
    variables: List[str] = None,
    comparison_pairs: List[Tuple[str, str, str]] = None,
) -> Dict:
    """差异对比地图管道函数。"""
    ...
```

---

## 五、模块清单与职责

### 5.1 Core 模块

| Core 模块 | 职责 | 预估行数 | 被哪些 Run 调用 |
|-----------|------|----------|----------------|
| `Core_Extract.py` | CMAQ/MCIP/排放 NC 文件读取、逐网格数据提取、MDA8 计算、超标天数统计、CSV 输出 | ~500 | `Run_Extract.py` |
| `Core_Mask.py` | 从边界 JSON/NC 生成区域掩膜、应用掩膜将区域外网格置 NaN、支持广东/惠州/陆地三种掩膜 | ~300 | `Run_Mask.py` |
| `Core_Map.py` | 模型网格读取、CSV 加载、数据重塑、单独空间分布图、差异对比地图、统一/分开图例 | ~500 | `Run_Map_Single.py`, `Run_Map_Diff.py` |
| `Core_PDF.py` | CSV 加载、KDE 拟合、多年份 PDF 对比图、多区域/多变体支持 | ~300 | `Run_PDF.py` |
| `Core_Charts.py` | 面积*天数柱状图、CASE 对比箱线图、排放柱状图、统计表生成 | ~400 | `Run_BarCharts.py`, `Run_BoxPlots.py` |

### 5.2 Run 入口一览

| Run 脚本 | 类型 | 输入位置 | 输出位置 |
|----------|------|----------|----------|
| `Run_Extract.py` | 数据提取 | `Data/Raw/CMAQ/`, `Data/Raw/MCIP/` | `Data/Processed/CMAQ/`, `Data/Processed/MCIP/` |
| `Run_Mask.py` | 掩膜处理 | `Data/Processed/` | `Data/Masked/GuangDong/`, `Data/Masked/HuiZhou/`, `Data/Masked/Land/` |
| `Run_Map_Single.py` | 单独地图 | `Data/Processed/` 或 `Data/Masked/` | `Picture/Map_Single/{data_source}/` |
| `Run_Map_Diff.py` | 差异地图 | `Data/Processed/` 或 `Data/Masked/` | `Picture/Map_Diff/{data_source}/` |
| `Run_PDF.py` | PDF 分布图 | `Data/Processed/` 或 `Data/Masked/` | `Picture/PDF/{data_source}/` |
| `Run_BarCharts.py` | 柱状图 | `Data/Masked/GuangDong/` | `Picture/BarCharts/` |
| `Run_BoxPlots.py` | 箱线图 | `Data/Processed/` + `Data/Masked/HuiZhou/` | `Picture/BoxPlots/` |

---

## 六、Data 目录规范

```
Data/
├── Raw/                       # 原始 NC 输入（只读，不修改）
│   ├── CMAQ/                  #   CMAQ Daily COMBINE ACONC NC 文件
│   │   └── Daily_COMBINE_ACONC_v54_D3_*.nc
│   ├── MCIP/                  #   MCIP METCRO2D/3D NC 文件
│   │   └── METCRO2D_YYYYDDD.nc, METCRO3D_YYYYDDD.nc
│   └── Emission/              #   排放清单 NC 文件
│       └── EM_AV_YYYYDDD.nc
│
├── Processed/                 # 提取后的逐网格 CSV（全区域，无掩膜）
│   ├── CMAQ/                  #   污染物浓度+超标天数
│   │   └── {year}_Emission[{met_year}met]_{month}.csv
│   │       列: ROW, COL, O3, PM2.5, O3_Days, PM2.5_Days
│   ├── MCIP/                  #   气象变量统计
│   │   └── {year}_mcipout_{month}.csv
│   │       列: ROW, COL, TA_mean, TA_max, SOL_RAD_mean, SOL_RAD_max, PBLH_mean, PBLH_max
│   └── Emission/              #   排放清单月均值
│       └── EM_{year}{month}_PM2.5.csv
│           列: ROW, COL, PM2.5
│
├── Masked/                    # 区域掩膜后 CSV（非目标区域网格置 NaN）
│   ├── GuangDong/             #   广东省掩膜（原 cmaqout_processed_GuangDong/）
│   │   └── *_GuangDong.csv
│   ├── HuiZhou/               #   惠州掩膜（原 cmaqout_processed_HuiZhou/）
│   │   └── *_HuiZhou.csv
│   └── Land/                  #   陆地掩膜（原 cmaqout_processed_land/）
│       └── *_land.csv
│
├── Boundary/                  # 边界/网格文件（不经常变动）
│   ├── GRIDCRO2D_2000121_GuangDongD3   # 主网格定义文件
│   ├── GRIDCRO2D_2000121_GuangDongD1
│   ├── GRIDCRO2D_Huizhou_Flag.nc       # 惠州 Flag 掩膜
│   ├── HuiZhou_2000121_GuangDongD3.nc
│   ├── China_Provinces_2000121_GuangDongD3.nc
│   ├── China_provinces.json            # 省界 GeoJSON
│   ├── huizhou.json                    # 惠州边界
│   ├── huizhou_boundary.json
│   ├── china.json                      # 中国边界
│   └── china_cities.json               # 城市边界
│
├── Station/                   # 站点观测数据
│   └── (站点校验相关 CSV/NC)
│
├── Hourly/                    # 小时级数据
│   └── (热浪分析相关)
│
└── Statistics/                # 统计输出 CSV
    └── (CASE 对比统计表、百分位统计等)
```

**规则**：
- 子目录按**数据来源/处理阶段**命名（Raw → Processed → Masked → Statistics）
- 文件名保留 `{year}_{content}_{month}.csv` 格式，便于按年份检索
- `Boundary/` 集中存放所有不常变动的参考文件
- 原始 NC 文件移入 `Data/Raw/`，不放在根目录

---

## 七、Picture 目录规范

```
Picture/
├── Map_Single/                # 单独空间分布图（原 Emission_Alone_Plots_CN/ 等）
│   ├── CMAQ/                  #   {data_variant}/{year}/{CaseN}_{month}_{var}.png
│   ├── MCIP/                  #   {data_variant}/{year}/{var}_{month}.png
│   └── Emission/              #   {data_variant}/{year}/PM2.5_{month}.png
│
├── Map_Diff/                  # 差异对比地图（原 Emission_Comparison_Plots_CN/ 等）
│   ├── CMAQ/                  #   {var}_CASE{X}-CASE{Y}_{month}.png
│   ├── MCIP/                  #   {var}_{year1}vs{year2}_{month}.png
│   └── Emission/              #   PM2.5_{year1}_minus_{year2}_{month}.png
│
├── PDF/                       # KDE 分布对比图（原 Emission_Comparison_Plots_PDF_CN/ 等）
│   ├── CMAQ/                  #   {var}_{year}vs2023_{month}_{region}.png
│   ├── MCIP/                  #   {var}_{year}vs2023_{month}_{region}.png
│   └── Emission/              #   PM2.5_{year}vs2023_{month}_{region}.png
│
├── BarCharts/                 # 柱状图（原 BarCharts_Output_CaseComparison/ 等）
│   └── {var}_AreaDays_{month}_{region}.png
│
├── BoxPlots/                  # 箱线图（原 Boxplots_Output_CaseComparison/）
│   └── {var}_CaseComparison_{month}.png
│
├── CaseComparison/            # CASE 对比汇总图
├── Hourly/                    # 小时级图表（原 Mcip_Comparison_Plots_Hourly_Case/）
└── Station/                   # 站点校验图（原 臭氧颗粒物站点校验/）
```

**规则**：
- 按**图表类型/数据源**两级建子目录
- 多年结果用年份子目录（`Picture/Map_Single/CMAQ/{year}/`）
- **仅输出 PNG**，不输出 PDF
- 使用统一学术配色（`NATURE_COLORS`）

---

## 八、耦合规则

### 8.1 依赖层次（由上到下）

```
Run_*.py
  └── Core_*.py (同级 import)
        ├── esil/           (地图、日期工具)
        └── 标准库 (numpy, pandas, matplotlib, xarray, scipy 等)
```

### 8.2 禁止的依赖

- ❌ `Core_*.py` 不能 `import Run_*.py`
- ❌ `Core_*.py` 不能硬编码路径（必须通过参数传入）
- ❌ `Run_*.py` 之间不能互相 import
- ❌ `Core_*.py` 不能互相循环引用
- ❌ 不能 import `Other/` 下的文件
- ❌ 不能 import 废弃脚本（`1_codenotuse/`）

### 8.3 允许的依赖

- ✅ `Core_A.py` 可以 `import Core_B.py`（如 `Core_Map` 可使用 `Core_Mask` 的掩膜工具函数）
- ✅ `Run_*.py` 可以 `sys.path.insert(0, ...)` 后 `import` 任意 Core 模块
- ✅ `esil/` 通过 `from esil.xxx import yyy` 引用
- ✅ 所有 Core 模块可以 import 标准科学计算库

### 8.4 数据流方向

```
外部 NC 文件
  │
  ▼
Data/Raw/CMAQ/、Data/Raw/MCIP/、Data/Raw/Emission/
  │  (Core_Extract: NC→CSV)
  ▼
Data/Processed/CMAQ/、Data/Processed/MCIP/、Data/Processed/Emission/
  │  (Core_Mask: 应用区域掩膜)
  ▼
Data/Masked/GuangDong/、Data/Masked/HuiZhou/、Data/Masked/Land/
  │  (Core_Map / Core_PDF / Core_Charts: 加载→计算→绘图)
  ▼
Picture/Map_Single/、Picture/Map_Diff/、Picture/PDF/、Picture/BarCharts/、Picture/BoxPlots/
  └── 最终 PNG
```

---

## 九、当前脚本 → 目标模块重构对照表

### 9.1 数据提取 → Core_Extract.py

| 当前脚本 | 功能 | 合并方式 |
|----------|------|----------|
| `extract_Emssion_devinform_O3MDA8.py` | CMAQ NC→CSV（主脚本，含 FileConfig） | → `Core_Extract.extract_cmaq_batch()` |
| `extract_EmssionAndMcip_devinform_O3MDA8.py` | 同上（功能重复，旧版） | → 合并入 `Core_Extract`，废弃旧版 |
| `extract_EmssionAndMcip_项目提交_Daily.py` | 项目提交专用日值提取 | → `Core_Extract` 参数化 output_format |
| `extract_EmssionAndMcip_项目提交_Hourly.py` | 项目提交专用小时值提取 | → `Core_Extract` 参数化 temporal_resolution |
| `extract_Emssion_devinform_AnnualAvgPollutant.py` | 年平均污染物提取 | → `Core_Extract.extract_annual()` |
| `extract_Mcip_devinform_O3MDA8_heatwave.py` | 热浪气象提取 | → `Core_Extract` 参数化 mode="heatwave" |
| `extract_Mcip_hourly_heatwave.py` | 小时级热浪提取 | → `Core_Extract` 参数化 |
| `extract_Mcip_hourly_heatwave_D3_True.py` | D3 域热浪提取 | → `Core_Extract` 参数化 domain |
| `process_GDEI_ALL_True_AutoUnit.py` | 排放清单自动处理（推荐版） | → `Core_Extract.process_emission()` |
| `process_GDEI_ALL.py` | 排放清单处理（旧版） | → 废弃，用 True_AutoUnit 版 |

### 9.2 区域掩膜 → Core_Mask.py

| 当前脚本 | 功能 | 合并方式 |
|----------|------|----------|
| `mask_cmaqout_processed_to_GuangDong.py` | CMAQ CSV→广东掩膜 | → `Core_Mask.apply_mask(mask_type="guangdong")` |
| `mask_cmaqout_processed_to_land.py` | CMAQ CSV→陆地掩膜 | → `Core_Mask.apply_mask(mask_type="land")` |
| `mask_mcipout_processed_to_landandGuangDong.py` | MCIP CSV→陆地+广东掩膜 | → `Core_Mask` 批量处理 |
| `NaNHuiZhou_jform.py` | 惠州 Flag NC 生成 | → `Core_Mask.create_huizhou_flag()` |
| `NaNHuiZhou_mcip_1based.py` | 惠州 MCIP 掩膜 | → `Core_Mask.apply_mask(mask_type="huizhou", source="mcip")` |
| `NaNHuiZhou_peopleoutput_1based.py` | 惠州排放掩膜 | → `Core_Mask.apply_mask(mask_type="huizhou", source="emission")` |

### 9.3 单独空间地图 → Core_Map.py (mode="single")

| 当前脚本 | 数据源 | 合并方式 |
|----------|--------|----------|
| `MapForAlone_emission_CN.py` | CMAQ | → `run_single_map_pipeline(data_source="cmaq")` |
| `MapForAlone_emission_CN_Case.py` | CMAQ (Case) | → 参数化 case_filter |
| `MapForAlone_emission_CN_Case_land.py` | CMAQ (Case+Land) | → 参数化 data_variant="land" |
| `MapForAlone_mcipout_CN.py` | MCIP | → `run_single_map_pipeline(data_source="mcip")` |
| `MapForAlone_mcipout_CN_Hourly.py` | MCIP (Hourly) | → 参数化 temporal_resolution="hourly" |
| `MapForAlone_mcipout_CN_land.py` | MCIP (Land) | → 参数化 data_variant="land" |
| `MapForAlone_peopleoutput_CN.py` | Emission | → `run_single_map_pipeline(data_source="emission")` |
| `MapForAlone_wrfout_CN.py` | WRF | → 参数化 data_source="wrf" |

### 9.4 差异对比地图 → Core_Map.py (mode="diff")

| 当前脚本 | 数据源 | 合并方式 |
|----------|--------|----------|
| `MapForDiffrenceBetweenDatasets_emission_CN.py` | CMAQ (CN 版，推荐) | → `run_diff_map_pipeline(data_source="cmaq")` |
| `MapForDiffrenceBetweenDatasets_emission.py` | CMAQ (旧版) | → 废弃 |
| `MapForDiffrenceBetweenDatasets_mcipout_CN.py` | MCIP (CN 版) | → `run_diff_map_pipeline(data_source="mcip")` |
| `MapForDiffrenceBetweenDatasets_mcipout.py` | MCIP (旧版) | → 废弃 |
| `MapForDiffrenceBetweenDatasets_peopleoutput_CN.py` | Emission (CN 版) | → `run_diff_map_pipeline(data_source="emission")` |
| `MapForDiffrenceBetweenDatasets_peopleoutput.py` | Emission (旧版) | → 废弃 |
| `MapForDiffrenceBetweenDatasets_mcipout_CN_hourly.py` | MCIP 小时级 | → 参数化 temporal_resolution |
| `MapForDiffrenceBetweenDatasets_mcipout_CN_hourly_Case.py` | MCIP 小时级 Case | → 参数化 |
| `MapForDiffrenceBetweenDatasets_wrfout_CN_hourly.py` | WRF 小时级 | → 参数化 data_source="wrf" |

### 9.5 PDF 分布图 → Core_PDF.py

| 当前脚本 | 数据源 | 合并方式 |
|----------|--------|----------|
| `PDF_emssion_kde_simply.py` | CMAQ (推荐版) | → `run_pdf_pipeline(data_source="cmaq")` |
| `PDF_emssion_kde_simply_AddBar.py` | CMAQ + 柱状图叠加 | → 参数化 add_bar=True |
| `PDF_emission_kde_simply_Four.py` | CMAQ 四 CASE 对比 | → 参数化 case_mode="four" |
| `PDF_emission_kde_simply_Muti.py` | CMAQ 多情景 | → 参数化 case_mode="multi" |
| `PDF_mcipout_kde_simply.py` | MCIP | → `run_pdf_pipeline(data_source="mcip")` |
| `PDF_mcipout_kde_simply_AddBar.py` | MCIP + 柱状图 | → 参数化 |
| `PDF_mcipout_kde_simply_Hourly.py` | MCIP 小时级 | → 参数化 |
| `PDF_mcipout_kde_simply_Muti.py` | MCIP 多情景 | → 参数化 |
| `PDF_peopleoutput_kde_simply.py` | Emission | → `run_pdf_pipeline(data_source="emission")` |

### 9.6 柱状图 → Core_Charts.py (mode="bar")

| 当前脚本 | 功能 | 合并方式 |
|----------|------|----------|
| `BarChartsForPM2.5O3_Case_面积*天数_emission.py` | CMAQ 面积*天数柱状图 | → `run_bar_pipeline(data_source="cmaq")` |
| `BarChartsForPM2.5O3_Case_面积*天数_emission_Case1_3.py` | CASE1-3 变体 | → 参数化 cases |
| `BarChartsForPM2.5O3_Case_面积*天数_mcipout.py` | MCIP 面积*天数 | → `run_bar_pipeline(data_source="mcip")` |
| `BarChartsForPM2.5O3_Case_面积*天数_mcipout_Case1_3.py` | MCIP CASE1-3 变体 | → 参数化 |
| `BarChartsForPM2.5O3_Case_面积*天数_Combined_Case1_3.py` | 合并图 | → 参数化 combined=True |
| `BarCharts_peopleoutput_CN.py` | 排放柱状图 | → `run_bar_pipeline(data_source="emission")` |
| `BarCharts_peopleoutput_CN_AnnualAndMonth.py` | 排放年/月柱状图 | → 参数化 |
| `BarCharts_peopleoutput_CN_AnnualAndMonth_原始清单.py` | 原始清单版 | → 参数化 |
| `BarCharts_peopleoutput_CN_v1.py` | v1 版 | → 废弃 |

### 9.7 箱线图 → Core_Charts.py (mode="box")

| 当前脚本 | 功能 | 合并方式 |
|----------|------|----------|
| `BoxplotsForPM2.5O3_Case.py` | CASE 对比箱线图 | → `run_box_pipeline()` |
| `MapForBoxplots_Emission.py` | 箱线图辅助地图 | → 作为 `Core_Charts` 内部辅助函数 |
| `MapForBoxplots_Emission_Case.py` | 同上 Case 版 | → 参数化 |

### 9.8 工具/辅助类

| 当前脚本 | 合并方式 |
|----------|----------|
| `filter_guangdong_weather.py` | → 保留为独立工具或作为 Core 内部函数 |
| `match_lab_stations_coords.py` | → 保留为独立工具 |
| `fix_timepoint_in_lab_results.py` | → 保留为独立工具 |
| `check_hour_structure.py` | → 保留为独立工具 |

---

## 十、重构步骤建议

### 第一阶段：目录骨架（预计 0.5 天）

1. 创建 `docs/` 目录，放入本文档
2. 创建 `Data/` 子目录结构：`Raw/CMAQ/`, `Raw/MCIP/`, `Raw/Emission/`, `Processed/CMAQ/`, `Processed/MCIP/`, `Processed/Emission/`, `Masked/GuangDong/`, `Masked/HuiZhou/`, `Masked/Land/`, `Boundary/`, `Station/`, `Hourly/`, `Statistics/`
3. 创建 `Picture/` 子目录结构：`Map_Single/CMAQ/`, `Map_Single/MCIP/`, `Map_Single/Emission/`, `Map_Diff/CMAQ/`, `Map_Diff/MCIP/`, `Map_Diff/Emission/`, `PDF/CMAQ/`, `PDF/MCIP/`, `PDF/Emission/`, `BarCharts/`, `BoxPlots/`, `CaseComparison/`, `Hourly/`, `Station/`
4. 创建 `Other/legacy_scripts/` 和 `Other/legacy_outputs/`
5. 删除 `esil_2/`，统一使用根目录 `esil/`
6. 移动边界/网格文件到 `Data/Boundary/`
7. 更新 `.gitignore`：排除 `__pycache__/`、`Data/Raw/`（大文件）、`Picture/`（生成物）

### 第二阶段：Core 模块提取（预计 2-3 天）

按功能域逐步提取，**每提取一个模块立即配套一个 Run 入口验证**：

1. `Core_Mask.py` — 掩膜生成与应用（功能相对独立，适合首先提取）
   - 配套 `Run_Mask.py`
   - 测试：运行 mask → 验证输出 CSV 与原脚本输出一致

2. `Core_Extract.py` — 数据提取（最核心的预处理逻辑）
   - 配套 `Run_Extract.py`
   - 测试：运行提取 → 验证 CSV 格式、数值与原脚本一致

3. `Core_Map.py` — 空间地图绘制（最复杂，最大模块）
   - 配套 `Run_Map_Single.py` + `Run_Map_Diff.py`
   - 测试：运行所有数据源的地图绘制

4. `Core_PDF.py` — KDE 分布图（逻辑清晰，改动较小）
   - 配套 `Run_PDF.py`

5. `Core_Charts.py` — 柱状图 + 箱线图
   - 配套 `Run_BarCharts.py` + `Run_BoxPlots.py`

### 第三阶段：Data 目录重组（预计 1 天）

1. 将 `cmaqout_processed/*.csv` → `Data/Processed/CMAQ/`
2. 将 `mcipout_processed/*.csv` → `Data/Processed/MCIP/`
3. 将 `emissionlist/EM_*.csv` → `Data/Processed/Emission/`
4. 将 `cmaqout_processed_GuangDong/*.csv` → `Data/Masked/GuangDong/`
5. 将 `cmaqout_processed_HuiZhou/*.csv` → `Data/Masked/HuiZhou/`
6. 将 `cmaqout_processed_land/*.csv` → `Data/Masked/Land/`
7. 同样处理 `mcipout_processed_*` 和 `emissionlist_HuiZhou/`
8. 将 `cmaqout/`, `mcipout/`, `wrfout/` 下 NC 文件 → `Data/Raw/`
9. 更新所有 Run 脚本中的路径配置

### 第四阶段：废弃代码归档（预计 0.5 天）

1. `1_codenotuse/` 下全部脚本 → `Other/legacy_scripts/`
2. `1_PictureAndDatenotuse/` 下全部内容 → `Other/legacy_outputs/`
3. `claude_analysisreport_used/` → 保留或移入 `docs/`
4. `校验Zip/` → `Other/`
5. `cmaq_项目提交/`, `cmaq_项目提交_hourly/` → `Other/`
6. 清理旧的输出目录（`Emssion_Comparison_Plots/`, `Emission_Comparison_Plots_PDF_CN/` 等），保留最新生成的图片在 `Picture/`

---

## 十一、关键规范清单

| # | 规范 | 说明 |
|---|------|------|
| 1 | Core/Run 分离 | Core 纯函数、Run 纯配置 |
| 2 | 路径参数化 | Core 不出现任何硬编码路径 |
| 3 | 平面顶层 | 所有 Core_/Run_ 在项目根目录 |
| 4 | Data/ 按处理阶段 | Raw → Processed → Masked → Statistics |
| 5 | Picture/ 按图类型+数据源 | Map_Single/{cmaq\|mcip\|emission}/ |
| 6 | 仅 PNG 输出 | 不生成 PDF |
| 7 | 统一学术配色 | `NATURE_COLORS` |
| 8 | 单模块职责 | 每个 Core 不超过 500 行 |
| 9 | 命名一致性 | CASE 统一大写（CASE1-CASE6）；变量命名遵循 DATA_SOURCE_CONFIGS |
| 10 | esil 单例 | 项目根目录只保留一份 esil/ |
| 11 | Other/ 归档 | 废弃代码不移入 Core/Run |
| 12 | CASE 配置集中 | CASE_DEFINITIONS 字典只在 Core_Extract 定义一次，其他模块 import |
| 13 | 数据变体参数化 | 区域（raw/land/GuangDong/HuiZhou）通过参数切换，不复刻脚本 |
| 14 | 无循环引用 | Core 模块之间单向依赖 |
| 15 | docstring 完整 | 每个 Core 模块有模块级 docstring，每个函数有参数说明 |

---

## 十二、CASE 定义规范（全局统一）

为避免不同脚本中各写一套 CASE 映射，统一在 `Core_Extract.py` 中定义，其他模块引入：

```python
# Core_Extract.py（唯一权威定义）
CASE_DEFINITIONS = {
    # CASE: (emission_year, met_year, 描述)
    'CASE1': ('2000', '2000', '2000e2000m'),  # 2000排放 + 2000气象
    'CASE2': ('2000', '2023', '2000e2023m'),  # 2000排放 + 2023气象
    'CASE3': ('2023', '2023', '2023e2023m'),  # 2023排放 + 2023气象（基准）
    'CASE4': ('2023', '2000', '2023e2000m'),  # 2023排放 + 2000气象
    'CASE5': ('2060', '2060', '2060e2060m'),  # 2060排放 + 2060气象
    'CASE6': ('2030', '2030', '2030e2030m'),  # 2030排放 + 2030气象
}
```

---

*本文档版本: 2026-05 (v1)*
*下一步: 按第十节重构步骤开始实施*

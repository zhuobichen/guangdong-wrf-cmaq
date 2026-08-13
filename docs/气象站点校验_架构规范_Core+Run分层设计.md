# 气象站点校验 架构规范

> 目标：对气象站点 MCIP 校验工作流进行 Core+Run 分层重构
> 版本: 2026-05 (v1)
> 基准参考: `GuangDong/docs/GuangDong项目架构规范_Core+Run分层设计.md`
> 项目路径: `/data/workspace/GuangDong/气象站点`

---

## 一、工作流概述

气象站点校验是一个**独立于 CMAQ 主分析管线**的子工作流，核心任务：

| 阶段 | 描述 |
|------|------|
| 数据完整性检查 | 筛选 ISD 气象站点中具有全年完整数据的站点 |
| 代表站点选取 | 按地理分布均匀原则选取 4 个校验站点（韶关、汕头、深圳宝安、湛江） |
| 格式转换 | 将 ISD 原始 CSV（DATE, TEMP, ...）转为标准校验表（Date, Lat, Lon, Obs_Temperature, ...） |
| MCIP 模型提取 | 从 METCRO2D/GRIDDOT2D NC 文件中提取站点对应网格的气象变量（TEMP2, Q2, PRSFC, WSPD10, WDIR10） |
| 时序图绘制 | 生成观测 vs 模型时间序列对比图（温度/湿度/气压/风速/风向） |
| 校验报表 | 生成校验结果数据表（xlsx） |

**当前支持年份**: 2000、2023
**站点类型**: 气象台站（99999 编号）+ 实验室站点（城市编码）

---

## 二、现状问题诊断

### 2.1 核心问题

| # | 问题 | 当前状态 | 影响 |
|---|------|----------|------|
| 1 | 无 Core/Run 分层 | 20+ 个脚本平铺在目录根下，每个含逻辑+配置 | 逻辑重复，公共函数散落各文件 |
| 2 | 数据/输出混放 | `2000_GuangDong/`、`2023_GuangDong/`、`*_校验表/`、`*_含MCIP/` 等 15+ 个子目录平铺 | 无法快速定位数据 |
| 3 | 硬编码路径 | 每个脚本内部直接写死绝对路径 | 年份/站点切换需改多份脚本 |
| 4 | 脚本变体多 | `6.1_`、`6.2_`、`6.3_` 仅有微小差异（温度 vs 风 vs 全变量） | 参数化即可合并 |
| 5 | log 文件堆积 | 根目录 10 个 `.log` 文件 | 混淆工作区 |
| 6 | 多余文档混放 | `MCIP数据提取与校验总结.md`、`完整工作流程文档.md`、`脚本使用说明.md`、`运行流程说明.md` 共 4 份 | 应统一到 docs/ |
| 7 | .cache 未清理 | `.cache/`、`__pycache__/` | 应被 .gitignore |
| 8 | 2000/2023 脚本分离 | 2000 年和 2023 年有独立的提取/绘图脚本 | 参数化年份即可合并 |

### 2.2 脚本统计

| 类别 | 数量 | 代表 |
|------|------|------|
| 数据筛选 | 3 | `1_检查全年数据完整性.py`, `2_提取站点名称.py`, `3_选择校验站点.py` |
| 格式转换 | 2 | `4_转换为校验表格式.py`, `4_转换为校验表格式_惠州.py` |
| MCIP 提取 | 1 | `5_MCIP数据提取脚本.py` (599 行，核心) |
| 实验室提取 | 2 | `4-5.3_实验室校验脚本.py`, `4-5.4_实验室校验脚本_实验室网格.py` |
| 时序图绘制 | 4 | `6.1_绘制校验时间序列图_2023.py`, `6.2_*_Wind0.py`, `6.3_*_温度_2023.py`, `6_绘制校验时间序列图.py` |
| 报表生成 | 3 | `7.1_生成校验结果数据表_2023.py`, `7.2_*_温度_2023.py`, `7_生成校验结果数据表_2000.py` |
| 辅助 | 1 | `提取模型数据到校验表.py` |
| 废弃变体 | 1 | `5.2_MCIP数据提取脚本_优化版_v2_NotUse.py` |

---

## 三、目标顶层目录结构

```
GuangDong/
├── ...（主分析管线 Core_/Run_，不变）...
│
├── Data/
│   └── Station/                              # 气象站点数据（新增子目录）
│       ├── Raw/                              #   ISD 原始站点 CSV（只读）
│       │   ├── 2000/                         #     {站点编号}.csv
│       │   └── 2023/
│       ├── Processed/                        #   标准校验表
│       │   ├── 2000/                         #     {站点编号}_校验表.csv
│       │   └── 2023/
│       └── Validation/                       #   含 MCIP 模型数据的校验表
│           ├── 2000/                         #     {站点编号}_校验表_含MCIP模型数据.csv
│           └── 2023/
│
├── Picture/
│   └── Station/                              # 气象校验图（新增子目录）
│       ├── Timeseries/                       #   时间序列对比图
│       │   ├── 2000/                         #     {站点名}_时间序列对比_{时段}.png
│       │   └── 2023/
│       └── StationMap/                       #   站点分布图
│
├── Core_WeatherValidation.py                 # 核心模块：校验全流程
├── Run_WeatherValidation.py                  # 入口：校验配置
│
├── docs/
│   ├── GuangDong项目架构规范_Core+Run分层设计.md
│   └── 气象站点校验_架构规范_Core+Run分层设计.md  # 本文档
│
└── 气象站点/                                  # 仅保留数据，代码迁移到根目录
    ├── 2000_GuangDong/                       #   Raw 源数据
    ├── 2023_GuangDong/                       #   Raw 源数据
    └── Other/                                #   归档废弃脚本
```

---

## 四、Core+Run 分层设计

### 4.1 核心原则

```
┌──────────────────────────────────────────────┐
│  Run_WeatherValidation.py                    │
│  - 硬编码路径配置（BASE_DIR, DATA_DIR 等）      │
│  - 硬编码年份/站点/变量参数                      │
│  - 仅调用 Core_WeatherValidation 模块的函数     │
│  - 不超过 60 行有效逻辑                         │
├──────────────────────────────────────────────┤
│  Core_WeatherValidation.py                    │
│  - 纯函数，所有路径/参数通过函数签名传入          │
│  - 包含以下功能域:                              │
│    1. 数据完整性检查                            │
│    2. 校验表格式转换                            │
│    3. MCIP 网格匹配与数据提取                    │
│    4. 时间序列对比图绘制                        │
│    5. 校验结果报表生成                           │
│  - 每个功能域不超过 150 行                       │
│  - 无 if __name__ == "__main__"               │
├──────────────────────────────────────────────┤
│  esil/                                        │
│  - 底层工具库，无项目特定路径                    │
└──────────────────────────────────────────────┘
```

### 4.2 模块设计

| Core 模块 | 职责 | 预估行数 |
|-----------|------|----------|
| `Core_WeatherValidation.py` | 站点数据筛选、校验表转换、MCIP 网格匹配提取、时序图绘制、报表生成 | ~500 |

**设计理由**：气象站点校验是一个相对紧凑的工作流（5 个阶段），合并为一个 Core 模块比拆分为 5 个小模块更合理，避免过度碎片化。主 CMAQ 管线已有 5 个 Core 模块，气象校验作为辅助工作流用一个 Core 模块足矣。

### 4.3 Run 入口脚本模板

```python
#!/usr/bin/env python3
"""
Run_WeatherValidation.py — 气象站点 MCIP 校验入口
==================================================
用法:
    python Run_WeatherValidation.py [--year 2000|2023] [--step all|check|convert|extract|plot|report]
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Core_WeatherValidation import (
    check_data_completeness,
    convert_to_validation_table,
    extract_mcip_data,
    plot_timeseries_comparison,
    generate_validation_report,
)

# ====== 配置 ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "Data", "Station", "Raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "Data", "Station", "Processed")
VALIDATION_DIR = os.path.join(BASE_DIR, "Data", "Station", "Validation")
MCIP_DIR = os.path.join(BASE_DIR, "mcipout")
PICTURE_DIR = os.path.join(BASE_DIR, "Picture", "Station", "Timeseries")

YEARS = [2000, 2023]
STATIONS = {
    '59082099999': '韶关',
    '59316099999': '汕头',
    '59493099999': '深圳宝安',
    '59658099999': '湛江',
}

# ====== 执行 ======
if __name__ == "__main__":
    for year in YEARS:
        # Step 1: 数据完整性检查
        check_data_completeness(RAW_DIR, PROCESSED_DIR, year)
        # Step 2: 校验表转换
        convert_to_validation_table(PROCESSED_DIR, PROCESSED_DIR, year, STATIONS)
        # Step 3: MCIP 数据提取
        extract_mcip_data(MCIP_DIR, PROCESSED_DIR, VALIDATION_DIR, year, STATIONS)
        # Step 4: 时序图绘制
        plot_timeseries_comparison(VALIDATION_DIR, PICTURE_DIR, year, STATIONS)
        # Step 5: 报表生成
        generate_validation_report(VALIDATION_DIR, year, STATIONS)
```

---

## 五、当前脚本 → 目标模块重构对照表

### Core_WeatherValidation.py 函数映射

| 函数 | 职责 | 来源于 |
|------|------|--------|
| `check_data_completeness()` | 检查站点数据是否覆盖全年，筛选完整站点 | `1_检查全年数据完整性.py` |
| `select_representative_stations()` | 按地理分布选取代表站点 | `2_提取站点名称.py` + `3_选择校验站点.py` |
| `convert_to_validation_table()` | ISD 原始 CSV → 标准校验表格式 | `4_转换为校验表格式.py` + `4_转换为校验表格式_惠州.py` |
| `get_grid_from_latlon()` | 经纬度 → ROW/COL（KD-Tree 球面距离） | `5_MCIP数据提取脚本.py` 中的 `get_grid_from_latlon()` |
| `read_metcro2d_data()` | 读取 METCRO2D NC 文件 | `5_MCIP数据提取脚本.py` 中的 `read_metcro2d_data()` |
| `calculate_relative_humidity()` | 从 Q2 计算相对湿度 | `5_MCIP数据提取脚本.py` 中的 `calculate_relative_humidity()` |
| `extract_mcip_data()` | 遍历校验表，提取 MCIP 网格数据并填充 | `5_MCIP数据提取脚本.py` 中的 `process_station()` |
| `plot_timeseries_comparison()` | 绘制观测 vs 模型时间序列对比图 | `6.1_`、`6.2_`、`6.3_`、`6_` 合并 |
| `generate_validation_report()` | 生成校验统计 xlsx 报表 | `7.1_`、`7.2_`、`7_` 合并 |

### 废弃/特殊处理

| 当前脚本 | 处理方式 |
|----------|----------|
| `5.2_MCIP数据提取脚本_优化版_v2_NotUse.py` | → 移入 `气象站点/Other/` |
| `4-5.3_实验室校验脚本.py` | → 保留为独立脚本（实验室站点逻辑与气象台站差异大） |
| `4-5.4_实验室校验脚本_实验室网格.py` | → 保留为独立脚本 |
| `提取模型数据到校验表.py` | → 功能已包含在 `extract_mcip_data()`，废弃 |
| 10 个 `.log` 文件 | → 删除，改为代码内 `logging` 模块输出 |
| 4 份 md 文档 | → 合并到 `docs/` 下的本文档 |

---

## 六、Data 目录规范

```
Data/Station/
├── Raw/                                   # ISD 原始站点数据（只读）
│   ├── 2000/                              #   {站点编号}.csv（列: DATE, TEMP, DEWP, SLP, STP, VISIB, WDSP, MXSPD, GUST, MAX, MIN, PRCP, SNDP, FRSHTT）
│   └── 2023/
│
├── Processed/                             # 标准校验表（观测值）
│   ├── 2000/                              #   {站点编号}_校验表.csv（列: Date, Lat, Lon, Station, Obs_Temperature, Obs_Humidity, Obs_AirPress, Obs_WindSpeed, Obs_WindDirection）
│   └── 2023/
│
└── Validation/                            # 含 MCIP 模型数据的完整校验表
    ├── 2000/                              #   {站点编号}_校验表_含MCIP模型数据.csv
    └── 2023/                              #   （在上述列基础上 + Grid_ROW, Grid_COL, Grid_Temperature, Grid_Humidity, Grid_AirPress, Grid_WindSpeed, Grid_WindDirection）
```

---

## 七、Picture 目录规范

```
Picture/Station/
├── Timeseries/                            # 时间序列对比图
│   ├── 2000/
│   │   ├── {站点名}_温度对比_1月.png
│   │   ├── {站点名}_温度对比_7月.png
│   │   ├── {站点名}_温度对比_全年.png
│   │   ├── {站点名}_湿度对比_1月_7月.png
│   │   └── {站点名}_全变量对比_1月_7月.png
│   └── 2023/
│
└── StationMap/                            # 站点分布地图
    └── {year}_站点分布_广东.png
```

---

## 八、耦合规则

### 8.1 依赖层次

```
Run_WeatherValidation.py
  └── Core_WeatherValidation.py
        ├── 标准库 (numpy, pandas, matplotlib, xarray, scipy, netCDF4)
        └── （无 esil 依赖，气象校验使用独立的地图绘制逻辑）
```

### 8.2 禁止的依赖

- ❌ Core_WeatherValidation.py 不能硬编码路径
- ❌ Core_WeatherValidation.py 不能 import 主分析管线的 Core_Extract / Core_Map 等
- ❌ 不能 import `气象站点/` 下的其他脚本

### 8.3 数据流

```
ISD 原始 CSV（气象站点/Raw/）
  │  check_data_completeness()
  ▼
完整站点 CSV（气象站点/Raw/+Data/Station/Raw/）
  │  convert_to_validation_table()
  ▼
标准校验表（Data/Station/Processed/）
  │  extract_mcip_data()
  ▼
含 MCIP 校验表（Data/Station/Validation/）
  │  plot_timeseries_comparison() / generate_validation_report()
  ▼
Picture/Station/Timeseries/ + xlsx 报表
```

---

## 九、重构步骤

### 第一阶段：目录整理（0.3 天）

1. 将 `气象站点/2000_GuangDong/` → `Data/Station/Raw/2000/`
2. 将 `气象站点/2023_GuangDong/` → `Data/Station/Raw/2023/`
3. 将 `*_校验表/` → `Data/Station/Processed/`
4. 将 `*_校验表_含MCIP模型数据/`（以及 `*_GridLab/`） → `Data/Station/Validation/`
5. 创建 `Picture/Station/Timeseries/` 和 `Picture/Station/StationMap/`
6. 删除 10 个 `.log` 文件和 `.cache/` 目录
7. 合并 4 份 md 文档到 `docs/`
8. 废弃脚本移入 `气象站点/Other/`

### 第二阶段：Core 模块提取（1 天）

1. 从 `5_MCIP数据提取脚本.py` 提取公共函数（`get_grid_from_latlon`, `read_metcro2d_data`, `calculate_relative_humidity`）
2. 参数化所有硬编码路径为函数参数
3. 合并 4 个绘图脚本变体为一个 `plot_timeseries_comparison()`（参数化 mode: temperature/wind/all）
4. 合并 3 个报表脚本为 `generate_validation_report()`
5. 创建 `Core_WeatherValidation.py`

### 第三阶段：Run 入口 + 验证（0.5 天）

1. 创建 `Run_WeatherValidation.py`
2. 运行 2000 年全流程，对比输出一致
3. 运行 2023 年全流程，对比输出一致
4. 更新 `.gitignore`

---

## 十、关键规范清单

| # | 规范 | 说明 |
|---|------|------|
| 1 | 单 Core 模块 | `Core_WeatherValidation.py` 不超过 500 行 |
| 2 | 路径参数化 | 所有路径通过函数签名传入 |
| 3 | 年份参数化 | `year` 参数切换 2000/2023，不复刻脚本 |
| 4 | 数据按年份分层 | `Data/Station/{Raw,Processed,Validation}/{year}/` |
| 5 | Picture 按年份分层 | `Picture/Station/Timeseries/{year}/` |
| 6 | 统一输出 PNG | 不输出 PDF |
| 7 | log 文件 → logging 模块 | 运行时输出到控制台，不生成独立 log 文件 |
| 8 | 变量模式参数化 | `plot_timeseries_comparison(mode="temperature|wind|all")` |
| 9 | 站点配置字典化 | `STATIONS = {id: name}` 在 Run 入口统一定义 |
| 10 | 文档统一到 docs/ | 不在代码目录放 md |

---

*本文档版本: 2026-05 (v1)*
*下一步: 按第九节重构步骤开始实施*

# GuangDong Code and Data Documentation

**Base Path**: `/data/workspace/GuangDong`

## 📋 快速索引

### 📁 Data Folders
- **cmaqout_processed/**: CMAQ model output data
- **mcipout_processed/**: MCIP meteorological preprocessing data
- **emissionlist/**: PM2.5 emission source data
- **_HuiZhou suffix folders**: Huizhou region specific data

### 📊 Script Types
- **MapForDiffrenceBetweenDatasets_*.py**: Difference comparison analysis scripts
- **MapForAlone_*.py**: Individual plotting scripts
- **PDF_*.py**: Probability density distribution scripts
- **extract_*.py**: Data extraction scripts

---

## 🗂️ Data File Formats

### Guangdong Province Full Region Data
| Folder | Format | Example |
|--------|------|------|
| `cmaqout_processed/` | `{year}_Emission[{year}met]_{month}.csv` | `2000_Emission[2000met]_01.csv` |
| `mcipout_processed/` | `{year}_mcipout_{month}.csv` | `2030_mcipout_07.csv` |
| `emissionlist/` | `EM_{year}{month}_PM2.5.csv` | `EM_202301_PM2.5.csv` |

### Huizhou Region Data (`_HuiZhou` Suffix)
| Folder | Format | Example |
|--------|------|------|
| `cmaqout_processed_HuiZhou/` | `{year}_Emission[{year}met]_{month}_HuiZhou.csv` | `2000_Emission[2000met]_01_HuiZhou.csv` |
| `mcipout_processed_HuiZhou/` | `{year}_mcipout_{month}_HuiZhou.csv` | `2030_mcipout_07_HuiZhou.csv` |
| `emissionlist_HuiZhou/` | `EM_{year}{month}_PM2.5_HuiZhou.csv` | `EM_202301_PM2.5_HuiZhou.csv` |

### Year and Month Codes
- **Years**: 2000, 2023, 2030, 2060
- **Months**: 01 (January), 07 (July)

## 📖 Detailed Script Description

### 🔄 差异对比分析脚本 (`MapForDiffrenceBetweenDatasets_*.py`)

**功能**: 生成不同数据集之间的差值地图，支持年份、气象条件、排放清单对比

#### 📊 `MapForDiffrenceBetweenDatasets_emission.py`
| 项目 | 详情 |
|------|------|
| **功能** | 绘制CMAQ输出变量差值地图 |
| **支持变量** | O3, PM2.5, O3_Days, PM2.5_Days |
| **输出示例** | `O3_Conc_2023e2000m_2023e2023m_Jan.png` |
| **对比类型** | 清单变化: `(2000e - 2023e)2023m`<br>气象变化: `2023e(2000m - 2023m)`<br>综合变化: `2000 - 2023` |

#### 🌡️ `MapForDiffrenceBetweenDatasets_mcipout.py`
| 项目 | 详情 |
|------|------|
| **功能** | 绘制气象变量差值地图 |
| **支持变量** | TA_mean, TA_max, SOL_RAD_mean, SOL_RAD_max, PBLH_mean, PBLH_max |
| **输出示例** | `TA_2000vs2023_07Mean.png` |
| **变量映射** | TA → Temperature (°C)<br>SOL_RAD → SOLAR (W/m²)<br>PBLH → PBLH (m) |

#### 💨 `MapForDiffrenceBetweenDatasets_peopleoutput.py`
| 项目 | 详情 |
|------|------|
| **功能** | 绘制PM2.5排放变量差值地图 |
| **支持变量** | PM2.5 |
| **输出示例** | `PM25_2000_minus_2023_January.png` |
| **单位** | g/s |

### 🗺️ 单独绘制脚本 (`MapForAlone_*.py`)

**功能**: 生成各变量的空间分布图，支持多年份批量处理和统一/分开图例模式

#### 📊 `MapForAlone_emission.py`
| 项目 | 详情 |
|------|------|
| **功能** | 绘制CMAQ变量空间分布图 |
| **支持变量** | O3, PM2.5, O3_Days, PM2.5_Days |
| **输入格式** | `{year}_Emission[{year}met]_{month}.csv` |
| **输出示例** | `202301_O3.png` |
| **特点** | 支持统一/分开图例模式 |

#### 🌡️ `MapForAlone_mcipout.py`
| 项目 | 详情 |
|------|------|
| **功能** | 绘制气象变量空间分布图 |
| **支持变量** | TA_mean, TA_max, SOL_RAD_mean, SOL_RAD_max, PBLH_mean, PBLH_max |
| **输入格式** | `{year}_mcipout_{month}.csv` |
| **输出示例** | `200001_TA_mean.png` |

#### 💨 `MapForAlone_peopleoutput.py`
| 项目 | 详情 |
|------|------|
| **功能** | 绘制PM2.5排放空间分布图 |
| **支持变量** | PM2.5 |
| **输入格式** | `EM_{year}{month}_PM2.5.csv` |
| **输出示例** | `PM2.5 (January Mean): 2023.png` |

### 📈 概率密度分布脚本 (`PDF_*.py`)

**功能**: 生成变量的概率密度函数(PDF)图，使用KDE核密度估计方法，支持自动化对比分析

#### 📊 `PDF_emssion_kde_simply.py`
| 项目 | 详情 |
|------|------|
| **功能** | 生成CMAQ变量KDE分布对比图 |
| **支持变量** | O3, PM2.5 |
| **输出示例** | `O3_2000vs2023_01.png` |
| **对比年份** | 2000/2030/2060 vs 2023 |
| **地区支持** | 全省 + 惠州 |

#### 🌡️ `PDF_mcipout_kde_simply.py`
| 项目 | 详情 |
|------|------|
| **功能** | 生成气象变量KDE分布对比图 |
| **支持变量** | TA_mean, TA_max, SOL_RAD_mean, SOL_RAD_max, PBLH_mean, PBLH_max |
| **输出示例** | `TA_mean_2000vs2023_01_GuangDong.png` |
| **地区** | normal (全省) / huizhou |

#### 💨 `PDF_peopleoutput_kde_simply.py`
| 项目 | 详情 |
|------|------|
| **功能** | 生成PM2.5排放KDE分布对比图 |
| **支持变量** | PM2.5 |
| **输出示例** | `PM2.5_2000vs2023_01.png` |
| **单位** | g/s |
| **特点** | 使用98.5%分位数截断极端值 |

### ⚙️ 数据提取脚本

**功能**: 从原始数据文件中提取和处理大气环境数据，生成标准化的CSV格式文件

#### 🔄 `extract_EmssionAndMcip_devinform_O3MDA8.py`
| 项目 | 详情 |
|------|------|
| **功能** | 综合数据提取脚本，从CMAQ Daily COMBINE ACONC文件提取污染物和气象数据 |
| **输入文件** | Daily_COMBINE_ACONC_v54_D3_*.nc (CMAQ模型输出) |
| **提取变量** | 污染物: O3_MDA8_CN, PM25_TOT<br>气象: SFC_TMP, SOL_RAD, PBLH |
| **输出文件** | `{年份}_Emission[{年份}met]_{月份}.csv`<br>`{年份}_mcipout_{月份}.csv` |
| **超标统计** | O3: >160 μg/m³, PM2.5: >75 μg/m³ |
| **区域过滤** | 支持惠州区域过滤（非惠州网格设为NaN） |
| **特点** | 同时生成全省和惠州版本，自动计算月均值和超标天数 |

#### 🌡️ `extract_Mcip_jform_2000_24h_NextDay.py`
| 项目 | 详情 |
|------|------|
| **功能** | 从MCIP METCRO2D/3D文件提取气象数据，处理时区和重复时间 |
| **输入文件** | METCRO2D_YYYYDDD.nc, METCRO3D_YYYYDDD.nc |
| **提取变量** | TEMP2 (2m温度), RGRND (太阳辐射), PBL (边界层高度) |
| **输出文件** | `{年份}_mcipout_{月份}_Comparison_NextDay.csv` |
| **时间处理** | UTC转北京时间，处理24:00时间点，去除重复时间 |
| **统计计算** | TA_mean/max, SOL_RAD_mean/max, PBLH_mean/max |
| **温度转换** | 自动从K转换为°C |
| **特点** | 跨年数据处理，自动时区转换，日平均值计算 |

#### 💨 `process_GDEI_PM25_Auto.py`
| 项目 | 详情 |
|------|------|
| **功能** | 自动检测和处理GD排放清单中的PM2.5数据，基于时间模式计算月平均值 |
| **输入文件** | EM_AV_YYYYDDD.nc (GD排放清单文件) |
| **数据目录** | `/data/workspace/GuangDong/emissionlist/GD2060/` |
| **PM2.5物种** | PEC, POC, PNO3, PSO4, PCL, PNH4, PNA, PMG, PK, PCA, PNCOM, PFE, PAL, PSI, PTI, PMN, PH2O, PMOTHR |
| **选择策略** | 自动选择目标月份的第一个周五、周六、周日文件 |
| **时间模式** | 区分工作日、周六、周日的排放特征 |
| **输出文件** | `EM_{年份}{月份}_PM2.5.csv`, `EM_{年份}{月份}_PM2.5.nc` |
| **计算方法** | 基于样本日计算月均值，加权平均不同日期类型 |
| **单位** | g/s |
| **特点** | 自动化文件识别，多物种PM2.5合并，缺失值处理，统计验证 |

---

## 2. 数据文件结构

### 2.1 cmaqout_processed/ 文件夹
- **文件格式**: `{年份}_Emission[{年份}met]_{月份}.csv`
- **示例**: `2000_Emission[2000met]_01.csv`
- **内容**: CMAQ模型输出数据，包含O3、PM2.5等浓度和超标天数
- **关键列**: ROW, COL, O3, PM2.5, O3_Days, PM2.5_Days

### 2.2 cmaqout_processed_HuiZhou/ 文件夹
- **文件格式**: `{年份}_Emission[{年份}met]_{月份}_HuiZhou.csv`
- **示例**: `2000_Emission[2000met]_01_HuiZhou.csv`
- **内容**: 惠州地区的CMAQ模型输出数据
- **特点**: 文件名末尾添加`_HuiZhou`后缀

### 2.3 mcipout_processed/ 文件夹
- **文件格式**: `{年份}_mcipout_{月份}.csv`
- **示例**: `2000_mcipout_07.csv`
- **内容**: MCIP气象预处理数据
- **关键列**: ROW, COL, TA_mean, TA_max, SOL_RAD_mean, SOL_RAD_max, PBLH_mean, PBLH_max

### 2.4 mcipout_processed_HuiZhou/ 文件夹
- **文件格式**: `{年份}_mcipout_{月份}_HuiZhou.csv`
- **示例**: `2000_mcipout_01_HuiZhou.csv`
- **内容**: 惠州地区的MCIP气象数据
- **特点**: 文件名末尾添加`_HuiZhou`后缀

### 2.5 emissionlist/ 文件夹
- **文件格式**: `EM_{年份}{月份}_PM2.5.csv`
- **示例**: `EM_200001_PM2.5.csv`
- **内容**: PM2.5排放源数据
- **关键列**: ROW, COL, PM2.5

### 2.6 emissionlist_HuiZhou/ 文件夹
- **文件格式**: `EM_{年份}{月份}_PM2.5_HuiZhou.csv`
- **示例**: `EM_200001_PM2.5_HuiZhou.csv`
- **内容**: 惠州地区PM2.5排放源数据
- **特点**: 文件名末尾添加`_HuiZhou`后缀

---

## 3. 文件命名规范

### 3.1 年份标识
- **2000**: 2000年基准数据
- **2023**: 2023年基准数据
- **2030**: 2030年预测数据
- **2060**: 2060年预测数据

### 3.2 月份标识
- **01**: 1月（January）
- **07**: 7月（July）

### 3.3 地区标识
- **无后缀**: 广东省全域
- **_HuiZhou**: 惠州地区

### 3.4 数据类型标识
- **Emission[YYYYmet]**: 使用YYYY年气象的排放清单
- **mcipout**: MCIP气象输出数据
- **EM**: 排放源数据

---

## 4. 输出结果

### 4.1 差值地图输出
- **CMAQ对比**: `Emission_Comparison_Plots/`
- **气象对比**: `Mcip_Comparison_Plots/`
- **排放对比**: `PeopleEmission_Plots/`

### 4.2 空间分布图输出
- **按年份分目录**: `年份/变量月份.png`
- **示例**: `2023/O3_01.png`

### 4.3 PDF分布图输出
- **CMAQ PDF**: `Emission_Comparison_Plots_PDF/`
- **气象 PDF**: `Mcip_Comparison_Plots_PDF/`
- **排放 PDF**: `PeopleEmission_Plots_PDF/`

---

## 5. 关键技术特性

### 5.1 图例处理
- **统一图例**: 所有年份使用相同色标范围
- **分开图例**: 每个文件独立计算最优色标范围
- **自动计算**: 基于分位数自动排除极端值

### 5.2 地图投影
- **模型文件**: `GRIDCRO2D_2000121_GuangDongD3`
- **边界文件**: `china_cities.json`
- **投影系统**: WRF模型投影

### 5.3 数据质量控制
- **网格匹配**: 严格验证数据长度与模型网格匹配
- **缺失值处理**: 自动跳过全缺失值的变量
- **范围检查**: 对异常值进行范围限制

---

## 6. 使用建议

1. **运行顺序**: 先运行单独绘制脚本生成基础图表，再运行差异对比脚本进行对比分析
2. **参数调整**: 根据具体需求修改脚本中的年份、月份、变量列表配置
3. **输出管理**: 建议定期清理输出目录，避免文件过多
4. **资源监控**: 大批量处理时注意内存和磁盘空间使用情况

---

*本文档最后更新时间: 2025年11月26日*
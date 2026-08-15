# GuangDong WRF-CMAQ 项目

广东省 WRF-CMAQ 空气质量多尺度模拟与评估的可视化 / 数据提取脚本库。

## 项目定位

对 CMAQ 输出（`cmaqout_processed/`）、MCIP 气象预处理（`mcipout_processed/`）、
排放清单（`emissionlist/`）进行差异对比、空间分布图、概率密度分布图的绘制与数据提取。
核心代码已重构到顶层 `Core_*.py`，历史脚本保留在 `Other/legacy_scripts/`。

## 运行环境

- Python 3.9+
- 依赖见 `requirements.txt`（`pip install -r requirements.txt`）

## 数据目录

数据默认位于 `/data/workspace/GuangDong`（HPC 路径）。本仓库**不包含**数据文件，
克隆后需自行准备以下目录结构（详见 `GuangDong_November_CodeAndDataExplanation.md`）：

```
Data/
├── cmaqout_processed/        # CMAQ 输出：{year}_Emission[{year}met]_{month}.csv
├── mcipout_processed/        # MCIP 气象：{year}_mcipout_{month}.csv
├── emissionlist/             # 排放清单：EM_{year}{month}_PM2.5.csv
└── Station/                  # 站点数据
```

运行前请把 `Core_*.py` 中的路径指向你本机的数据位置。

## 脚本说明

| 前缀 | 用途 |
|---|---|
| `Core_Map*.py` | 差值 / 单独空间分布图 |
| `Core_Extract*.py` | 数据提取 |
| `Core_PDF*.py` | 概率密度分布图 |
| `Core_Charts*.py` | 柱状图 |
| `Core_Validation*.py` | 站点 / 气象校验 |

历史一次性脚本在 `Other/legacy_scripts/`，不建议直接复用。

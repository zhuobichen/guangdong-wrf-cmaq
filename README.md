# Guangdong WRF-CMAQ

> 广东省空气质量多尺度模拟与评估 — CMAQ/WRF 建模、排放处理、气象-化学校验

## 项目定位

以广东省（含珠三角、惠州）为研究区域，进行三层嵌套网格（D1 27km / D2 9km / D3 3km）的 WRF-CMAQ 空气质量模拟。涵盖气象驱动、排放处理、模型运行、校验全流程，含排放情景对比和热浪分析专项。

## 关键技术

| 技术 | 用途 |
|------|------|
| WRF v3.9.1+ | 气象场模拟 |
| CMAQ v5.3 / v5.4 | 空气质量模拟（O3/PM2.5/NO2） |
| MEGAN v3.2 | 生物源排放 |
| MCIP | 气象-化学接口处理 |
| MEIC / EDGAR | 人为排放清单 |

## 目录结构

```
GuangDong/
├── Core_Extract.py       — CMAQ/WRF/MCIP 数据提取核心
├── Core_Map.py           — 空间地图绘制
├── Core_Charts.py        — 统计图表（箱线图/柱状图）
├── Core_Mask.py          — 区域掩膜处理
├── Core_PDF.py           — PDF 分布图
├── Run_Extract.py        — 数据提取入口
├── Run_Mask.py           — 掩膜处理入口
│
├── Data/                 ← 输入数据（CMAQ/WRF/监测）
├── cmaqout_processed/    ← CMAQ 后处理结果
├── mcipout_processed/    ← MCIP 处理结果
├── emissionlist/         ← 排放清单
├── 气象站点/             ← 气象站点校验
├── 臭氧颗粒物站点校验/   ← O3/PM 站点校验
├── cmaq_项目提交/        ← 项目交付材料
│
├── CLAUDE.md             ← AI 助手项目上下文
└── 1_codenotuse/         ← 废弃旧代码（归档）
```

## 研究区域

| 域 | 分辨率 | 范围 |
|----|--------|------|
| D1 (d01) | 27 km | 中国东部 |
| D2 (d02) | 9 km | 广东省 |
| D3 (d03) | 3 km | 珠三角 / 惠州 |

## 文档

- `CLAUDE.md` — AI 助手上下文
- `GuangDong_November_CodeAndDataExplanation.md` — 代码与数据说明
- `docs/GuangDong项目架构规范_Core+Run分层设计.md` — 架构规范
- `气象站点/完整工作流程文档.md` — 气象校验全流程

## 快速开始

```bash
python Run_Extract.py    # CMAQ 数据提取
python Run_Mask.py       # 区域掩膜处理
```

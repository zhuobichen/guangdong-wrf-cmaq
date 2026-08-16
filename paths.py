#!/usr/bin/env python3
"""paths.py — 项目数据路径集中配置。

所有数据路径统一通过 DATA_ROOT / data_path() 获取，
部署时可用环境变量覆盖，无需修改代码。
"""

import os

# 项目数据根目录。默认保留原硬编码路径，可用环境变量覆盖：
#   GUANGDONG_DATA_ROOT=/your/data/root
DATA_ROOT = os.environ.get("GUANGDONG_DATA_ROOT", "/data/workspace/GuangDong")

# 行政边界 GeoJSON（来自 DataFusion_China 外部数据）。
# 默认保留原硬编码路径，可用环境变量覆盖：
#   GUANGDONG_BOUNDARY_JSON=/your/boundary/china_cities.json
BOUNDARY_JSON = os.environ.get(
    "GUANGDONG_BOUNDARY_JSON",
    "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json",
)


def data_path(*parts):
    """拼接 DATA_ROOT 与相对路径片段，返回完整路径。"""
    return os.path.join(DATA_ROOT, *parts)

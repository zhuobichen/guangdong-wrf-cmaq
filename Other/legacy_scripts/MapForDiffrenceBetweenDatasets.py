#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from esil.rsm_helper.model_property import model_attribute
from esil.map_helper import get_multiple_data, show_maps
import cmaps

# 基础配置
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
cmap_delta = cmaps.ViBlGrWhYeOrRe  # 差值图颜色映射

def get_dataset_label(variable):
    """简化的数据集标签获取"""
    label_map = {
        'PM25': 'PM2.5'
    }
    return label_map.get(variable, variable)

def plot_pm25_diff_map(data_2000, data_2023, model_file, save_path, boundary_json_file):
    """
    绘制2000-2023 PM2.5差值地图
    """
    # 加载模型投影信息
    mp = model_attribute(model_file)
    proj, longitudes, latitudes = mp.projection, mp.lons, mp.lats
    grid_shape = longitudes.shape

    # 假设数据中PM2.5的列名为'PM25'，若实际列名不同需修改此处
    pm_col = 'PM25'
    if pm_col not in data_2000.columns or pm_col not in data_2023.columns:
        raise ValueError(f"数据中缺少{pm_col}列，请检查数据格式")

    # 确保数据长度匹配网格尺寸
    if len(data_2000) != grid_shape[0] * grid_shape[1] or len(data_2023) != grid_shape[0] * grid_shape[1]:
        raise ValueError("数据长度与网格尺寸不匹配，请检查输入数据")

    # 重塑数据并计算差值（2023 - 2000）
    pm_2000 = data_2000[pm_col].values.reshape(grid_shape)
    pm_2023 = data_2023[pm_col].values.reshape(grid_shape)
    pm_diff = pm_2000 - pm_2023

    # 准备绘图数据
    plot_data = {}
    get_multiple_data(
        plot_data,
        dataset_name="PM2.5 (January Mean): 2000-2023",
        variable_name="",
        grid_x=longitudes,
        grid_y=latitudes,
        grid_concentration=pm_diff,
        is_delta=True,
        cmap=cmap_delta
    )

    # 绘图配置
    plot_settings = {
        'unit': "μg/m³",  # PM2.5常用单位
        'cmap': cmap_delta,
        'show_lonlat': True,
        'projection': proj,
        'is_wrf_out_data': True,
        'boundary_file': boundary_json_file,
        'show_original_grid': True,
        'delta_map_settings': {
            "cmap": cmap_delta,
            # "value_range": (None, None),  # 根据PM2.5差值合理设置范围，可按需调整
            "value_range": (-25, 25),  # 根据PM2.5差值合理设置范围，可按需调整
            "colorbar_ticks_value_format": ".1f",
            "value_format": ".1f"
        },
        'title_fontsize': 12,
        'xy_title_fontsize': 10,
        'show_dependenct_colorbar': True,
        'show_domain_mean': True
    }

    # 绘制并保存图像
    try:
        fig = show_maps(
            plot_data,
            unit=plot_settings['unit'],
            cmap=plot_settings['cmap'],
            show_lonlat=plot_settings['show_lonlat'],
            projection=plot_settings['projection'],
            is_wrf_out_data=plot_settings['is_wrf_out_data'],
            boundary_file=plot_settings['boundary_file'],
            show_original_grid=plot_settings['show_original_grid'],
            delta_map_settings=plot_settings['delta_map_settings'],
            title_fontsize=plot_settings['title_fontsize'],
            xy_title_fontsize=plot_settings['xy_title_fontsize'],
            show_dependenct_colorbar=plot_settings['show_dependenct_colorbar'],
            show_domain_mean=plot_settings['show_domain_mean']
        )

        # 确保保存目录存在
        os.makedirs(save_path, exist_ok=True)
        save_file = os.path.join(save_path, "PM25_2000_minus_2023_January.png")
        fig.savefig(save_file, dpi=300, bbox_inches="tight")
        print(f"图像已保存至: {save_file}")
        plt.close(fig)
    except Exception as e:
        print(f"绘图时出错: {str(e)}")
        raise

if __name__ == "__main__":
    # 核心输入参数 - 直接指定两个数据文件路径
    file_2000 = "/data/workspace/GuangDong/cmaqout_processed/2000_PM25-01-avg_with_row_col.csv"
    file_2023 = "/data/workspace/GuangDong/cmaqout_processed/2023_PM25-01-avg_with_row_col.csv"
    
    # 模型文件路径（请根据实际情况确认是否需要修改）
    model_file = r"/data/workspace/GuangDong/GRIDCRO2D_2000121_GuangDongD3"
    
    # 边界文件路径（若绘制广东地图，建议替换为广东的边界JSON文件，此处先用原有路径占位）
    # boundary_file = "/data/workspace/GuangDong/china.json"
    boundary_file = "/data/workspace/DataFusion_China/China_Data/RegionAndPopulation_Data/Chinajson/china_cities.json"  # 边界文件
    
    # 图像保存路径
    save_dir = "/data/workspace/GuangDong/PM25_Comparison_Plots"

    # 读取数据
    try:
        data_2000 = pd.read_csv(file_2000)
        data_2023 = pd.read_csv(file_2023)
        print("数据读取成功")
    except Exception as e:
        print(f"读取数据失败: {str(e)}")

    # 绘制差值地图
    plot_pm25_diff_map(data_2000, data_2023, model_file, save_dir, boundary_file)
    print("绘图完成！")
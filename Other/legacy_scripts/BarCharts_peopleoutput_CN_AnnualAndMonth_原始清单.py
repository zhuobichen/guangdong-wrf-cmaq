#!/usr/bin/env python
# coding: utf-8

import os
import sys
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'SimHei', 'DejaVu Sans']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['font.family'] = 'sans-serif'

# 确保所有元素都使用中文字体
plt.rcParams['font.size'] = 14
plt.rcParams['axes.titlesize'] = 20
plt.rcParams['axes.labelsize'] = 16
 


# -------------------------- 辅助函数 --------------------------
def get_month_name_cn(month_str):
    """将月份数字转换为中文月份名称"""
    month_names_cn = {
        '01': '1月', '02': '2月', '03': '3月', '04': '4月',
        '05': '5月', '06': '6月', '07': '7月', '08': '8月',
        '09': '9月', '10': '10月', '11': '11月', '12': '12月'
    }
    return month_names_cn.get(month_str, f'{month_str}月')


def get_variable_unit(variable):
    """获取变量对应的单位（当前输入为吨，这里统一以千吨显示）"""
    return '千吨'


def get_variable_display_name(variable):
    """获取变量在图中显示的名称（如 VOCs 统一显示为 VOC）。"""
    if variable.upper() in ['VOC', 'VOCs']:
        return 'VOCs'
    return variable


def load_allocated_csv(csv_path):
    """读取按比例分配后的千吨排放量CSV，结构：
    返回：
        data[污染物][年份][月份] = 排放量（千吨）
        has_month_data: 布尔值，是否包含1月/7月等月度数据（非全年）
    月份包含："1月"、"7月"、"全年"
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"未找到CSV文件：{csv_path}")
    df = pd.read_csv(csv_path)
    required_cols = {'年份', '月份', '污染物', '排放量'}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError(f"CSV缺少必要列：{required_cols}，实际列：{df.columns.tolist()}")
    
    data = {}
    # 记录是否有月度数据（排除"全年"）
    has_month_data = False
    # 收集所有出现的月份值，用于判断
    month_values = set()
    
    for _, row in df.iterrows():
        year = int(row['年份'])
        month = str(row['月份'])
        pol = str(row['污染物'])
        val = float(row['排放量'])
        
        month_values.add(month)
        data.setdefault(pol, {}).setdefault(year, {})[month] = val
    
    # 判断是否有月度数据：如果存在非"全年"的月份（如1月、7月、01、07等），则视为有月度数据
    non_annual_months = [m for m in month_values if m != '全年']
    has_month_data = len(non_annual_months) > 0
    
    return data, has_month_data


# -------------------------- 绘图函数 --------------------------
def plot_monthly_comparison_from_csv(data_by_pol, target_years, save_path):
    """绘制月度对比图：1月与7月，数据来自分配后千吨CSV。"""
    variables = ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC']
    years = [int(y) for y in target_years]
    months = ['1月', '7月']
    colors = ['#1f77b4', '#ff7f0e']

    os.makedirs(save_path, exist_ok=True)
    unit = get_variable_unit('PM2.5')

    for var in variables:
        fig, ax = plt.subplots(figsize=(11, 7))
        display_var = get_variable_display_name(var)

        x_positions = []
        bar_heights = []
        bar_colors = []

        n_years = len(years)
        group_spacing = 1.5

        for m_idx, month in enumerate(months):
            group_start = m_idx * group_spacing
            for y_idx, year in enumerate(years):
                x = group_start + y_idx * 0.5
                x_positions.append(x)
                val = data_by_pol.get(var, {}).get(year, {}).get(month, 0.0)
                bar_heights.append(val)
                bar_colors.append(colors[y_idx])

        bar_width = 0.45
        bars = ax.bar(x_positions, bar_heights, width=bar_width, color=bar_colors)

        group_centers = []
        for m_idx in range(len(months)):
            group_start = m_idx * group_spacing
            center = group_start + (n_years - 1) * 0.5 / 2.0
            group_centers.append(center)
        ax.set_xticks(group_centers)
        ax.set_xticklabels(months, fontsize=15)
        ax.tick_params(axis='y', labelsize=15)
        ax.tick_params(axis='x', labelsize=15)

        ax.set_title(f'CMAQ模拟区域{display_var}排放量', fontsize=20, fontweight='bold')
        ax.set_ylabel(f'排放量 ({unit})', fontsize=18)

        current_ylim = ax.get_ylim()
        ax.set_ylim(current_ylim[0], current_ylim[1] * 1.15)

        for bar, val in zip(bars, bar_heights):
            height = bar.get_height()
            if height > 0:
                label = f'{val:.2f}'
                ax.annotate(label,
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 4),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=15, fontweight='bold')

        plt.tight_layout()
        save_file = os.path.join(save_path, f'Monthly_Comparison_{var}.png')
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"✅ {display_var} 月度对比图已保存：{save_file}")


def plot_annual_comparison_from_csv(data_by_pol, target_years, save_path):
    """绘制年度对比图：每个污染物单独一张图（数据来自CSV的“全年”）。"""
    variables = ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC']
    years = [int(y) for y in target_years]
    
    # 颜色配置：2000(黄), 2023(绿), 2030(蓝), 2060(青/蓝绿)
    # 参考颜色值：#FFC000 (Yellow), #1E8449 (Green), #2E86C1 (Blue), #17A589 (Cyan)
    colors = ['#FFC000', '#1E8449', '#1f77b4', '#17becf']
    
    # 如果年份数量超过预设颜色数量，扩展颜色列表
    if len(years) > len(colors):
        # 使用 matplotlib 的 colormap 补充颜色
        import matplotlib.cm as cm
        cmap = cm.get_cmap('tab10')
        extra_colors = [cmap(i) for i in range(len(years) - len(colors))]
        colors.extend(extra_colors)

    os.makedirs(save_path, exist_ok=True)
    unit = get_variable_unit('PM2.5')

    for var in variables:
        fig, ax = plt.subplots(figsize=(10, 6))  # 调整画布大小，参考图比较宽
        display_var = get_variable_display_name(var)

        x_positions = list(range(len(years)))
        bar_heights = [data_by_pol.get(var, {}).get(y, {}).get('全年', 0.0) for y in years]

        bar_width = 0.55
        # 确保颜色列表长度与条形数量一致
        current_colors = colors[:len(years)]
        bars = ax.bar(x_positions, bar_heights, width=bar_width, color=current_colors)

        ax.set_xticks(x_positions)
        ax.set_xticklabels([f'{y}年' for y in years], fontsize=15)
        ax.tick_params(axis='y', labelsize=15)
        
        # 设置标题和标签
        ax.set_title(f'CMAQ模拟区域{display_var}排放量', fontsize=20, fontweight='bold')
        ax.set_ylabel(f'年度排放量 ({unit})', fontsize=16, fontweight='bold') # 加粗

        # 设置Y轴上限，留出空间给标签
        current_ylim = ax.get_ylim()
        ax.set_ylim(current_ylim[0], current_ylim[1] * 1.2) # 稍微增加顶部空间

        # 添加数值标签
        for bar, val in zip(bars, bar_heights):
            height = bar.get_height()
            if height > 0:
                label = f'{val:.2f}'
                ax.annotate(label,
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 5),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=14, fontweight='bold')

        plt.tight_layout()
        save_file = os.path.join(save_path, f'Annual_Comparison_{var}.png')
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"✅ {display_var} 年度对比图已保存：{save_file}")


 


# -------------------------- 主函数 --------------------------
def main():
    print("="*70)
    print("    开始绘制广东原始清单排放量对比柱形图    ")
    print("="*70)

    # 核心配置（内定指定年份和月份）
    # 关注 2000, 2023, 2030, 2060 年
    TARGET_YEARS = [2000, 2023, 2030, 2060]
    TARGET_MONTHS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    
    # 路径配置
    GD_DATA_DIR = "/data/workspace/GuangDong/emissionlist"        # 广东数据目录
    SAVE_PATH = "/data/workspace/GuangDong/Emission_Comparison_BoxPlots"  # 结果保存路径
    CSV_PATH = os.path.join(GD_DATA_DIR, "GuangDong_2000_2023_2030_2060_原始清单排放量千吨_年度.csv")

    # 加载分配后千吨数据（新增返回是否有月度数据）
    print(f"\n1. 加载CSV数据：{CSV_PATH}")
    data_by_pol, has_month_data = load_allocated_csv(CSV_PATH)

    # 绘制月度对比图（1月、7月）- 仅当有月度数据时绘制
    if has_month_data:
        print("\n2. 绘制月度对比图（1月、7月）...")
        plot_monthly_comparison_from_csv(data_by_pol, TARGET_YEARS, SAVE_PATH)
    else:
        print("\n⚠️  未检测到月度数据（仅包含全年数据），跳过月度对比图绘制")
    
    # 绘制年度对比图（全年）- 始终绘制
    print("\n3. 绘制年度对比图（全年）...")
    plot_annual_comparison_from_csv(data_by_pol, TARGET_YEARS, SAVE_PATH)

    print(f"\n✅ 所有对比图绘制完成！结果已保存至：{SAVE_PATH}")


if __name__ == "__main__":
    main()
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
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12


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
        return 'VOC'
    return variable


def aggregate_monthly_to_yearly(emission_data, target_years, target_months):
    """
    将月份数据加总为年度数据
    输入格式：{变量名: {"2000-01": 总排放量, "2000-02": 总排放量, ...}}
    输出格式：{变量名: {"2000": 年度总排放量, "2023": 年度总排放量, ...}}
    """
    yearly_data = {}
    variables = ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC']

    for var in variables:
        if var in emission_data:
            yearly_data[var] = {}
            for year in target_years:
                yearly_sum = 0
                available_months = 0

                # 加总该年份的所有月份数据
                for month in target_months:
                    year_month = f"{year}-{month}"
                    if year_month in emission_data[var]:
                        yearly_sum += emission_data[var][year_month]
                        available_months += 1

                # 只有当数据存在时才添加
                if available_months > 0:
                    yearly_data[var][str(year)] = yearly_sum
                    print(f"  {var} {year}年：{available_months}个月数据，年度总和：{yearly_sum:.3f}")
                else:
                    print(f"  警告：{var} {year}年无有效数据")

    return yearly_data


def load_emission_data(root_dir, region_name, target_years, target_months):
    """
    加载指定年月的排放数据（多变量文件格式）
    返回格式：{变量名: {"2000-01": 总排放量, "2000-07": 总排放量, ...}}
    """
    emission_data = {}
    variables = ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC']

    # 遍历指定的年份和月份
    for year in target_years:
        for month in target_months:
            year_month = f"{year}-{month}"
            # 构造文件名
            if region_name == "GuangDong":
                filename = f"EM_{year}{month}_ALL_OnlyGuangDong.csv"
            elif region_name == "HuiZhou":
                filename = f"EM_{year}{month}_ALL_HuiZhou.csv"
            else:
                continue

            file_path = os.path.join(root_dir, filename)
            if not os.path.exists(file_path):
                print(f"警告：{region_name} {year}年{month}月文件不存在 ({file_path})，跳过")
                continue

            try:
                df = pd.read_csv(file_path)
                # 计算每个变量的总排放量
                for var in variables:
                    # VOC 特殊处理：如果列名是 VOCs，也视为 VOC
                    col_name = var
                    if var == 'VOC' and 'VOC' not in df.columns:
                        if 'VOCs' in df.columns:
                            col_name = 'VOCs'

                    if col_name in df.columns:
                        total_emission = df[col_name].sum()
                        if var not in emission_data:
                            emission_data[var] = {}
                        emission_data[var][year_month] = total_emission
                    else:
                        print(f"警告：{file_path} 缺少 {var} 列，跳过该变量")

            except Exception as e:
                print(f"读取文件 {file_path} 失败：{str(e)}，跳过")
                continue

    return emission_data




def plot_monthly_comparison(guangdong_emission_data, target_years, save_path):
    """绘制月度对比图：每个污染物单独一张图
    
    每张图显示：1月、7月的数据（每个月份2000年、2023年并排）
    """
    variables = ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC']
    years = [str(y) for y in target_years]
    months = ['01', '07']  # 只使用1月和7月
    month_labels = {'01': '1月', '07': '7月'}
    colors = ['#1f77b4', '#ff7f0e']  # 2000、2023
    
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    unit = get_variable_unit('PM2.5')
    
    # 为每个污染物单独绘制一张图
    for var in variables:
        fig, ax = plt.subplots(figsize=(10, 6))
        display_var = get_variable_display_name(var)
        
        # 准备数据：每个月份2个年份并排
        x_positions = []
        bar_heights = []
        bar_colors = []
        
        n_years = len(years)
        group_spacing = 1.5  # 每个月份间隔，缩小以让1月和7月靠近
        
        for m_idx, month in enumerate(months):
            group_start = m_idx * group_spacing
            for y_idx, year in enumerate(years):
                x = group_start + y_idx * 0.4
                x_positions.append(x)
                
                key = f"{year}-{month}"
                val = guangdong_emission_data.get(var, {}).get(key, 0.0)
                bar_heights.append(val / 1000.0)  # 转为千吨
                bar_colors.append(colors[y_idx])
        
        # 绘制柱形图
        bar_width = 0.35
        bars = ax.bar(x_positions, bar_heights, width=bar_width, color=bar_colors)
        
        # 设置 x 轴刻度（每个月份组的中心）
        group_centers = []
        for m_idx in range(len(months)):
            group_start = m_idx * group_spacing
            center = group_start + (n_years - 1) * 0.4 / 2.0
            group_centers.append(center)
        ax.set_xticks(group_centers)
        ax.set_xticklabels([month_labels[m] for m in months], fontsize=17)
        
        # 标题和标签
        ax.set_title(f'广东{display_var}排放量', fontsize=14, fontweight='bold')
        ax.set_ylabel(f'排放量 ({unit})', fontsize=17)
        
        # 调整y轴范围：往上拉10%
        current_ylim = ax.get_ylim()
        ax.set_ylim(current_ylim[0], current_ylim[1] * 1.1)
        
        # 添加网格
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        # 添加数值标签
        for bar, val in zip(bars, bar_heights):
            height = bar.get_height()
            if height > 0:
                label = f'{val:.2f}'
                ax.annotate(label,
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=8, rotation=0)
        
        # 添加图例（移到x轴下方，横向排列，无边框，拉长颜色块）
        legend_handles = [
            plt.Rectangle((0, 0), 1, 1, color=colors[i], label=years[i])
            for i in range(n_years)
        ]
        legend = ax.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, -0.05), 
                          frameon=False, fontsize=12, ncol=n_years, handlelength=3, columnspacing=2)
        
        plt.tight_layout()
        save_file = os.path.join(save_path, f'Monthly_Comparison_{var}.png')
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        print(f"✅ {display_var} 月度对比图已保存：{save_file}")


def plot_annual_comparison(guangdong_yearly_data, target_years, save_path):
    """绘制年度对比图：每个污染物单独一张图
    
    每张图显示：2000年、2023年的全年数据对比
    """
    variables = ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC']
    years = [str(y) for y in target_years]
    colors = ['#1f77b4', '#ff7f0e']  # 2000、2023
    
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    unit = get_variable_unit('PM2.5')
    
    # 为每个污染物单独绘制一张图
    for var in variables:
        fig, ax = plt.subplots(figsize=(10, 6))
        display_var = get_variable_display_name(var)
        
        # 准备数据
        x_positions = list(range(len(years)))
        bar_heights = []
        
        for year in years:
            val = guangdong_yearly_data.get(var, {}).get(year, 0.0)
            bar_heights.append(val / 1000.0)  # 转为千吨
        
        # 绘制柱形图
        bar_width = 0.5
        bars = ax.bar(x_positions, bar_heights, width=bar_width, color=colors)
        
        # 设置 x 轴刻度：直接在每个柱子下方显示年份
        ax.set_xticks(x_positions)
        ax.set_xticklabels([f'{y}年' for y in years], fontsize=17)
        
        # 标题和标签
        ax.set_title(f'广东{display_var}排放量', fontsize=14, fontweight='bold')
        ax.set_ylabel(f'年度排放量 ({unit})', fontsize=17)
        
        # 调整y轴范围：往上拉10%
        current_ylim = ax.get_ylim()
        ax.set_ylim(current_ylim[0], current_ylim[1] * 1.1)
        
        # 添加网格
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        # 添加数值标签
        for bar, val in zip(bars, bar_heights):
            height = bar.get_height()
            if height > 0:
                label = f'{val:.2f}'
                ax.annotate(label,
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        save_file = os.path.join(save_path, f'Annual_Comparison_{var}.png')
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        print(f"✅ {display_var} 年度对比图已保存：{save_file}")


# -------------------------- 主函数 --------------------------
def main():
    print("="*70)
    print("    开始绘制广东和惠州排放量对比柱形图    ")
    print("="*70)

    # 核心配置（内定指定年份和月份）
    # 只关注 2000 和 2023 年；月份仍读取全年，用于计算“全年总量”
    TARGET_YEARS = [2000, 2023]
    TARGET_MONTHS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    
    # 路径配置
    GD_DATA_DIR = "/data/workspace/GuangDong/emissionlist"        # 广东数据目录
    SAVE_PATH = "/data/workspace/GuangDong/Emission_Comparison_BoxPlots"  # 结果保存路径

    # 加载数据
    print(f"\n1. 加载指定年月数据：{TARGET_YEARS}年 全年12个月份")
    print("   加载广东数据...")
    gd_emission_data = load_emission_data(GD_DATA_DIR, "GuangDong", TARGET_YEARS, TARGET_MONTHS)

    # 将月份数据聚合为年度数据
    print("\n2. 将月份数据加总为年度数据...")
    print("   广东数据聚合...")
    gd_yearly_data = aggregate_monthly_to_yearly(gd_emission_data, TARGET_YEARS, TARGET_MONTHS)

    # 绘制月度对比图（1张图，5个子图）
    print("\n3. 绘制月度对比图（1月、7月）...")
    plot_monthly_comparison(gd_emission_data, TARGET_YEARS, SAVE_PATH)
    
    # 绘制年度对比图（1张图，5个子图）
    print("\n4. 绘制年度对比图（全年）...")
    plot_annual_comparison(gd_yearly_data, TARGET_YEARS, SAVE_PATH)

    print(f"\n✅ 所有对比图绘制完成！结果已保存至：{SAVE_PATH}")


if __name__ == "__main__":
    main()
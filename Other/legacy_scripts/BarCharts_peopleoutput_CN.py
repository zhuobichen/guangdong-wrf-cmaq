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
    """获取变量对应的单位"""
    if variable == 'PM2.5':
        return 'g/s'
    elif variable in ['NOX', 'SO2', 'NH3', 'VOC']:
        return 'moles/s'
    else:
        return ''


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
                    if var in df.columns:
                        total_emission = df[var].sum()
                        if var not in emission_data:
                            emission_data[var] = {}
                        emission_data[var][year_month] = total_emission
                    else:
                        print(f"警告：{file_path} 缺少 {var} 列，跳过该变量")

            except Exception as e:
                print(f"读取文件 {file_path} 失败：{str(e)}，跳过")
                continue

    return emission_data




def plot_emission_comparison(guangdong_yearly_data, huizhou_yearly_data, target_years, save_path):
    """
    绘制排放量对比柱形图（横轴只有年份）
    """
    variables = ['PM2.5', 'NOX', 'SO2', 'NH3', 'VOC']
    colors = ['#1f77b4', '#ff7f0e']  # 广东：蓝色，惠州：橙色

    # 创建保存目录
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # 横轴标签为年份
    x_labels = [str(year) for year in target_years]

    # 遍历每个污染物绘制独立图表
    for var in variables:
        # 获取变量单位
        unit = get_variable_unit(var)

        # 提取年度排放量数据
        gd_values = []
        hz_values = []
        for year in x_labels:
            gd_values.append(guangdong_yearly_data.get(var, {}).get(year, 0))
            hz_values.append(huizhou_yearly_data.get(var, {}).get(year, 0))

        # 创建图表（根据数据量调整宽度）
        fig_width = max(8, len(x_labels) * 1.5)
        fig, ax = plt.subplots(figsize=(fig_width, 6))

        # 绘制柱形图
        bar_width = 0.35
        x = np.arange(len(x_labels))
        bars1 = ax.bar(x - bar_width/2, gd_values, bar_width, label='GuangDong', color=colors[0])
        bars2 = ax.bar(x + bar_width/2, hz_values, bar_width, label='HuiZhou', color=colors[1])

        # 设置标题和标签（包含单位）
        ax.set_title(f'广东和惠州 {var} 年度总排放量对比', fontsize=16)
        ax.set_xlabel('年份', fontsize=14)
        ax.set_ylabel(f'年度总排放量 ({unit})', fontsize=14)  # 添加单位标注
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=0, ha='center')  # 年份不需要旋转

        # 右上角图例
        ax.legend(loc='upper right', frameon=True)

        # 添加数值标签（保留三位小数）
        def add_value_labels(bars):
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    if unit == 'g/s':
                        # PM2.5保留三位小数（常规格式）
                        label = f'{height:.3f}'
                    else:
                        # 气体污染物使用科学计数法，保留三位小数
                        label = f'{height:.3f}'
                    ax.annotate(label,
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),
                                textcoords="offset points",
                                ha='center', va='bottom', fontsize=9)

        add_value_labels(bars1)
        add_value_labels(bars2)

        # 调整布局并保存
        plt.tight_layout()
        save_file = os.path.join(save_path, f'{var}_yearly_emission_comparison.png')
        plt.savefig(save_file, dpi=300, bbox_inches='tight')
        plt.close(fig)

        print(f"✅ {var} 年度对比图已保存：{save_file}")


# -------------------------- 主函数 --------------------------
def main():
    print("="*70)
    print("    开始绘制广东和惠州排放量对比柱形图    ")
    print("="*70)

    # 核心配置（内定指定年份和月份）
    TARGET_YEARS = [2000, 2023, 2030, 2060]  # 指定年份
    TARGET_MONTHS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]  # 全年12个月份
    
    # 路径配置
    GD_DATA_DIR = "/data/workspace/GuangDong/emissionlist"        # 广东数据目录
    HZ_DATA_DIR = "/data/workspace/GuangDong/emissionlist_HuiZhou" # 惠州数据目录
    SAVE_PATH = "/data/workspace/GuangDong/Emission_Comparison_BoxPlots"  # 结果保存路径

    # 加载数据
    print(f"\n1. 加载指定年月数据：{TARGET_YEARS}年 全年12个月份")
    print("   加载广东数据...")
    gd_emission_data = load_emission_data(GD_DATA_DIR, "GuangDong", TARGET_YEARS, TARGET_MONTHS)

    print("   加载惠州数据...")
    hz_emission_data = load_emission_data(HZ_DATA_DIR, "HuiZhou", TARGET_YEARS, TARGET_MONTHS)

    # 将月份数据聚合为年度数据
    print("\n2. 将月份数据加总为年度数据...")
    print("   广东数据聚合...")
    gd_yearly_data = aggregate_monthly_to_yearly(gd_emission_data, TARGET_YEARS, TARGET_MONTHS)

    print("   惠州数据聚合...")
    hz_yearly_data = aggregate_monthly_to_yearly(hz_emission_data, TARGET_YEARS, TARGET_MONTHS)

    # 绘制年度对比图
    print("\n3. 绘制年度柱形图...")
    plot_emission_comparison(gd_yearly_data, hz_yearly_data, TARGET_YEARS, SAVE_PATH)
    
    print(f"\n✅ 所有对比图绘制完成！结果已保存至：{SAVE_PATH}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查小时数据结构脚本
检查输入数据中每天是否有24小时还是25小时
"""
import netCDF4 as nc
import pandas as pd
import numpy as np
import datetime as dt
import re

def check_hour_structure():
    """检查小时数据结构"""

    # 测试文件路径
    test_file = "/data/workspace/GuangDong/cmaqout/COMBINE_ACONC_v54_D3_2000met_2023emis_GD_layer_1_2000-06-26_2000-07-31_18species.nc"

    print(f"检查文件: {test_file}")

    try:
        ds = nc.Dataset(test_file)

        # 读取时间变量
        if 'TSTEP' in ds.variables:
            time_var = ds.variables['TSTEP']
            print(f"时间变量名称: TSTEP")
        elif 'time' in ds.variables:
            time_var = ds.variables['time']
            print(f"时间变量名称: time")
        else:
            print("未找到时间变量，使用文件名推断")
            # 解析文件名中的日期
            filename = test_file.split('/')[-1]
            pattern = r'(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})'
            matches = re.findall(pattern, filename)
            if matches:
                start_year, start_month, start_day, end_year, end_month, end_day = matches[0]
                start_date = dt.datetime(int(start_year), int(start_month), int(start_day))
                end_date = dt.datetime(int(end_year), int(end_month), int(end_day))
                total_hours = int((end_date - start_date).total_seconds() // 3600)
                print(f"从文件名推断的总小时数: {total_hours}")
            else:
                print("无法解析文件日期")
                return

        # 读取温度数据来检查结构
        ta_data = ds.variables['SFC_TMP'][:, 0, :, :]  # 小时级温度数据
        n_t, n_row, n_col = ta_data.shape

        print(f"\n📊 数据基本信息:")
        print(f"总小时数: {n_t}")
        print(f"网格维度: {n_row} × {n_col}")

        # 检查每天的小时数
        print(f"\n🔍 检查每天的小时数结构:")

        # 如果有时间变量，使用时间变量
        if 'TSTEP' in ds.variables or 'time' in ds.variables:
            times = time_var[:]
            print(f"时间变量长度: {len(times)}")
            print(f"时间变量前10个值: {times[:10]}")
        else:
            # 使用文件名推断的时间
            filename = test_file.split('/')[-1]
            pattern = r'(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})'
            matches = re.findall(pattern, filename)
            if matches:
                start_year, start_month, start_day, end_year, end_month, end_day = matches[0]
                start_date = dt.datetime(int(start_year), int(start_month), int(start_day))

                print(f"开始日期: {start_date}")

                # 检查前10天的小时数
                for day_offset in range(min(10, n_t // 24)):
                    hour_start = day_offset * 24
                    hour_end = min((day_offset + 1) * 24, n_t)

                    actual_hours = hour_end - hour_start
                    current_date = start_date + dt.timedelta(days=day_offset)

                    print(f"  {current_date.strftime('%Y-%m-%d')}: {actual_hours}小时 (索引 {hour_start}-{hour_end-1})")

                    # 检查是否有25小时的情况
                    if actual_hours == 25:
                        print(f"    ⚠️  发现25小时的天数！")

        # 更详细地检查小时结构
        print(f"\n📈 详细小时分析:")

        # 方法1：按24小时分组检查
        expected_days = n_t // 24
        remaining_hours = n_t % 24

        print(f"预期完整天数: {expected_days}")
        print(f"剩余小时数: {remaining_hours}")

        if remaining_hours > 0:
            print(f"⚠️  数据不是完整的24小时倍数！")

        # 方法2：检查温度数据的连续性
        print(f"\n🔬 检查数据连续性:")

        # 选择一个网格检查温度变化
        test_r, test_c = 100, 100
        temp_series = ta_data[:, test_r, test_c]

        # 查找温度突变点（可能表示天边界）
        temp_changes = []
        for i in range(1, len(temp_series)):
            if abs(temp_series[i] - temp_series[i-1]) > 5:  # 温度变化大于5度
                temp_changes.append(i)

        print(f"温度突变点位置: {temp_changes[:10]}...")  # 只显示前10个

        # 分析每天的小时数模式
        print(f"\n🕐 分析每天实际小时数:")

        if 'TSTEP' in ds.variables or 'time' in ds.variables:
            # 如果有时间变量，分析时间模式
            hours_per_day = {}

            for i in range(min(240, n_t)):  # 检查前240小时（10天）
                day_idx = i // 24
                hour_in_day = i % 24

                if day_idx not in hours_per_day:
                    hours_per_day[day_idx] = 0
                hours_per_day[day_idx] += 1

            print("前10天的小时数分布:")
            for day_idx in sorted(hours_per_day.keys()):
                print(f"  第{day_idx+1}天: {hours_per_day[day_idx]}小时")

        ds.close()

        # 提供修改建议
        print(f"\n💡 修改建议:")
        if remaining_hours > 0:
            print(f"  发现数据不是24小时的完整倍数")
            print(f"  建议只使用前{expected_days * 24}个小时的数据")
            print(f"  即忽略最后{remaining_hours}个小时")
        else:
            print(f"  数据看起来是完整的24小时倍数")

    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_hour_structure()
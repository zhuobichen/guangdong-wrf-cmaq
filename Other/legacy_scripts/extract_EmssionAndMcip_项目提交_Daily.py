#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目提交数据提取脚本：
1. 从CMAQ Daily COMBINE ACONC文件中提取指定变量
2. 保持原始nc文件的属性和结构
3. 输出为nc文件格式，便于项目提交使用
4. 提取的变量包括：O3_MDA8、PM25_TOT、SFC_TMP、SOL_RAD、PBLH
"""

import netCDF4 as nc
import numpy as np
import os
import sys
import datetime as dt
import re


def parse_dates_from_filename(filename):
    """从 CMAQ 标准文件名里抠出起止日期"""
    pattern = r'(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})'
    matches = re.findall(pattern, filename)

    if matches:
        start_year, start_month, start_day, end_year, end_month, end_day = matches[0]
        start_date = dt.datetime(int(start_year), int(start_month), int(start_day))
        end_date = dt.datetime(int(end_year), int(end_month), int(end_day))
        return start_date, end_date
    else:
        raise ValueError(f"无法从文件名中解析日期: {filename}")


def extract_variables_to_nc(input_nc_file, output_nc_file, variables_to_extract):
    """
    从输入nc文件中提取指定变量并保存到输出nc文件
    
    Args:
        input_nc_file: 输入nc文件路径
        output_nc_file: 输出nc文件路径
        variables_to_extract: 需要提取的变量列表
    """
    print(f"开始从 {input_nc_file} 提取变量到 {output_nc_file}")
    
    # 打开输入文件
    input_ds = nc.Dataset(input_nc_file, 'r')
    
    # 创建输出文件
    output_ds = nc.Dataset(output_nc_file, 'w', format='NETCDF4')
    
    try:
        # 复制全局属性
        for attr_name in input_ds.ncattrs():
            output_ds.setncattr(attr_name, input_ds.getncattr(attr_name))
        
        # 复制维度
        for dim_name, dim in input_ds.dimensions.items():
            if dim.isunlimited():
                output_ds.createDimension(dim_name, None)  # unlimited dimension
            else:
                output_ds.createDimension(dim_name, len(dim))
        
        # 复制所有变量（包括坐标变量）
        for var_name, var in input_ds.variables.items():
            # 创建变量
            output_var = output_ds.createVariable(var_name, var.dtype, var.dimensions, 
                                                zlib=True, complevel=6)
            
            # 复制变量属性
            for attr_name in var.ncattrs():
                if attr_name != '_FillValue':  # 避免冲突
                    output_var.setncattr(attr_name, var.getncattr(attr_name))
            
            # 如果变量在需要提取的列表中或为坐标变量，则复制数据
            if var_name in variables_to_extract or is_coordinate_variable(var_name, input_ds):
                print(f"复制变量数据: {var_name}")
                output_var[:] = var[:]
            else:
                # 对于不需要的变量，只保留结构，数据用NaN填充
                print(f"保留变量结构（不复制数据）: {var_name}")
                
        print(f"✅ 变量提取完成: {output_nc_file}")
        
    except Exception as e:
        print(f"❌ 提取过程中出现错误: {str(e)}")
        raise
    finally:
        # 关闭文件
        input_ds.close()
        output_ds.close()


def is_coordinate_variable(var_name, dataset):
    """判断是否为坐标变量（维度坐标）"""
    # 检查变量名是否与维度名相同
    dimensions = dataset.dimensions.keys()
    if var_name in dimensions:
        return True
    
    # 检查是否为常见的坐标变量
    coordinate_vars = ['TSTEP', 'DATE-TIME', 'LAY', 'ROW', 'COL', 'VAR', 'DATE', 'TIME']
    return var_name in coordinate_vars


def calculate_variable_averages(input_nc_file, target_variables):
    """
    计算输入nc文件中指定变量的平均值
    """
    print(f"计算 {input_nc_file} 中变量的平均值...")
    
    ds = nc.Dataset(input_nc_file, 'r')
    averages = {}
    
    for var_name in target_variables:
        if var_name in ds.variables:
            var_data = ds.variables[var_name][:]
            # 计算平均值，忽略NaN值
            avg_value = np.nanmean(var_data)
            averages[var_name] = avg_value
            print(f"  {var_name}: {avg_value:.4f}")
        else:
            print(f"  {var_name}: 变量不存在")
            averages[var_name] = np.nan
    
    ds.close()
    return averages


def extract_specific_variables_to_new_nc(input_nc_file, output_nc_file, target_variables):
    """
    从输入nc文件中仅提取特定变量并创建新的nc文件
    
    Args:
        input_nc_file: 输入nc文件路径
        output_nc_file: 输出nc文件路径
        target_variables: 需要提取的目标变量列表
    """
    print(f"开始从 {input_nc_file} 提取特定变量到 {output_nc_file}")
    print(f"目标变量: {target_variables}")
    
    # 打开输入文件
    input_ds = nc.Dataset(input_nc_file, 'r')
    
    # 创建输出文件
    output_ds = nc.Dataset(output_nc_file, 'w', format='NETCDF4')
    
    try:
        # 复制全局属性
        for attr_name in input_ds.ncattrs():
            output_ds.setncattr(attr_name, input_ds.getncattr(attr_name))
        
        # 复制维度
        for dim_name, dim in input_ds.dimensions.items():
            if dim.isunlimited():
                output_ds.createDimension(dim_name, None)  # unlimited dimension
            else:
                output_ds.createDimension(dim_name, len(dim))
        
        # 首先复制所有维度坐标变量
        for var_name, var in input_ds.variables.items():
            # 如果是维度坐标变量，直接复制
            if is_coordinate_variable(var_name, input_ds):
                output_var = output_ds.createVariable(var_name, var.dtype, var.dimensions,
                                                    zlib=True, complevel=6)
                for attr_name in var.ncattrs():
                    output_var.setncattr(attr_name, var.getncattr(attr_name))
                output_var[:] = var[:]
                print(f"复制坐标变量: {var_name}")
        
        # 然后复制目标变量
        missing_vars = []
        for var_name in target_variables:
            if var_name in input_ds.variables:
                var = input_ds.variables[var_name]
                output_var = output_ds.createVariable(var_name, var.dtype, var.dimensions,
                                                    zlib=True, complevel=6)
                
                # 复制变量属性
                for attr_name in var.ncattrs():
                    output_var.setncattr(attr_name, var.getncattr(attr_name))
                
                # 复制变量数据
                output_var[:] = var[:]
                print(f"复制目标变量: {var_name}")
            else:
                missing_vars.append(var_name)
                print(f"⚠️ 目标变量不存在: {var_name}")
        
        if missing_vars:
            print(f"⚠️ 以下变量在输入文件中未找到: {missing_vars}")
        
        print(f"✅ 特定变量提取完成: {output_nc_file}")
        
    except Exception as e:
        print(f"❌ 提取过程中出现错误: {str(e)}")
        raise
    finally:
        # 关闭文件
        input_ds.close()
        output_ds.close()


def main():
    """主函数"""
    print("="*80)
    print("项目提交数据提取脚本")
    print("功能：从原始nc文件中提取指定变量，输出为nc格式")
    print("="*80)
    
    # 定义需要提取的变量
    target_variables = [
        'O3_MDA8',      # O3日最大8小时平均浓度
        'PM25_TOT',     # PM2.5总浓度
        'SFC_TMP',      # 地面温度
        'SOL_RAD',      # 太阳辐射
        'PBLH'          # 边界层高度
    ]
    
    # 示例文件配置 - 用户可以在这里添加更多文件配置
    # 从原始脚本中获取文件配置
    FILE_CONFIGS = [
        #Case2 2000e2023met
        {
            'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2023met_2000emis_GD_layer_1_2023-06-26_2023-07-31_18species.nc",
            'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case2_7月.nc"
        },
        {
            'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2023met_2000emis_GD_layer_1_2022-12-27_2023-01-31_18species.nc",
            'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case2_1月.nc"
        },
        #Case4 2023e2000m
        {
            'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2000met_2023emis_GD_layer_1_2000-06-26_2000-07-31_18species.nc",
            'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case4_7月.nc"
        },
        {
            'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_2000met_2023emis_GD_layer_1_1999-12-27_2000-01-31_18species.nc",
            'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case4_1月.nc"
        },

        #Case3 2023e2023m
        {
            'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2023_GD_layer_1_2023-06-26_2023-07-31_18species.nc",
            'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case3_7月.nc"
        },
        {
            'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2023_GD_layer_1_2022-12-27_2023-01-31_18species.nc",
            'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case3_1月.nc"
        },

        #Case1 2000e2000m
        {
            'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2000_GD_layer_1_2000-06-26_2000-07-31_18species.nc",
            'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case1_7月.nc"
        },
        {
            'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2000_GD_layer_1_1999-12-27_2000-01-31_18species.nc",
            'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case1_1月.nc"
        },
        #Case5 2060e2060m
        {
        'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2060_GD_layer_1_2060-06-26_2060-07-31_18species.nc",
        'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case5_7月.nc"
        },
        {
            'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2060_GD_layer_1_2059-12-27_2060-01-31_18species.nc",
            'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case5_1月.nc"
        },

        #Case6 2030e2030m
        {
        'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2030_GD_layer_1_2030-06-26_2030-07-31_18species.nc",
        'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case6_7月.nc"
        },
        {
        'input_nc_file': "/data/workspace/GuangDong/cmaqout/Daily_COMBINE_ACONC_v54_D3_ssp126_2030_GD_layer_1_2029-12-27_2030-01-31_18species.nc",
        'output_nc_file': "/data/workspace/GuangDong/cmaq_项目提交/extracted_Case6_1月.nc"
        },
    ]
    
    # 使用用户定义的配置
    file_configs = FILE_CONFIGS
    
    # 首先计算所有输入文件的变量平均值，用于检查
    print("\n" + "="*80)
    print("计算原始文件中变量的平均值（用于检查）")
    print("="*80)
    
    all_averages = []
    for i, config in enumerate(FILE_CONFIGS):
        input_file = config['input_nc_file']
        if not os.path.exists(input_file):
            print(f"⚠️ 输入文件不存在: {input_file}")
            continue
        
        print(f"\n处理第 {i+1}/{len(FILE_CONFIGS)} 个文件: {os.path.basename(input_file)}")
        averages = calculate_variable_averages(input_file, target_variables)
        
        # 提取Case和月份信息
        filename = os.path.basename(input_file)
        case_match = re.search(r'(Case\d+)', config['output_nc_file'])
        case_name = case_match.group(1) if case_match else 'Unknown'
        
        month_match = re.search(r'_(\d{2})月', config['output_nc_file']) or re.search(r'-(\d{2})-', filename)
        if month_match:
            month = month_match.group(1)
        else:
            # 从文件名中提取月份
            month = 'Unknown'
            if '07' in filename or '06' in filename or '07' in config['output_nc_file'] or '06' in config['output_nc_file']:
                month = '07'
            elif '01' in filename or '12' in filename or '01' in config['output_nc_file'] or '12' in config['output_nc_file']:
                month = '01'
        
        all_averages.append({
            'Case': case_name,
            'Month': month,
            'File': os.path.basename(input_file),
            **averages
        })
    
    # 创建汇总表格
    print("\n" + "="*80)
    print("原始文件变量平均值汇总表")
    print("="*80)
    
    # 打印表头
    print(f"{'Case':<8} {'Month':<6} {'O3_MDA8':<12} {'PM25_TOT':<12} {'SFC_TMP':<12} {'SOL_RAD':<12} {'PBLH':<12}")
    print("-"*80)
    
    # 打印每行数据
    for avg_data in all_averages:
        print(f"{avg_data['Case']:<8} {avg_data['Month']:<6} {avg_data['O3_MDA8']:<12.4f} {avg_data['PM25_TOT']:<12.4f} {avg_data['SFC_TMP']:<12.4f} {avg_data['SOL_RAD']:<12.4f} {avg_data['PBLH']:<12.4f}")
    
    print("\n开始提取变量到新的nc文件...")
    
    # 确保输出目录存在
    output_dir = "/data/workspace/GuangDong/cmaq_项目提交"
    os.makedirs(output_dir, exist_ok=True)
    
    # 处理每个文件配置
    for i, config in enumerate(file_configs):
        print(f"\n处理第 {i+1}/{len(file_configs)} 个文件...")
        
        input_file = config['input_nc_file']
        output_file = config['output_nc_file']
        
        # 检查输入文件是否存在
        if not os.path.exists(input_file):
            print(f"⚠️ 输入文件不存在: {input_file}")
            continue
        
        try:
            # 提取特定变量到新的nc文件
            extract_specific_variables_to_new_nc(input_file, output_file, target_variables)
        except Exception as e:
            print(f"❌ 处理文件时出现错误: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n{'='*80}")
    print("项目提交数据提取完成！")
    print(f"{'='*80}")


# --------------------------------------------------
# 命令行入口
# --------------------------------------------------
if __name__ == '__main__':
    main()
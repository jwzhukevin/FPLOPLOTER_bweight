#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPLO GUI性能测试工具
作者: zhujiawen@ustc.mail.edu.cn
"""

import time
import multiprocessing
import numpy as np
import matplotlib.pyplot as plt
from fplo_visualizer import FPLOVisualizer

def test_data_loading_performance(filename):
    """测试数据加载性能"""
    print("=== 数据加载性能测试 ===")
    
    start_time = time.time()
    
    # 测试不同的k点限制
    k_limits = [50, 100, 200, 414]  # 414是完整数据
    
    for k_limit in k_limits:
        print(f"\n测试k点限制: {k_limit}")
        
        load_start = time.time()
        visualizer = FPLOVisualizer(filename)
        visualizer.analyze_file_info()
        visualizer.parse_header_and_system()
        
        if k_limit < 414:
            visualizer.read_and_parse_data(max_kpoints=k_limit)
        else:
            visualizer.read_and_parse_data()
        
        load_time = time.time() - load_start
        
        print(f"  加载时间: {load_time:.2f}秒")
        print(f"  k点数: {visualizer.k_points.shape[0] if hasattr(visualizer, 'k_points') else 0}")
        print(f"  能带数: {visualizer.num_bands if hasattr(visualizer, 'num_bands') else 0}")
        print(f"  轨道数: {len(visualizer.orbital_info) if hasattr(visualizer, 'orbital_info') else 0}")
        
        # 估算内存使用
        if hasattr(visualizer, 'band_weights'):
            memory_mb = visualizer.band_weights.nbytes / 1024 / 1024
            print(f"  权重数据内存: {memory_mb:.1f}MB")

def test_multicore_performance():
    """测试多核处理性能"""
    print("\n=== 多核处理性能测试 ===")
    
    cpu_count = multiprocessing.cpu_count()
    print(f"检测到 {cpu_count} 个CPU核心")
    
    # 生成测试数据
    test_data_size = 1000
    test_data = []
    
    for i in range(test_data_size):
        k_points = np.random.random(100)
        energies = np.random.random(100) * 10 - 5
        weights = np.random.random(100)
        settings = {'weight_threshold': 0.02, 'max_points_per_orbital': 500}
        
        test_data.append((f"test_orbital_{i}", k_points, energies, weights, settings))
    
    # 测试单核处理
    print(f"\n单核处理 {test_data_size} 个轨道...")
    start_time = time.time()
    
    from fplo_gui_main import process_single_orbital
    single_results = [process_single_orbital(data) for data in test_data]
    
    single_time = time.time() - start_time
    print(f"单核处理时间: {single_time:.2f}秒")
    
    # 测试多核处理
    if cpu_count > 1:
        print(f"\n多核处理 {test_data_size} 个轨道 (使用{min(4, cpu_count)}核)...")
        start_time = time.time()
        
        try:
            from concurrent.futures import ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=min(4, cpu_count)) as executor:
                multi_results = list(executor.map(process_single_orbital, test_data))
            
            multi_time = time.time() - start_time
            print(f"多核处理时间: {multi_time:.2f}秒")
            print(f"性能提升: {single_time/multi_time:.1f}倍")
            
        except Exception as e:
            print(f"多核处理测试失败: {e}")

def test_interpolation_performance():
    """测试插值性能"""
    print("\n=== 插值性能测试 ===")
    
    # 生成测试数据
    k_points = np.linspace(0, 5, 100)
    energies = np.sin(k_points) * 2
    weights = np.random.random(100)
    
    density_factors = [1, 2, 5, 10, 15, 20]
    
    for density in density_factors:
        print(f"\n测试插值密度: {density}倍")
        
        start_time = time.time()
        
        try:
            from scipy.interpolate import interp1d
            
            # 生成密集点
            k_dense = np.linspace(k_points[0], k_points[-1], len(k_points) * density)
            
            # 线性插值
            f_energy = interp1d(k_points, energies, kind='linear')
            f_weight = interp1d(k_points, weights, kind='linear')
            
            e_dense = f_energy(k_dense)
            w_dense = f_weight(k_dense)
            
            interp_time = time.time() - start_time
            
            print(f"  插值时间: {interp_time*1000:.1f}毫秒")
            print(f"  原始点数: {len(k_points)}")
            print(f"  插值后点数: {len(k_dense)}")
            print(f"  数据增长: {len(k_dense)/len(k_points):.1f}倍")
            
        except Exception as e:
            print(f"  插值失败: {e}")

def test_plotting_performance():
    """测试绘图性能"""
    print("\n=== 绘图性能测试 ===")
    
    point_counts = [100, 500, 1000, 2000, 5000]
    
    for count in point_counts:
        print(f"\n测试绘制 {count} 个点...")
        
        # 生成测试数据
        x = np.random.random(count) * 10
        y = np.random.random(count) * 10 - 5
        sizes = np.random.random(count) * 50 + 10
        colors = np.random.random(count)
        
        start_time = time.time()
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(8, 6))
        scatter = ax.scatter(x, y, s=sizes, c=colors, alpha=0.7, edgecolors='none')
        
        plot_time = time.time() - start_time
        
        print(f"  绘图时间: {plot_time*1000:.1f}毫秒")
        print(f"  每点时间: {plot_time*1000/count:.3f}毫秒")
        
        plt.close(fig)

def generate_performance_report():
    """生成性能报告"""
    print("\n=== 系统性能报告 ===")
    
    import psutil
    
    # CPU信息
    cpu_count = multiprocessing.cpu_count()
    cpu_freq = psutil.cpu_freq()
    print(f"CPU核心数: {cpu_count}")
    if cpu_freq:
        print(f"CPU频率: {cpu_freq.current:.0f} MHz")
    
    # 内存信息
    memory = psutil.virtual_memory()
    print(f"总内存: {memory.total / 1024 / 1024 / 1024:.1f} GB")
    print(f"可用内存: {memory.available / 1024 / 1024 / 1024:.1f} GB")
    
    # 性能建议
    print("\n=== 性能建议 ===")
    
    if memory.total < 8 * 1024 * 1024 * 1024:  # 小于8GB
        print("• 内存较少，建议:")
        print("  - 最大点数/轨道: 300-500")
        print("  - 关闭插值功能")
        print("  - 权重阈值: 0.05")
    elif memory.total < 16 * 1024 * 1024 * 1024:  # 8-16GB
        print("• 内存适中，建议:")
        print("  - 最大点数/轨道: 500-1000")
        print("  - 插值密度: 1-2倍")
        print("  - 权重阈值: 0.02")
    else:  # 16GB以上
        print("• 内存充足，建议:")
        print("  - 最大点数/轨道: 1000-2000")
        print("  - 插值密度: 2-5倍")
        print("  - 权重阈值: 0.01")
    
    if cpu_count >= 8:
        print("• CPU核心充足，建议启用多核处理")
    elif cpu_count >= 4:
        print("• CPU核心适中，可以启用多核处理")
    else:
        print("• CPU核心较少，建议关闭多核处理")

def main():
    """主函数"""
    print("FPLO GUI性能测试工具")
    print("作者: zhujiawen@ustc.mail.edu.cn")
    print("=" * 50)
    
    # 生成系统性能报告
    generate_performance_report()
    
    # 测试多核处理性能
    test_multicore_performance()
    
    # 测试插值性能
    test_interpolation_performance()
    
    # 测试绘图性能
    test_plotting_performance()
    
    # 如果提供了文件路径，测试数据加载
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if os.path.exists(filename):
            test_data_loading_performance(filename)
        else:
            print(f"\n警告: 文件 {filename} 不存在")
    else:
        print("\n提示: 可以提供+bweight文件路径来测试数据加载性能")
        print("用法: python3 performance_test.py /path/to/+bweights")
    
    print("\n性能测试完成!")

if __name__ == "__main__":
    import sys
    main()

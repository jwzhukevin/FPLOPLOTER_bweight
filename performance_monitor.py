#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPLO GUI性能监控工具
作者: zhujiawen@ustc.mail.edu.cn
"""

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    print("警告: psutil模块未安装，性能监控功能将受限")
    print("请运行: pip install psutil 来安装完整功能")
    PSUTIL_AVAILABLE = False
    psutil = None

import time
import threading
import sys

class PerformanceMonitor:
    """性能监控器 - 支持有限功能模式"""

    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.psutil_available = PSUTIL_AVAILABLE
        
    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("性能监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("性能监控已停止")
    
    def _monitor_loop(self):
        """监控循环 - 支持备用模式"""
        while self.monitoring:
            try:
                if self.psutil_available:
                    # 获取当前进程信息
                    process = psutil.Process()

                    # CPU使用率
                    cpu_percent = process.cpu_percent()

                    # 内存使用情况
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024

                    # 系统总内存
                    system_memory = psutil.virtual_memory()
                    total_memory_gb = system_memory.total / 1024 / 1024 / 1024
                    memory_percent = (memory_mb / 1024) / total_memory_gb * 100

                    # 输出监控信息
                    print(f"\r[性能监控] CPU: {cpu_percent:5.1f}% | "
                          f"内存: {memory_mb:6.1f}MB ({memory_percent:4.1f}%) | "
                          f"线程数: {process.num_threads()}", end="", flush=True)
                else:
                    # 基础监控模式
                    current_time = time.strftime("%H:%M:%S")
                    print(f"\r[基础监控] 时间: {current_time} | "
                          f"状态: 运行中 | "
                          f"提示: 安装psutil获取详细信息", end="", flush=True)

                # 检查是否需要警告 (仅在psutil可用时)
                if self.psutil_available:
                    if cpu_percent > 80:
                        print(f"\n警告: CPU使用率过高 ({cpu_percent:.1f}%)")

                    if memory_mb > 2048:  # 超过2GB
                        print(f"\n警告: 内存使用过高 ({memory_mb:.1f}MB)")

                time.sleep(2)  # 每2秒更新一次

            except Exception as e:
                if self.psutil_available and 'psutil' in str(e):
                    # psutil相关错误
                    print(f"\n监控错误: {e}")
                    break
                elif not self.psutil_available:
                    # 基础模式下的错误，继续运行
                    continue
                else:
                    print(f"\n监控错误: {e}")
                    break

def get_system_info():
    """获取系统信息 - 支持备用模式"""
    print("=== 系统信息 ===")

    if PSUTIL_AVAILABLE:
        try:
            # CPU信息
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            print(f"CPU核心数: {cpu_count}")
            if cpu_freq:
                print(f"CPU频率: {cpu_freq.current:.0f} MHz")

            # 内存信息
            memory = psutil.virtual_memory()
            print(f"总内存: {memory.total / 1024 / 1024 / 1024:.1f} GB")
            print(f"可用内存: {memory.available / 1024 / 1024 / 1024:.1f} GB")
            print(f"内存使用率: {memory.percent:.1f}%")

            # 磁盘信息
            disk = psutil.disk_usage('/')
            print(f"磁盘总容量: {disk.total / 1024 / 1024 / 1024:.1f} GB")
            print(f"磁盘可用: {disk.free / 1024 / 1024 / 1024:.1f} GB")

        except Exception as e:
            print(f"获取系统信息失败: {e}")
            print("使用基础信息模式...")
            get_basic_system_info()
    else:
        print("psutil模块不可用，使用基础信息模式...")
        get_basic_system_info()

    print()

def get_basic_system_info():
    """获取基础系统信息 - 不依赖psutil"""
    import platform
    import os

    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python版本: {platform.python_version()}")
    print(f"处理器架构: {platform.machine()}")

    # 尝试获取CPU核心数
    try:
        cpu_count = os.cpu_count()
        print(f"CPU核心数: {cpu_count}")
    except:
        print("CPU核心数: 无法获取")

    print("注意: 安装psutil模块可获取更详细的系统信息")
    print("运行命令: pip install psutil")

def get_performance_recommendations():
    """获取性能建议"""
    print("=== 性能优化建议 ===")

    if not PSUTIL_AVAILABLE:
        print("psutil模块不可用，提供通用性能建议:")
        print("• 通用优化建议:")
        print("  - 如果内存不足，降低最大点数/轨道到500")
        print("  - 如果CPU较慢，降低插值密度到2")
        print("  - 提高权重阈值到0.05可减少计算量")
        print("  - 使用快速渲染模式可提高响应速度")
        print("• 安装psutil模块可获取针对性建议:")
        print("  pip install psutil")
        return

    try:
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()

        if memory.total < 8 * 1024 * 1024 * 1024:  # 小于8GB
            print("• 内存较少，建议:")
            print("  - 降低最大点数/轨道到500")
            print("  - 关闭插值功能")
            print("  - 提高权重阈值到0.05")

        if cpu_count < 4:
            print("• CPU核心较少，建议:")
            print("  - 降低插值密度到2")
            print("  - 使用快速渲染模式")
    except Exception as e:
        print(f"获取系统信息失败: {e}")
        print("提供通用性能建议:")
        print("  - 降低最大点数/轨道到500")
        print("  - 提高权重阈值到0.05")
    
    print("• 通用建议:")
    print("  - 关闭其他占用内存的程序")
    print("  - 使用费米面专注模式减少数据量")
    print("  - 定期保存工作，避免数据丢失")
    print()

if __name__ == "__main__":
    print("FPLO GUI性能监控工具")
    print("作者: zhujiawen@ustc.mail.edu.cn")
    print()
    
    # 显示系统信息
    get_system_info()
    
    # 显示性能建议
    get_performance_recommendations()
    
    # 启动监控
    monitor = PerformanceMonitor()
    
    try:
        monitor.start_monitoring()
        
        print("按Ctrl+C停止监控...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n正在停止监控...")
        monitor.stop_monitoring()
        print("监控已停止")

# -*- coding: utf-8 -*-
"""
工具类模块：
- MultiCoreProcessor: 多核处理器
- process_single_orbital: 单轨道处理函数
- DataLoaderThread: 数据加载线程

说明：按照项目决策，已删除增量缓存机制（PlotCache）。当前采用全量重绘，
保留懒加载与并行处理优化。
"""

import multiprocessing
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal


class MultiCoreProcessor:
    """多核处理器"""

    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        print(f"检测到 {self.cpu_count} 个CPU核心")

    def process_orbitals_parallel(self, orbital_data_list, process_func, max_workers=None):
        """并行处理轨道数据"""
        if max_workers is None:
            max_workers = min(self.cpu_count, len(orbital_data_list))
        if max_workers <= 1 or len(orbital_data_list) <= 1:
            return [process_func(data) for data in orbital_data_list]
        try:
            from concurrent.futures import ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(process_func, orbital_data_list))
            return results
        except Exception as e:
            print(f"多核处理失败，回退到单核: {e}")
            return [process_func(data) for data in orbital_data_list]


def process_single_orbital(orbital_data):
    """处理单个轨道的函数（用于多核处理）"""
    orbital_key, k_points, energies, weights, settings = orbital_data

    weight_threshold = settings.get('weight_threshold', 0.02)
    max_points = settings.get('max_points_per_orbital', 500)

    mask = weights > weight_threshold
    if not np.any(mask):
        return None

    k_filtered = k_points[mask]
    e_filtered = energies[mask]
    w_filtered = weights[mask]

    if len(k_filtered) > max_points:
        import numpy as _np
        sample_indices = _np.argsort(w_filtered)[-max_points:]
        k_filtered = k_filtered[sample_indices]
        e_filtered = e_filtered[sample_indices]
        w_filtered = w_filtered[sample_indices]

    return {
        'orbital_key': orbital_key,
        'k_points': k_filtered,
        'energies': e_filtered,
        'weights': w_filtered
    }


class DataLoaderThread(QThread):
    """数据加载线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def run(self):
        try:
            self.status.emit("开始读取文件...")
            self.progress.emit(10)

            from fplo_visualizer import FPLOVisualizer

            self.status.emit("初始化可视化器...")
            self.progress.emit(10)

            visualizer = FPLOVisualizer(self.filename)

            self.status.emit("分析文件信息...")
            self.progress.emit(20)
            visualizer.analyze_file_info()

            self.status.emit("解析头部和轨道信息...")
            self.progress.emit(40)
            visualizer.parse_header_and_system()

            self.status.emit("读取和重组数据...")
            self.progress.emit(70)
            max_kpoints = 200
            visualizer.read_and_parse_data(max_kpoints=max_kpoints)

            self.status.emit(f"数据采样: 限制到 {max_kpoints} 个k点以提高性能")
            self.status.emit("完成数据处理...")
            self.progress.emit(90)

            elements = sorted(visualizer.elements)
            orbital_types = sorted(visualizer.orbital_types)
            self.status.emit(f"检测到 {len(elements)} 种元素: {', '.join(elements)}")
            self.status.emit(f"检测到 {len(orbital_types)} 种轨道: {', '.join(orbital_types)}")
            self.status.emit(f"总计 {len(visualizer.orbital_info)} 个轨道组合")

            self.status.emit("数据加载完成!")
            self.progress.emit(100)
            self.finished.emit(visualizer)
        except Exception as e:
            self.error.emit(f"数据加载失败: {str(e)}")

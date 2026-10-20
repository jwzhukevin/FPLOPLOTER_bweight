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
from orbital_data import AnalysisCancelled, prepare_weight_points
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
    """Filter and sample one band identically to the GUI path."""
    orbital_key, k_points, energies, weights, settings = orbital_data
    k, energy, weight = prepare_weight_points(
        k_points, energies, weights, settings.get('weight_threshold', 0.02),
        settings.get('max_points_per_orbital', 500), settings.get('energy_range'),
    )
    if not len(weight):
        return None
    return {'orbital_key': orbital_key, 'k_points': k, 'energies': energy, 'weights': weight}


class DataLoaderThread(QThread):
    """Read/analyze off-thread; the native finished signal retains its lifecycle meaning."""
    result = pyqtSignal(object)
    status = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, filename, mode='complete', parent=None):
        super().__init__(parent)
        self.filename = filename
        self.mode = mode
        self.generation = 0

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            kwargs = dict(cancel_check=self.isInterruptionRequested, configure_plot=False)
            if self.mode == 'fermi':
                from fplo_fermi_visualizer import FPLOFermiVisualizer
                self.status.emit('正在后台读取文件并分析费米区域…')
                visualizer = FPLOFermiVisualizer(self.filename, **kwargs)
            else:
                from fplo_visualizer import FPLOVisualizer
                self.status.emit('正在后台读取能带数据…')
                visualizer = FPLOVisualizer(self.filename, **kwargs)
                visualizer.analyze_file_info()
                visualizer.parse_header_and_system()
                # GUI display limits come from its controls, never the loader.
                visualizer.read_and_parse_data()
            if not self.isInterruptionRequested():
                self.status.emit(f'完整数据已校验：{visualizer.num_kpoints} k点；仅绘图时限点')
                for warning in visualizer.validation_warnings:
                    self.status.emit(warning)
                # Results must not retain a callback to a soon-deleted QThread.
                visualizer._cancel_check = None
                self.result.emit(visualizer)
        except AnalysisCancelled:
            pass
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.error.emit(str(exc))

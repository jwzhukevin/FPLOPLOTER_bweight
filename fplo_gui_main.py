#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPLO能带权重可视化GUI主程序

=== 文件结构导航 ===
1. 导入和配置
2. 工具类（已迁移至 gui/）
   - MultiCoreProcessor: 多核处理器
   - DataLoaderThread: 数据加载线程
3. 绘图组件
   - InteractivePlotWidget: 交互式绘图组件
4. 控制面板
   - ControlPanel: 主要的设置控制面板
5. 日志组件（已迁移至 gui/）
   - LogWidget: 日志显示组件
6. 主窗口（已迁移至 gui/）
   - MainWindow: 应用程序主窗口
7. 程序入口
"""

import sys
import os
import traceback
import multiprocessing
import hashlib
import pickle
from functools import lru_cache
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QFileDialog, QTextEdit, QSplitter,
                             QGroupBox, QCheckBox, QSlider, QLabel, QComboBox,
                             QSpinBox, QDoubleSpinBox, QLineEdit, QColorDialog,
                             QMessageBox, QProgressBar, QTabWidget, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

# 导入日志管理器
from log_manager import logger, log_info, log_warning, log_error, log_critical, log_status, log_user_action, log_performance, log_data_info, log_debug

# 智能matplotlib后端选择
import matplotlib
try:
    # 尝试使用Qt5Agg后端
    matplotlib.use('Qt5Agg')
    print("使用Qt5Agg后端")
except Exception as e:
    try:
        # 回退到TkAgg
        matplotlib.use('TkAgg')
        print("回退到TkAgg后端")
    except:
        # 使用默认后端
        print(f"使用默认matplotlib后端: {matplotlib.get_backend()}")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 设置matplotlib的字体和样式
try:
    plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    print("matplotlib字体配置完成")
except Exception as e:
    print(f"matplotlib字体配置失败: {e}")

import numpy as np
import re
import colorsys
from matplotlib.patches import Rectangle
from matplotlib.text import Text

# 导入可视化器
from fplo_visualizer import FPLOVisualizer
from fplo_fermi_visualizer import FPLOFermiVisualizer

# 导入性能监控器
from performance_monitor import PerformanceMonitor

# 引入拆分后的模块
from gui.tools import MultiCoreProcessor, DataLoaderThread, process_single_orbital
from gui.log_widget import LogWidget

# ============================================================================
# 2. 工具类模块（已迁移）
# ============================================================================

# [Deprecated 20250827] 工具类已迁移至 gui/tools.py：
# - MultiCoreProcessor
# - process_single_orbital
# - DataLoaderThread
# 这里保留导入（见顶部），以保持外部调用不变。

# ============================================================================
# 3. 绘图组件模块
# ============================================================================

class InteractivePlotWidget(QWidget):
    """增强的交互式绘图组件"""

    def __init__(self):
        super().__init__()
        self.visualizer = None
        self.current_plot_type = "complete"  # complete, fermi, individual
        self.visible_orbitals = {}
        self.visible_elements = {}

        # 初始化多核处理器（已删除缓存机制，采用全量重绘）
        self.multicore_processor = MultiCoreProcessor()

        # 框选放大相关
        self.zoom_mode = False
        self.zoom_rect = None
        self.current_xlim = None
        self.current_ylim = None
        self.is_zoomed = False  # 标记是否处于缩放状态

        # 图例相关
        self.draggable_legend = None
        self.legend_settings = {
            'fontsize': 10,
            'frameon': True,
            'fancybox': True,
            'shadow': True,
            'framealpha': 0.9,
            'facecolor': 'white',
            'edgecolor': 'black',
            'location': 'upper right'
        }

        print(f"初始化绘图组件: {self.multicore_processor.cpu_count} 核心可用")
        # 学术标准的绘图设置 - 性能优化版
        self.plot_settings = {
            # 标题和标签设置
            'title': 'FPLO Band Structure with Orbital Projections',
            'xlabel': 'Wave vector',
            'ylabel': 'Energy (eV)',
            'title_fontsize': 16,
            'label_fontsize': 14,
            'tick_fontsize': 12,
            'legend_fontsize': 10,

            # 费米线设置
            'fermi_line_color': '#FF0000',
            'fermi_line_style': '--',
            'fermi_line_width': 2.0,
            'fermi_line_alpha': 0.8,
            'fermi_energy': 0.0,  # 可调节的费米能级
            'show_fermi_line': True,

            # 背景能带设置
            'band_line_color': '#000000',
            'band_line_width': 0.8,
            'band_line_alpha': 0.6,
            'band_line_style': '-',
            'show_band_lines': True,

            # 轨道权重点设置 - 性能优化
            'point_size_factor': 1.0,
            'point_alpha': 0.7,
            'point_min_size': 2,  # 减小最小点大小
            'point_max_size': 50,  # 减小最大点大小
            'weight_threshold': 0.02,  # 提高权重阈值，减少绘制点数

            # 费米面专注模式
            'fermi_window': [-5.0, 5.0],

            # 图形设置 - 性能优化
            'figure_dpi': 100,  # 降低DPI以提高性能
            'grid_alpha': 0.3,
            'grid_style': ':',
            'background_color': 'white',

            # 性能设置
            'max_points_per_orbital': 500,  # 每个轨道最大点数（降低）
            'use_fast_rendering': True,     # 使用快速渲染
            'use_multiprocessing': True,    # 使用多核处理

            # 学术标准颜色方案
            'color_scheme': 'academic'  # academic, colorful, monochrome
        }

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        try:
            # 创建matplotlib图形 - 自适应DPI
            import tkinter as tk
            try:
                root = tk.Tk()
                dpi = root.winfo_fpixels('1i')
                root.destroy()
                dpi = max(72, min(dpi, 150))  # 限制DPI范围
            except:
                dpi = 100  # 默认DPI

            self.figure = Figure(figsize=(12, 8), dpi=dpi)
            self.canvas = FigureCanvas(self.figure)

            # 设置canvas属性以提高兼容性
            self.canvas.setFocusPolicy(Qt.StrongFocus)
            self.canvas.setMinimumSize(600, 400)

            self.toolbar = NavigationToolbar(self.canvas, self)

            print(f"matplotlib组件初始化完成 (DPI: {dpi})")

        except Exception as e:
            print(f"matplotlib初始化警告: {e}")
            # 使用最基本的配置
            self.figure = Figure(figsize=(10, 6), dpi=80)
            self.canvas = FigureCanvas(self.figure)
            self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # 连接matplotlib事件
        try:
            self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
            self.canvas.mpl_connect('button_release_event', self.on_mouse_release)
            self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
            print("matplotlib事件连接完成")
        except Exception as e:
            print(f"matplotlib事件连接失败: {e}")

        self.setLayout(layout)

    def set_visualizer(self, visualizer, filename=None):
        """设置可视化器 - 支持双可视化器系统"""
        print(f"设置可视化器，文件: {filename}")

        # 保存文件名用于后续切换
        if filename:
            self.current_filename = filename

        # 默认设置为完整能带可视化器
        self.complete_visualizer = visualizer
        self.visualizer = visualizer
        self.current_plot_type = "complete"

        print("默认使用完整能带模式")

        # 初始化轨道可见性 - 默认全部不显示，减少初始化时间
        for orbital_key in visualizer.orbital_info.keys():
            self.visible_orbitals[orbital_key] = False

        # 自动分配颜色
        self._assign_colors()

        # 从文件头部获取费米能级
        if 'fermi_energy' in visualizer.header_info:
            self.plot_settings['fermi_energy'] = visualizer.header_info['fermi_energy']

        # 只绘制能带骨架，不绘制轨道权重
        print("初始化完成，只显示能带骨架，轨道权重默认隐藏以提高性能")
        self.plot_current_view()

    def _assign_colors(self):
        """根据当前颜色方案分配颜色"""
        if not self.visualizer:
            return

        # 学术标准颜色方案
        academic_colors = {
            # 元素特定颜色 (基于常见的学术惯例)
            's': ['#1f77b4', '#aec7e8', '#c5dbf1'],  # 蓝色系 (s轨道)
            'p': ['#ff7f0e', '#ffbb78', '#ffd1a3'],  # 橙色系 (p轨道)
            'd': ['#2ca02c', '#98df8a', '#c7e9c7'],  # 绿色系 (d轨道)
            'f': ['#d62728', '#ff9896', '#ffb3b3']   # 红色系 (f轨道)
        }

        # 多彩颜色方案
        colorful_colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2'
        ]

        # 单色方案 (灰度)
        monochrome_colors = [
            '#2C3E50', '#34495E', '#5D6D7E', '#85929E', '#AEB6BF',
            '#D5DBDB', '#BDC3C7', '#95A5A6', '#7F8C8D', '#566573'
        ]

        color_scheme = self.plot_settings.get('color_scheme', 'academic')
        print(f"应用颜色方案: {color_scheme}")
        print(f"轨道数量: {len(self.visualizer.orbital_info)}")

        if color_scheme == 'academic':
            print("使用学术标准颜色方案")
            # 按轨道类型分配颜色
            color_index = {}
            for orbital_type in ['s', 'p', 'd', 'f']:
                color_index[orbital_type] = 0

            for orbital_key in sorted(self.visualizer.orbital_info.keys()):
                _, orbital_type = orbital_key.split('_')

                if orbital_type in academic_colors:
                    colors = academic_colors[orbital_type]
                    color = colors[color_index[orbital_type] % len(colors)]
                    color_index[orbital_type] += 1
                else:
                    color = '#95A5A6'  # 默认灰色

                self.visualizer.orbital_colors[orbital_key] = color

        elif color_scheme == 'colorful':
            print("使用多彩颜色方案")
            # 使用多彩颜色方案
            for i, orbital_key in enumerate(sorted(self.visualizer.orbital_info.keys())):
                color = colorful_colors[i % len(colorful_colors)]
                self.visualizer.orbital_colors[orbital_key] = color

        elif color_scheme == 'monochrome':
            print("使用单色方案")
            # 使用单色方案
            for i, orbital_key in enumerate(sorted(self.visualizer.orbital_info.keys())):
                color = monochrome_colors[i % len(monochrome_colors)]
                self.visualizer.orbital_colors[orbital_key] = color

        # 说明：针对“元素+nℓ”键，按ℓ（s/p/d/f）分桶，对每个ℓ下的n进行全局轮换，使用高对比度调色板
        # 仅当选择学术/多彩方案时，重建颜色以提高区分度
        try:
            scheme = self.plot_settings.get('color_scheme', 'academic')
            if scheme in ('academic', 'colorful') and hasattr(self.visualizer, 'orbital_info'):
                # 高对比度基色（matplotlib/tab10风格），在每个ℓ内轮换
                high_contrast_palette = [
                    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
                ]

                # 收集每个ℓ下的所有n（全局），用于稳定轮换
                l_to_ns = {l: [] for l in ['s', 'p', 'd', 'f']}
                for orbital_key in self.visualizer.orbital_info.keys():
                    # 提取类型部分：nℓ 或 仅ℓ
                    if '_' in orbital_key:
                        type_part = orbital_key.split('_', 1)[1]
                    else:
                        type_part = orbital_key

                    # 末尾字母若为spdf则为ℓ
                    l_letter = type_part[-1] if type_part and type_part[-1] in 'spdf' else None
                    if l_letter not in l_to_ns:
                        continue
                    n_part = type_part[:-1] if l_letter and len(type_part) > 1 else ''
                    # 统一保存为字符串，空表示无n
                    if n_part not in l_to_ns[l_letter]:
                        l_to_ns[l_letter].append(n_part)

                # 对每个ℓ的n集合进行排序（数值优先，其次字典序），确保全局一致
                for l in l_to_ns:
                    def n_key(n):
                        try:
                            return (0, int(n))
                        except:
                            return (1, n)
                    l_to_ns[l].sort(key=n_key)

                # [Fix 20250825] 使用固定30色方案：元素→色系哈希/手动映射；元素内按 ℓ→n 循环取色
                # 6 个色系，每系 5 个颜色（均不含 light/dark 关键词）
                family_palette = {
                    'red':    ['#FF0000', '#B22222', '#DC143C', '#FF6347', '#FF4500'],
                    'orange': ['#FFA500', '#FFD700', '#DAA520', '#FFFF00', '#F0E68C'],
                    'green':  ['#008000', '#00FF00', '#7CFC00', '#7FFF00', '#9ACD32'],
                    'cyan':   ['#00FFFF', '#40E0D0', '#7FFFD4', '#48D1CC', '#5F9EA0'],
                    'blue':   ['#0000FF', '#4169E1', '#6495ED', '#1E90FF', '#00BFFF'],
                    'violet': ['#800080', '#EE82EE', '#FF00FF', '#8A2BE2', '#DA70D6'],
                }
                family_order = ['red', 'orange', 'green', 'cyan', 'blue', 'violet']

                # 手动覆盖映射（优先于哈希；可按需扩展/外部配置）
                # [Preset 20250825] 常见元素的色系归类
                manual_family = {
                    # red
                    'O': 'red', 'Br': 'red',
                    # orange（黄/橙系）
                    'S': 'orange', 'P': 'orange', 'Si': 'orange', 'B': 'orange',
                    'Al': 'orange', 'Fe': 'orange', 'Cu': 'orange', 'Au': 'orange',
                    # green（卤素/碱土/部分过渡金属）
                    'F': 'green', 'Cl': 'green', 'Be': 'green', 'Mg': 'green',
                    'Ca': 'green', 'Cr': 'green', 'V': 'green', 'Ni': 'green',
                    # cyan（H/C 及若干金属）
                    'H': 'cyan', 'C': 'cyan', 'Zn': 'cyan', 'Mo': 'cyan',
                    'W': 'cyan', 'Se': 'cyan',
                    # blue（N/稀有气体/部分金属）
                    'N': 'blue', 'He': 'blue', 'Ne': 'blue', 'Ar': 'blue',
                    'Kr': 'blue', 'Xe': 'blue', 'Ti': 'blue', 'Co': 'blue',
                    'Ag': 'blue', 'Pt': 'blue',
                    # violet（碱金属/碱土及部分）
                    'Li': 'violet', 'Na': 'violet', 'K': 'violet', 'Rb': 'violet',
                    'Cs': 'violet', 'Ba': 'violet', 'Mn': 'violet', 'I': 'violet',
                }

                def element_to_family(element):
                    # 手动映射优先
                    fam = manual_family.get(element)
                    if fam in family_palette:
                        return fam
                    # 稳定哈希：按字符编码求和对 6 取模
                    idx = sum(ord(c) for c in element) % len(family_order)
                    return family_order[idx]

                # 解析 type_part，返回排序键 (ℓ优先级, n, 原串)
                def parse_type(type_part):
                    l_letter = type_part[-1] if (type_part and type_part[-1] in ['s', 'p', 'd', 'f']) else ''
                    n_part = type_part[:-1] if (len(type_part) > 1 and l_letter) else ''
                    try:
                        n_val = int(n_part) if n_part != '' else -1
                    except Exception:
                        n_val = 10**9
                    l_priority = {'s': 0, 'p': 1, 'd': 2, 'f': 3}.get(l_letter, 999)
                    return (l_priority, n_val, type_part)

                # 构建：元素 -> 其所有 type_part 集合
                element_types = {}
                for ok in self.visualizer.orbital_info.keys():
                    if '_' in ok:
                        element, type_part = ok.split('_', 1)
                    else:
                        element, type_part = ok, ok
                    element_types.setdefault(element, set()).add(type_part)

                # 为每个元素分配其色系，并按 ℓ→n 排序循环上色
                type_color_map = {}
                for element, type_set in element_types.items():
                    family = element_to_family(element)
                    palette = family_palette[family]
                    sorted_types = sorted(type_set, key=lambda t: parse_type(t))
                    for i, t in enumerate(sorted_types):
                        type_color_map[(element, t)] = palette[i % len(palette)]

                # 回填到每个 orbital_key
                new_colors = {}
                for ok in sorted(self.visualizer.orbital_info.keys()):
                    if '_' in ok:
                        element, type_part = ok.split('_', 1)
                    else:
                        element, type_part = ok, ok
                    color = type_color_map.get((element, type_part), '#95A5A6')
                    new_colors[ok] = color

                # 覆盖颜色
                self.visualizer.orbital_colors.update(new_colors)
        except Exception as e:
            print(f"高对比度颜色重分配失败，沿用原方案: {e}")

        # 显示前几个轨道的颜色分配
        orbital_keys = list(self.visualizer.orbital_colors.keys())[:5]
        for orbital_key in orbital_keys:
            color = self.visualizer.orbital_colors[orbital_key]
            print(f"  {orbital_key}: {color}")

        if len(self.visualizer.orbital_colors) > 5:
            print(f"  ... 还有 {len(self.visualizer.orbital_colors) - 5} 个轨道")

        print(f"颜色分配完成，共 {len(self.visualizer.orbital_colors)} 个轨道")

    def plot_current_view(self):
        """根据当前视图模式绘制 - 简化版本"""
        current_mode = getattr(self, 'current_plot_type', 'complete')
        log_debug(f"绘制视图: {current_mode}")

        # 检查可视化器
        if not hasattr(self, 'visualizer') or self.visualizer is None:
            log_warning("无可视化器，跳过绘制")
            return

        # 保存缩放状态
        saved_xlim, saved_ylim = None, None
        if self.is_zoomed and hasattr(self.figure, 'axes') and self.figure.axes:
            ax = self.figure.axes[0]
            saved_xlim, saved_ylim = ax.get_xlim(), ax.get_ylim()

        # 根据模式选择绘制方法
        try:
            log_debug(f"使用可视化器类型: {type(self.visualizer).__name__}")

            if current_mode == "fermi":
                log_debug("调用费米专注绘制方法")
                self.plot_fermi_focused()
            else:
                log_debug("调用完整能带绘制方法")
                self.plot_complete_structure()

        except Exception as e:
            log_error(f"绘制错误: {e}")
            import traceback
            traceback.print_exc()
            return

        # 恢复缩放 - 但不覆盖费米专注模式的Y轴设置
        if self.is_zoomed and saved_xlim and saved_ylim:
            if hasattr(self.figure, 'axes') and self.figure.axes:
                ax = self.figure.axes[0]
                # 总是恢复X轴缩放
                ax.set_xlim(saved_xlim)

                # 只有在非费米专注模式下才恢复Y轴缩放
                if current_mode != "fermi":
                    ax.set_ylim(saved_ylim)
                    print(f"恢复缩放: X={saved_xlim}, Y={saved_ylim}")
                else:
                    print(f"费米专注模式: 只恢复X轴缩放={saved_xlim}, 保持费米窗口Y轴设置")

        # 强制刷新画布
        try:
            self.canvas.draw()
            self.canvas.flush_events()
            print(f"画布已强制刷新")
        except Exception as e:
            print(f"画布刷新失败: {e}")

        print(f"视图 {current_mode} 绘制完成")

    def plot_complete_structure(self):
        """绘制完整能带结构 - 学术标准"""
        if not self.visualizer:
            return

        # 设置图形样式
        plt.style.use('default')  # 重置样式
        self.figure.clear()

        # 设置背景颜色
        if self.plot_settings.get('background_color') == 'black':
            self.figure.patch.set_facecolor('black')
            text_color = 'white'
        else:
            self.figure.patch.set_facecolor('white')
            text_color = 'black'

        # 创建子图
        ax = self.figure.add_subplot(111)

        # 设置字体和样式
        title_fontsize = self.plot_settings.get('title_fontsize', 16)
        label_fontsize = self.plot_settings.get('label_fontsize', 14)
        tick_fontsize = self.plot_settings.get('tick_fontsize', 12)

        # 绘制能带骨架
        if self.plot_settings.get('show_band_lines', True):
            for band_idx in range(self.visualizer.num_bands):
                band_energies = self.visualizer.band_energies[:, band_idx]
                ax.plot(self.visualizer.k_points, band_energies,
                       color=self.plot_settings['band_line_color'],
                       linewidth=self.plot_settings['band_line_width'],
                       alpha=self.plot_settings['band_line_alpha'],
                       linestyle=self.plot_settings['band_line_style'],
                       zorder=1)

        # 绘制轨道权重
        # 如果是费米专注模式，传递费米窗口的能量范围
        energy_range = None
        if (self.current_plot_type == "fermi" and
            hasattr(self.visualizer, 'energy_window') and
            self.visualizer.energy_window is not None):
            energy_range = self.visualizer.energy_window
            log_debug(f"费米专注模式，使用能量范围: {energy_range}")

        self._plot_orbital_weights(ax, energy_range)

        # 添加费米能级
        fermi_energy = self.plot_settings.get('fermi_energy', 0.0)
        if self.plot_settings.get('show_fermi_line', True):
            ax.axhline(y=fermi_energy,
                      color=self.plot_settings['fermi_line_color'],
                      linestyle=self.plot_settings['fermi_line_style'],
                      linewidth=self.plot_settings['fermi_line_width'],
                      alpha=self.plot_settings['fermi_line_alpha'],
                      zorder=3, label='Fermi level')

        # 设置图形属性
        ax.set_xlabel(self.plot_settings['xlabel'], fontsize=label_fontsize, fontweight='bold', color=text_color)
        ax.set_ylabel(self.plot_settings['ylabel'], fontsize=label_fontsize, fontweight='bold', color=text_color)
        ax.set_title(self.plot_settings['title'], fontsize=title_fontsize, fontweight='bold', color=text_color, pad=10)

        # 设置网格
        grid_alpha = self.plot_settings.get('grid_alpha', 0.3)
        grid_style = self.plot_settings.get('grid_style', ':')
        ax.grid(True, alpha=grid_alpha, linestyle=grid_style, color='gray')

        # 应用高级设置
        self._apply_advanced_settings(ax, text_color, tick_fontsize)

        # 添加图例
        self._add_legend(ax)

        # 调整布局
        self.figure.tight_layout()

        # 绘制
        self.canvas.draw()

    def plot_fermi_focused(self):
        """绘制费米面专注模式 - 学术标准"""
        if not self.visualizer:
            return

        # 设置图形样式
        plt.style.use('default')  # 重置样式
        self.figure.clear()

        # 设置背景颜色
        if self.plot_settings.get('background_color') == 'black':
            self.figure.patch.set_facecolor('black')
            text_color = 'white'
        else:
            self.figure.patch.set_facecolor('white')
            text_color = 'black'

        # 创建子图
        ax = self.figure.add_subplot(111)

        # 设置字体和样式
        title_fontsize = self.plot_settings.get('title_fontsize', 16)
        label_fontsize = self.plot_settings.get('label_fontsize', 14)
        tick_fontsize = self.plot_settings.get('tick_fontsize', 12)

        # 获取费米能级
        fermi_energy = self.plot_settings.get('fermi_energy', 0.0)

        # 设置能量窗口
        energy_window = self.plot_settings['fermi_window']
        y_min = fermi_energy + energy_window[0]
        y_max = fermi_energy + energy_window[1]

        # 绘制能带骨架 (只绘制窗口内的部分)
        if self.plot_settings.get('show_band_lines', True):
            for band_idx in range(self.visualizer.num_bands):
                band_energies = self.visualizer.band_energies[:, band_idx]

                # 检查该能带是否在窗口内
                if np.max(band_energies) >= y_min and np.min(band_energies) <= y_max:
                    ax.plot(self.visualizer.k_points, band_energies,
                           color=self.plot_settings['band_line_color'],
                           linewidth=self.plot_settings['band_line_width'],
                           alpha=self.plot_settings['band_line_alpha'],
                           linestyle=self.plot_settings['band_line_style'],
                           zorder=1)

        # 绘制轨道权重 (只绘制窗口内的部分)
        self._plot_orbital_weights(ax, energy_range=[y_min, y_max])

        # 添加费米能级
        if self.plot_settings.get('show_fermi_line', True):
            ax.axhline(y=fermi_energy,
                      color=self.plot_settings['fermi_line_color'],
                      linestyle=self.plot_settings['fermi_line_style'],
                      linewidth=self.plot_settings['fermi_line_width'],
                      alpha=self.plot_settings['fermi_line_alpha'],
                      zorder=3, label='Fermi level')

        # 设置图形属性
        ax.set_xlabel(self.plot_settings['xlabel'], fontsize=label_fontsize, fontweight='bold', color=text_color)
        ax.set_ylabel(self.plot_settings['ylabel'], fontsize=label_fontsize, fontweight='bold', color=text_color)

        # 使用用户设置的标题，如果没有设置则使用默认的费米专注标题
        user_title = self.plot_settings.get('title', 'FPLO Band Structure with Orbital Projections')
        if user_title == 'FPLO Band Structure with Orbital Projections':
            # 如果是默认标题，则改为费米专注模式标题
            fermi_title = 'FPLO Band Structure (Fermi Level Focus)'
        else:
            # 如果用户自定义了标题，则在标题后添加费米专注标识
            fermi_title = f"{user_title} (Fermi Focus)"

        ax.set_title(fermi_title, fontsize=title_fontsize, fontweight='bold', color=text_color, pad=10)

        # 设置网格
        grid_alpha = self.plot_settings.get('grid_alpha', 0.3)
        grid_style = self.plot_settings.get('grid_style', ':')
        ax.grid(True, alpha=grid_alpha, linestyle=grid_style, color='gray')

        # 应用高级设置
        self._apply_advanced_settings(ax, text_color, tick_fontsize)

        # 设置y轴范围
        ax.set_ylim(y_min, y_max)

        # 添加图例
        self._add_legend(ax)

        # 删除Energy Window提示文字

        # 调整布局
        self.figure.tight_layout()

        # 绘制画布
        self.canvas.draw()

        log_info(f"费米专注模式绘制完成，能量范围: {y_min:.2f} ~ {y_max:.2f} eV")

    # 删除了水印相关方法

    def _apply_advanced_settings(self, ax, text_color, tick_fontsize):
        """应用高级绘图设置"""
        # 刻度线设置
        tick_direction = self.plot_settings.get('tick_direction', 'in')
        tick_width = self.plot_settings.get('tick_width', 1.0)
        tick_length = self.plot_settings.get('tick_length', 4.0)  # 新增：用户可自定义刻度线长度
        show_ticks = self.plot_settings.get('show_ticks', True)
        tick_label_fontsize = self.plot_settings.get('tick_label_fontsize', 12)
        tick_label_weight = self.plot_settings.get('tick_label_weight', 'normal')

        if show_ticks:
            ax.tick_params(axis='both', which='major',
                          labelsize=tick_label_fontsize,
                          colors=text_color,
                          direction=tick_direction,
                          width=tick_width,
                          length=tick_length)  # 使用用户设置的刻度线长度
        else:
            ax.tick_params(axis='both', which='major',
                          labelsize=tick_label_fontsize,
                          colors=text_color,
                          length=0)  # 隐藏刻度线

        # 框线设置
        frame_width = self.plot_settings.get('frame_width', 1.0)
        frame_top = self.plot_settings.get('frame_top', True)
        frame_bottom = self.plot_settings.get('frame_bottom', True)
        frame_left = self.plot_settings.get('frame_left', True)
        frame_right = self.plot_settings.get('frame_right', True)

        # 设置框线可见性和宽度
        for spine_name, visible in [('top', frame_top), ('bottom', frame_bottom),
                                   ('left', frame_left), ('right', frame_right)]:
            spine = ax.spines[spine_name]
            spine.set_visible(visible)
            if visible:
                spine.set_linewidth(frame_width)

        # 坐标轴标签设置
        xlabel_position = self.plot_settings.get('xlabel_position', 'bottom')
        ylabel_position = self.plot_settings.get('ylabel_position', 'left')
        xlabel_pad = self.plot_settings.get('xlabel_pad', 10)  # 新增：X轴标签距离
        ylabel_pad = self.plot_settings.get('ylabel_pad', 10)  # 新增：Y轴标签距离

        # 设置坐标轴标签位置
        if xlabel_position == 'top':
            ax.xaxis.set_label_position('top')
            ax.xaxis.tick_top()
        else:
            ax.xaxis.set_label_position('bottom')
            ax.xaxis.tick_bottom()

        if ylabel_position == 'right':
            ax.yaxis.set_label_position('right')
            ax.yaxis.tick_right()
        else:
            ax.yaxis.set_label_position('left')
            ax.yaxis.tick_left()

        # 设置轴标签距离边框的距离
        ax.xaxis.labelpad = xlabel_pad
        ax.yaxis.labelpad = ylabel_pad

        print(f"应用高级设置: 刻度线方向={tick_direction}, 宽度={tick_width}, 长度={tick_length}, 显示={show_ticks}")
        print(f"框线设置: 上={frame_top}, 下={frame_bottom}, 左={frame_left}, 右={frame_right}, 宽度={frame_width}")
        print(f"标签设置: 字体={tick_label_fontsize}, 粗细={tick_label_weight}, X位置={xlabel_position}, Y位置={ylabel_position}")
        print(f"标签距离: X轴={xlabel_pad}, Y轴={ylabel_pad}")

    def _plot_orbital_weights(self, ax, energy_range=None):
        """绘制轨道权重 - 性能优化版本"""
        if not self.visualizer:
            return

        import time
        start_time = time.time()

        # 获取设置参数
        weight_threshold = self.plot_settings.get('weight_threshold', 0.02)
        point_size_factor = self.plot_settings.get('point_size_factor', 1.0)
        point_alpha = self.plot_settings.get('point_alpha', 0.7)
        min_point_size = self.plot_settings.get('point_min_size', 2)
        max_point_size = self.plot_settings.get('point_max_size', 50)
        max_points_per_orbital = self.plot_settings.get('max_points_per_orbital', 1000)
        use_fast_rendering = self.plot_settings.get('use_fast_rendering', True)

        print(f"开始绘制轨道权重，阈值: {weight_threshold}, 最大点数: {max_points_per_orbital}")

        # 检查是否启用多核处理
        use_multiprocessing = self.plot_settings.get('use_multiprocessing', True)

        total_orbitals = len(self.visualizer.orbital_info)
        print(f"总轨道数: {total_orbitals}, 多核处理: {use_multiprocessing}")

        if use_multiprocessing and total_orbitals > 4:
            # 使用多核处理
            self._plot_orbital_weights_multicore(ax, energy_range, weight_threshold,
                                               point_size_factor, point_alpha,
                                               min_point_size, max_point_size,
                                               max_points_per_orbital)
        else:
            # 使用单核处理
            self._plot_orbital_weights_singlecore(ax, energy_range, weight_threshold,
                                                point_size_factor, point_alpha,
                                                min_point_size, max_point_size,
                                                max_points_per_orbital)

    def _plot_orbital_weights_multicore(self, ax, energy_range, weight_threshold,
                                      point_size_factor, point_alpha, min_point_size,
                                      max_point_size, max_points_per_orbital):
        """多核绘制轨道权重"""
        print("使用多核处理绘制轨道权重...")

        # 准备轨道数据列表
        orbital_data_list = []
        for orbital_key, indices in self.visualizer.orbital_info.items():
            # 检查轨道可见性
            if not self.visible_orbitals.get(orbital_key, True):
                continue

            if not indices or len(indices) == 0:
                continue

            # 为每个能带准备数据
            for band_idx in range(self.visualizer.num_bands):
                band_energies = self.visualizer.band_energies[:, band_idx]

                # 能量范围过滤
                if energy_range:
                    if np.max(band_energies) < energy_range[0] or np.min(band_energies) > energy_range[1]:
                        continue

                # 计算轨道权重
                try:
                    max_weight_index = self.visualizer.band_weights.shape[2] - 1
                    valid_indices = [idx for idx in indices if 0 <= idx <= max_weight_index]

                    if not valid_indices:
                        continue

                    orbital_weights = np.sum(self.visualizer.band_weights[:, band_idx, :][:, valid_indices], axis=1)

                    # 准备数据
                    settings = {
                        'weight_threshold': weight_threshold,
                        'max_points_per_orbital': max_points_per_orbital,
                        'energy_range': energy_range
                    }

                    orbital_data_list.append((
                        f"{orbital_key}_band_{band_idx}",
                        self.visualizer.k_points.copy(),
                        band_energies.copy(),
                        orbital_weights.copy(),
                        settings
                    ))

                except (IndexError, ValueError):
                    continue

        if not orbital_data_list:
            return

        print(f"准备处理 {len(orbital_data_list)} 个轨道-能带组合")

        # 多核处理
        try:
            processed_results = self.multicore_processor.process_orbitals_parallel(
                orbital_data_list, process_single_orbital,
                max_workers=min(4, len(orbital_data_list))  # 限制最大工作进程数
            )

            # 绘制结果
            for result in processed_results:
                if result is None:
                    continue

                orbital_key = result['orbital_key'].split('_band_')[0]
                color = self.visualizer.orbital_colors.get(orbital_key, '#95A5A6')

                k_filtered = result['k_points']
                e_filtered = result['energies']
                w_filtered = result['weights']

                if len(k_filtered) > 0:
                    # 计算点大小
                    w_max = np.max(w_filtered)
                    if w_max > 0:
                        w_normalized = w_filtered / w_max
                        point_sizes = (min_point_size +
                                     w_normalized * (max_point_size - min_point_size) * point_size_factor)
                    else:
                        point_sizes = np.ones_like(w_filtered) * min_point_size

                    # 直接绘制散点
                    ax.scatter(k_filtered, e_filtered, s=point_sizes, c=color,
                             alpha=point_alpha, edgecolors='none', zorder=2)

            print(f"多核处理完成，绘制了 {len([r for r in processed_results if r is not None])} 个轨道")

        except Exception as e:
            print(f"多核处理失败，回退到单核: {e}")
            self._plot_orbital_weights_singlecore(ax, energy_range, weight_threshold,
                                                point_size_factor, point_alpha,
                                                min_point_size, max_point_size,
                                                max_points_per_orbital)

    def _plot_orbital_weights_singlecore(self, ax, energy_range, weight_threshold,
                                       point_size_factor, point_alpha, min_point_size,
                                       max_point_size, max_points_per_orbital):
        """单核绘制轨道权重（原有逻辑）"""
        print("使用单核处理绘制轨道权重...")

        total_orbitals = len(self.visualizer.orbital_info)
        processed_orbitals = 0

        # 遍历所有轨道
        for orbital_key, indices in self.visualizer.orbital_info.items():
            processed_orbitals += 1
            if processed_orbitals % 5 == 0:
                print(f"处理进度: {processed_orbitals}/{total_orbitals} 轨道")
            # 检查轨道可见性
            if not self.visible_orbitals.get(orbital_key, True):
                continue

            # 检查indices是否有效
            if not indices or len(indices) == 0:
                continue



            # 获取轨道颜色
            color = self.visualizer.orbital_colors.get(orbital_key, '#95A5A6')

            # 调试信息
            if hasattr(self, '_debug_mode') and self._debug_mode:
                print(f"绘制轨道: {orbital_key}, 权重索引: {indices}, 颜色: {color}")

            # 遍历所有能带
            for band_idx in range(self.visualizer.num_bands):
                band_energies = self.visualizer.band_energies[:, band_idx]

                # 如果指定了能量范围，检查该能带是否在范围内
                if energy_range:
                    if np.max(band_energies) < energy_range[0] or np.min(band_energies) > energy_range[1]:
                        continue

                # 计算轨道权重 - 确保索引正确
                try:
                    # 检查索引是否在有效范围内
                    max_weight_index = self.visualizer.band_weights.shape[2] - 1
                    valid_indices = [idx for idx in indices if 0 <= idx <= max_weight_index]

                    if not valid_indices:
                        continue

                    # 计算该轨道的总权重
                    orbital_weights = np.sum(self.visualizer.band_weights[:, band_idx, :][:, valid_indices], axis=1)

                except (IndexError, ValueError) as e:
                    print(f"警告: 轨道 {orbital_key} 权重计算失败: {e}")
                    continue

                # 过滤显著权重
                mask = orbital_weights > weight_threshold
                if np.any(mask):
                    k_filtered = self.visualizer.k_points[mask]
                    e_filtered = band_energies[mask]
                    w_filtered = orbital_weights[mask]

                    # 如果指定了能量范围，进一步过滤
                    if energy_range:
                        range_mask = (e_filtered >= energy_range[0]) & (e_filtered <= energy_range[1])
                        k_filtered = k_filtered[range_mask]
                        e_filtered = e_filtered[range_mask]
                        w_filtered = w_filtered[range_mask]

                    if len(k_filtered) > 0:
                        # 数据采样以提高性能
                        if len(k_filtered) > max_points_per_orbital:
                            # 智能采样：保留权重最大的点
                            sample_indices = np.argsort(w_filtered)[-max_points_per_orbital:]
                            k_filtered = k_filtered[sample_indices]
                            e_filtered = e_filtered[sample_indices]
                            w_filtered = w_filtered[sample_indices]

                        # 计算点大小 - 使用更精确的缩放
                        w_max = np.max(w_filtered)
                        if w_max > 0:
                            w_normalized = w_filtered / w_max
                            point_sizes = (min_point_size +
                                         w_normalized * (max_point_size - min_point_size) * point_size_factor)
                        else:
                            point_sizes = np.ones_like(w_filtered) * min_point_size

                        # 直接绘制散点
                        print(f"完整能带模式绘制数据点数: {len(k_filtered)}")
                        ax.scatter(k_filtered, e_filtered, s=point_sizes, c=color,
                                 alpha=point_alpha, edgecolors='none', zorder=2)

    # 删除了插值相关的绘制方法

    def _get_unique_k_indices(self, k_points, tolerance=1e-10):
        """获取唯一k点的索引"""
        if len(k_points) <= 1:
            return np.arange(len(k_points))

        unique_indices = [0]  # 第一个点总是唯一的

        for i in range(1, len(k_points)):
            # 检查当前点是否与之前的点重复
            is_duplicate = False
            for j in unique_indices:
                if abs(k_points[i] - k_points[j]) < tolerance:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_indices.append(i)

        return np.array(unique_indices)

    def _find_continuous_segments(self, k_points, max_gap=0.1):
        """找到k点的连续段 - 改进版本"""
        if len(k_points) <= 1:
            return [np.array([0]) if len(k_points) == 1 else []]

        # 对k点进行排序，获取排序索引
        sorted_indices = np.argsort(k_points)
        sorted_k = k_points[sorted_indices]

        # 计算相邻k点的差值
        k_diffs = np.diff(sorted_k)

        # 动态计算间隙阈值（基于数据的统计特性）
        if len(k_diffs) > 0:
            median_diff = np.median(k_diffs)
            # 使用中位数的5倍作为间隙阈值，但不小于max_gap
            adaptive_gap = max(max_gap, median_diff * 5)
        else:
            adaptive_gap = max_gap

        # 找到不连续的点
        breaks = np.where(k_diffs > adaptive_gap)[0]

        # 构建段索引（基于排序后的索引）
        segments = []
        start = 0

        for b in breaks:
            if b + 1 > start:  # 确保段有效
                segment_indices = sorted_indices[start:b+1]
                if len(segment_indices) >= 2:  # 只保留有足够点的段
                    segments.append(segment_indices)
            start = b + 1

        # 添加最后一段
        if start < len(sorted_indices):
            segment_indices = sorted_indices[start:]
            if len(segment_indices) >= 2:
                segments.append(segment_indices)

        # 如果没有找到有效段，返回整个数组作为一段
        if not segments and len(k_points) >= 2:
            segments = [np.arange(len(k_points))]

        return segments

    def _add_legend(self, ax):
        """添加学术标准图例"""
        # 创建图例元素
        legend_elements = []

        # 按元素分组显示轨道
        elements = set()
        for orbital_key in self.visualizer.orbital_info.keys():
            element = orbital_key.split('_')[0]
            elements.add(element)

        # 按元素和轨道类型排序
        orbital_order = ['s', 'p', 'd', 'f']

        for element in sorted(elements):
            element_orbitals = []
            for orbital_key in self.visualizer.orbital_info.keys():
                if orbital_key.startswith(element + '_'):
                    element_orbitals.append(orbital_key)

            # [Fix 20250825] 图例元素内排序：按 ℓ(s<p<d<f) → n 升序 → 原串
            def legend_sort_key(orbital_key):
                # 提取类型部分（可能是 nℓ 或仅 ℓ）
                type_part = orbital_key.split('_', 1)[1] if '_' in orbital_key else orbital_key

                # 提取 ℓ 字母（最后一位在 spdf）
                l_letter = type_part[-1] if (type_part and type_part[-1] in ['s', 'p', 'd', 'f']) else ''

                # 提取 n（去掉最后一位的数字部分），无 n 时用 -1 提前显示
                n_part = type_part[:-1] if (len(type_part) > 1 and l_letter) else ''
                try:
                    n_val = int(n_part) if n_part != '' else -1
                except Exception:
                    n_val = 10**9  # 非法 n 放到最后

                l_priority = {'s': 0, 'p': 1, 'd': 2, 'f': 3}.get(l_letter, 999)
                return (l_priority, n_val, type_part)

            element_orbitals.sort(key=legend_sort_key)

            for orbital_key in element_orbitals:
                if self.visible_orbitals.get(orbital_key, True):
                    color = self.visualizer.orbital_colors.get(orbital_key, '#95A5A6')

                    # 格式化标签 - 学术标准格式
                    element_part, orbital_part = orbital_key.split('_')
                    formatted_label = f"{element_part} {orbital_part}"

                    legend_elements.append(plt.Line2D([0], [0], marker='o', color='w',
                                                    markerfacecolor=color, markersize=8,
                                                    markeredgecolor='black', markeredgewidth=0.5,
                                                    label=formatted_label))

        # 添加费米能级图例
        if self.plot_settings.get('show_fermi_line', True):
            legend_elements.append(plt.Line2D([0], [0],
                                            color=self.plot_settings['fermi_line_color'],
                                            linestyle=self.plot_settings['fermi_line_style'],
                                            linewidth=self.plot_settings['fermi_line_width'],
                                            alpha=self.plot_settings['fermi_line_alpha'],
                                            label='Fermi level'))

        # 添加能带线图例
        if self.plot_settings.get('show_band_lines', True):
            legend_elements.append(plt.Line2D([0], [0],
                                            color=self.plot_settings['band_line_color'],
                                            linestyle=self.plot_settings['band_line_style'],
                                            linewidth=self.plot_settings['band_line_width'],
                                            alpha=self.plot_settings['band_line_alpha'],
                                            label='Band structure'))

        if legend_elements:
            # 创建可拖动和自定义的图例
            legend = ax.legend(handles=legend_elements,
                             loc=self.legend_settings['location'],
                             fontsize=self.legend_settings['fontsize'],
                             frameon=self.legend_settings['frameon'],
                             fancybox=self.legend_settings['fancybox'],
                             shadow=self.legend_settings['shadow'],
                             framealpha=self.legend_settings['framealpha'],
                             edgecolor=self.legend_settings['edgecolor'],
                             facecolor=self.legend_settings['facecolor'])
            
            # 设置字体粗细
            for text in legend.get_texts():
                text.set_fontweight(self.legend_settings.get('fontweight', 'normal'))

            # 设置图例边框
            legend.get_frame().set_linewidth(0.8)

            # 使图例可拖动 - 使用matplotlib内置功能
            try:
                legend.set_draggable(True)
                print("图例拖动功能已启用（内置）")
            except AttributeError:
                # 兼容旧版本matplotlib
                try:
                    legend.draggable(True)
                    print("图例拖动功能已启用（兼容模式）")
                except:
                    print("图例拖动功能不可用")

            return legend

    def toggle_orbital_visibility(self, orbital_key, visible):
        """切换轨道可见性"""
        # [Deprecated 20250827] 旧逻辑：处理 "CLEAR_CACHE" 指令已删除（缓存机制废弃）
        if orbital_key == "RESET_ZOOM":
            # 重置缩放
            self.reset_zoom()
            return
        elif orbital_key == "LEGEND_SETTINGS":
            # 更新图例设置
            if isinstance(visible, dict):
                self.legend_settings.update(visible)
                self.plot_current_view()
                print("图例设置已更新")
            return
        elif orbital_key == "FONT_SIZE_CHANGED":
            # 界面字体大小改变，不影响绘图字体
            print(f"界面字体大小改变为: {visible}px，绘图字体保持独立设置")
            return

        # 轨道可见性设置 - 全局生效
        self.visible_orbitals[orbital_key] = visible
        self.plot_current_view()



    def set_view_mode(self, mode):
        """设置视图模式 - 支持双可视化器切换"""
        print(f"绘图组件接收到视图模式改变信号: {mode}")

        if mode not in ["complete", "fermi"]:
            print(f"无效的视图模式: {mode}")
            return

        old_mode = getattr(self, 'current_plot_type', 'unknown')
        self.current_plot_type = mode
        print(f"视图模式从 {old_mode} 切换到 {mode}")

        # 根据模式切换可视化器
        if mode == "complete":
            self._switch_to_complete_visualizer()
        elif mode == "fermi":
            self._switch_to_fermi_visualizer()

    def _switch_to_complete_visualizer(self):
        """切换到完整能带可视化器"""
        print("切换到完整能带可视化器 (fplo_visualizer.py)")

        # 如果已经是完整能带模式且可视化器存在，直接绘制
        if hasattr(self, 'complete_visualizer') and self.complete_visualizer is not None:
            print("使用已有的完整能带可视化器")
            self.visualizer = self.complete_visualizer
            self.plot_current_view()
            return

        # 需要创建完整能带可视化器
        if hasattr(self, 'current_filename') and self.current_filename:
            log_info("创建新的完整能带可视化器")
            self._create_complete_visualizer(self.current_filename)
        else:
            log_warning("没有文件名，无法创建可视化器")

    def _switch_to_fermi_visualizer(self):
        """切换到费米专注可视化器"""
        log_user_action("切换到费米专注模式")
        log_info("切换到费米专注可视化器")

        # 清除完整能带缓存
        if hasattr(self, 'plot_cache'):
            self.plot_cache.clear()
            log_debug("已清除完整能带缓存")

        # 如果已经是费米模式且可视化器存在，直接绘制
        if hasattr(self, 'fermi_visualizer') and self.fermi_visualizer is not None:
            log_debug("使用已有的费米专注可视化器")
            self.visualizer = self.fermi_visualizer
            self.plot_current_view()
            return

        # 需要创建费米专注可视化器
        if hasattr(self, 'current_filename') and self.current_filename:
            log_info("创建新的费米专注可视化器")
            self._create_fermi_visualizer(self.current_filename)
        else:
            log_warning("没有文件名，无法创建可视化器")

    def _create_complete_visualizer(self, filename):
        """创建完整能带可视化器"""
        try:
            from fplo_visualizer import FPLOVisualizer
            print("正在创建完整能带可视化器...")

            self.complete_visualizer = FPLOVisualizer(filename)
            self.visualizer = self.complete_visualizer

            print("完整能带可视化器创建成功")
            self.plot_current_view()

            # 通知控制面板更新轨道信息
            if hasattr(self, 'control_panel_ref') and self.control_panel_ref:
                self.control_panel_ref.set_orbitals(self.complete_visualizer)

        except Exception as e:
            print(f"创建完整能带可视化器失败: {e}")

    def _create_fermi_visualizer(self, filename):
        """创建费米专注可视化器"""
        try:
            from fplo_fermi_visualizer import FPLOFermiVisualizer
            print("正在创建费米专注可视化器...")

            self.fermi_visualizer = FPLOFermiVisualizer(filename)

            # 传递plot_settings到费米可视化器
            self.fermi_visualizer.plot_settings = self.plot_settings
            print("传递plot_settings到费米可视化器")

            # 应用控制面板的费米窗口设置
            if hasattr(self, 'control_panel_ref') and self.control_panel_ref:
                fermi_window = self.control_panel_ref.plot_settings.get('fermi_window', [-5.0, 5.0])
                window_size = fermi_window[1] - fermi_window[0]
                print(f"应用控制面板费米窗口设置: {fermi_window} (总窗口: {window_size:.1f} eV)")

                # 设置费米可视化器的窗口
                self.fermi_visualizer.set_fermi_window(window_size)

            self.visualizer = self.fermi_visualizer

            print("费米专注可视化器创建成功")
            self.plot_current_view()

            # 通知控制面板更新轨道信息
            if hasattr(self, 'control_panel_ref') and self.control_panel_ref:
                self.control_panel_ref.set_orbitals(self.fermi_visualizer)

        except Exception as e:
            print(f"创建费米专注可视化器失败: {e}")
            import traceback
            traceback.print_exc()
            # 如果费米可视化器创建失败，回退到完整能带
            print("回退到完整能带可视化器")
            self._switch_to_complete_visualizer()

    def update_plot_settings(self, settings):
        """更新绘图设置 - 全局生效于所有视图模式"""
        self.plot_settings.update(settings)
        print(f"更新绘图设置: {list(settings.keys())}")

        # 同步设置到费米可视化器
        if hasattr(self, 'fermi_visualizer') and self.fermi_visualizer:
            self.fermi_visualizer.plot_settings = self.plot_settings
            

        # 如果颜色方案改变，重新分配颜色
        if 'color_scheme' in settings:
            print(f"颜色方案改变为: {settings['color_scheme']}")
            self._assign_colors()

            # 更新控制面板中的轨道复选框颜色
            if hasattr(self, 'control_panel_ref'):
                self.control_panel_ref.update_orbital_checkboxes_style(
                    self.control_panel_ref.font_size)

        # 立即重绘当前视图
        self.plot_current_view()

    def on_mouse_press(self, event):
        """鼠标按下事件"""
        if event.button == 1 and event.inaxes:  # 左键
            if event.key == 'shift':  # Shift+左键开始框选
                self.zoom_mode = True
                self.zoom_start = (event.xdata, event.ydata)
                print("开始框选放大模式")

    def on_mouse_move(self, event):
        """鼠标移动事件"""
        if self.zoom_mode and event.inaxes:
            # 更新框选矩形（这里可以添加实时显示框选框的代码）
            pass

    def on_mouse_release(self, event):
        """鼠标释放事件"""
        if self.zoom_mode and event.button == 1 and event.inaxes:
            self.zoom_mode = False
            zoom_end = (event.xdata, event.ydata)

            if hasattr(self, 'zoom_start'):
                # 计算框选区域
                x1, y1 = self.zoom_start
                x2, y2 = zoom_end

                # 确保坐标顺序正确
                xmin, xmax = min(x1, x2), max(x1, x2)
                ymin, ymax = min(y1, y2), max(y1, y2)

                # 检查框选区域是否有效
                if abs(xmax - xmin) > 0.01 and abs(ymax - ymin) > 0.01:
                    self.zoom_to_region(xmin, xmax, ymin, ymax)
                    print(f"框选放大到区域: x=[{xmin:.2f}, {xmax:.2f}], y=[{ymin:.2f}, {ymax:.2f}]")
                else:
                    print("框选区域太小，忽略")

    def zoom_to_region(self, xmin, xmax, ymin, ymax):
        """放大到指定区域"""
        # 保存当前视图范围
        if hasattr(self.figure, 'axes') and len(self.figure.axes) > 0:
            ax = self.figure.axes[0]
            if not self.is_zoomed:
                # 第一次缩放，保存原始范围
                self.current_xlim = ax.get_xlim()
                self.current_ylim = ax.get_ylim()

            # 设置新的视图范围
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)
            self.is_zoomed = True

            # 重新绘制当前视图
            self.plot_current_view()

            print(f"缩放到区域: x=[{xmin:.2f}, {xmax:.2f}], y=[{ymin:.2f}, {ymax:.2f}]")

    def _plot_orbital_weights_in_region(self, ax, xmin, xmax, ymin, ymax):
        """在指定区域内绘制轨道权重"""
        if not self.visualizer:
            return

        print(f"在框选区域内重新绘制轨道权重: x=[{xmin:.2f}, {xmax:.2f}], y=[{ymin:.2f}, {ymax:.2f}]")

        # 清除当前轨道权重点（保留能带线）
        # 这里需要更精细的控制，只清除散点而保留线条

        # 重新绘制轨道权重，但只在指定区域内
        energy_range = [ymin, ymax]
        self._plot_orbital_weights(ax, energy_range=energy_range)

    def reset_zoom(self):
        """重置缩放"""
        if hasattr(self.figure, 'axes') and len(self.figure.axes) > 0:
            ax = self.figure.axes[0]
            if self.current_xlim and self.current_ylim and self.is_zoomed:
                ax.set_xlim(self.current_xlim)
                ax.set_ylim(self.current_ylim)
                self.is_zoomed = False
                self.plot_current_view()
                print("已重置缩放")

# ============================================================================
# 4. 控制面板模块 - 主要的GUI设置界面
# ============================================================================

class ControlPanel(QWidget):
    """增强的控制面板"""

    # 修复信号定义，支持多种数据类型
    orbital_toggled = pyqtSignal(str, object)  # 使用object类型支持任意数据
    view_mode_changed = pyqtSignal(str)
    settings_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.orbital_checkboxes = {}
        self.element_checkboxes = {}
        self.elements = set()
        self.orbital_types = set()
        self.font_size = 12  # 默认字体大小
        
        # 初始化绘图设置
        self.plot_settings = {
            'fermi_window': [-5.0, 5.0],  # 默认费米窗口
            'fermi_energy': 0.0,
            'show_fermi_line': True,
            'color_scheme': 'academic'
        }
        
        self.init_ui()

    def init_ui(self):
        # 使用主垂直布局
        main_layout = QVBoxLayout()

        # 创建紧凑的顶部控制区域
        top_controls = QWidget()
        top_controls.setMaximumHeight(120)  # 大幅减少顶部区域高度
        top_controls.setMinimumHeight(100)  # 设置最小高度
        top_layout = QVBoxLayout(top_controls)
        top_layout.setContentsMargins(5, 5, 5, 5)  # 减少边距
        top_layout.setSpacing(3)  # 减少间距

        # 紧凑的视图模式和界面设置组合
        compact_group = QGroupBox("视图与设置")
        compact_group.setMaximumWidth(300)  # 长度放大一倍 (150*2=300)
        compact_group.setMaximumHeight(80)   # 高度设置为目前的两倍 (40*2=80)
        compact_layout = QGridLayout()
        compact_layout.setContentsMargins(8, 8, 8, 8)  # 减少内边距
        compact_layout.setSpacing(5)  # 减少间距

        # 视图模式选择 - 使用单选按钮组实现真正的互斥
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup

        self.view_button_group = QButtonGroup()

        self.view_complete = QRadioButton("全部能带")
        self.view_complete.setChecked(True)  # 默认选中
        self.view_button_group.addButton(self.view_complete, 0)
        compact_layout.addWidget(self.view_complete, 0, 0)

        self.view_fermi = QRadioButton("费米附近")
        self.view_button_group.addButton(self.view_fermi, 1)
        compact_layout.addWidget(self.view_fermi, 0, 1)

        # 连接信号 - 使用buttonClicked信号，更加可靠
        self.view_button_group.buttonClicked.connect(self.on_view_button_clicked)

        # 删除了字体大小设置控制

        compact_group.setLayout(compact_layout)
        top_layout.addWidget(compact_group)

        main_layout.addWidget(top_controls)

        # 创建中间区域（轨道控制）- 可伸缩
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)

        # 轨道控制组
        orbital_control_group = QGroupBox("轨道显示控制")
        orbital_control_layout = QVBoxLayout()

        # 紧凑的轨道控制区域
        orbital_control_layout.setContentsMargins(4, 4, 4, 4)  # 进一步减少边距
        orbital_control_layout.setSpacing(2)  # 进一步减少间距

        # 第一行：轨道操作按钮 + 轨道数量
        first_row_layout = QHBoxLayout()
        first_row_layout.setSpacing(5)

        self.select_all_orbitals_btn = QPushButton("全选")
        self.select_all_orbitals_btn.setMinimumWidth(50)  # 设置最小宽度
        self.select_all_orbitals_btn.setMaximumWidth(60)  # 增加最大宽度
        self.select_all_orbitals_btn.clicked.connect(self.select_all_orbitals)
        first_row_layout.addWidget(self.select_all_orbitals_btn)

        self.deselect_all_orbitals_btn = QPushButton("全不选")
        self.deselect_all_orbitals_btn.setMinimumWidth(65)  # 设置最小宽度，避免文字遮挡
        self.deselect_all_orbitals_btn.setMaximumWidth(75)  # 增加最大宽度
        self.deselect_all_orbitals_btn.clicked.connect(self.deselect_all_orbitals)
        first_row_layout.addWidget(self.deselect_all_orbitals_btn)

        self.invert_selection_btn = QPushButton("反选")
        self.invert_selection_btn.setMinimumWidth(50)  # 设置最小宽度
        self.invert_selection_btn.setMaximumWidth(60)  # 增加最大宽度
        self.invert_selection_btn.clicked.connect(self.invert_orbital_selection)
        first_row_layout.addWidget(self.invert_selection_btn)

        # 轨道数量显示
        self.orbital_count_label = QLabel("轨道数量: 0")
        self.orbital_count_label.setStyleSheet("color: #7F8C8D; font-size: 10px; padding: 2px;")
        first_row_layout.addWidget(self.orbital_count_label)

        first_row_layout.addStretch()  # 弹性空间
        orbital_control_layout.addLayout(first_row_layout)

        # 删除第二行的重置缩放和测试按钮，保持界面简洁

        # 轨道显示控制区域 - 重新设计
        self.create_orbital_display_area()
        orbital_control_layout.addWidget(self.orbital_display_widget)

        orbital_control_group.setLayout(orbital_control_layout)
        middle_layout.addWidget(orbital_control_group)

        # 中间区域添加到主布局，设置伸缩因子为1（可伸缩）
        main_layout.addWidget(middle_widget, 1)

        # 创建标签页控制面板
        settings_tabs = QTabWidget()

        # 费米线设置标签页
        self.fermi_tab = QWidget()
        fermi_layout = QGridLayout()

        # 费米能级调整
        fermi_layout.addWidget(QLabel("费米能级 (eV):"), 0, 0)
        self.fermi_energy_spin = QDoubleSpinBox()
        self.fermi_energy_spin.setRange(-100, 100)
        self.fermi_energy_spin.setValue(0.0)
        self.fermi_energy_spin.setDecimals(3)
        self.fermi_energy_spin.setSingleStep(0.1)
        self.fermi_energy_spin.valueChanged.connect(self.on_fermi_settings_changed)
        fermi_layout.addWidget(self.fermi_energy_spin, 0, 1, 1, 2)

        # 费米线显示控制
        self.show_fermi_line = QCheckBox("显示费米线")
        self.show_fermi_line.setChecked(True)
        self.show_fermi_line.toggled.connect(self.on_fermi_settings_changed)
        fermi_layout.addWidget(self.show_fermi_line, 1, 0, 1, 3)

        # 费米线颜色
        fermi_layout.addWidget(QLabel("费米线颜色:"), 2, 0)
        self.fermi_color_btn = QPushButton()
        self.fermi_color_btn.setStyleSheet("background-color: #FF0000;")
        self.fermi_color_btn.clicked.connect(self.choose_fermi_color)
        fermi_layout.addWidget(self.fermi_color_btn, 2, 1, 1, 2)

        # 费米线样式
        fermi_layout.addWidget(QLabel("费米线样式:"), 3, 0)
        self.fermi_style_combo = QComboBox()
        self.fermi_style_combo.addItems(["-", "--", ":", "-."])
        self.fermi_style_combo.setCurrentText("--")
        self.fermi_style_combo.currentTextChanged.connect(self.on_fermi_settings_changed)
        fermi_layout.addWidget(self.fermi_style_combo, 3, 1, 1, 2)

        # 费米线宽度
        fermi_layout.addWidget(QLabel("费米线宽度:"), 4, 0)
        self.fermi_width_spin = QDoubleSpinBox()
        self.fermi_width_spin.setRange(0.5, 5.0)
        self.fermi_width_spin.setValue(2.0)
        self.fermi_width_spin.setSingleStep(0.1)
        self.fermi_width_spin.valueChanged.connect(self.on_fermi_settings_changed)
        fermi_layout.addWidget(self.fermi_width_spin, 4, 1, 1, 2)

        # 费米线透明度
        fermi_layout.addWidget(QLabel("费米线透明度:"), 5, 0)
        self.fermi_alpha_slider = QSlider(Qt.Horizontal)
        self.fermi_alpha_slider.setRange(1, 100)
        self.fermi_alpha_slider.setValue(80)
        self.fermi_alpha_slider.valueChanged.connect(self.on_fermi_settings_changed)
        fermi_layout.addWidget(self.fermi_alpha_slider, 5, 1)
        self.fermi_alpha_label = QLabel("0.8")
        fermi_layout.addWidget(self.fermi_alpha_label, 5, 2)

        # 费米窗口设置
        fermi_layout.addWidget(QLabel("费米窗口 (eV):"), 6, 0)
        fermi_window_layout = QHBoxLayout()

        self.fermi_window_min = QDoubleSpinBox()
        self.fermi_window_min.setRange(-50, 0)
        self.fermi_window_min.setValue(-5.0)
        self.fermi_window_min.setSingleStep(0.5)
        self.fermi_window_min.valueChanged.connect(self.on_fermi_settings_changed)

        self.fermi_window_max = QDoubleSpinBox()
        self.fermi_window_max.setRange(0, 50)
        self.fermi_window_max.setValue(5.0)
        self.fermi_window_max.setSingleStep(0.5)
        self.fermi_window_max.valueChanged.connect(self.on_fermi_settings_changed)

        fermi_window_layout.addWidget(self.fermi_window_min)
        fermi_window_layout.addWidget(QLabel("~"))
        fermi_window_layout.addWidget(self.fermi_window_max)

        fermi_layout.addLayout(fermi_window_layout, 6, 1, 1, 2)

        self.fermi_tab.setLayout(fermi_layout)

        # ===== 能带设置标签页 =====
        band_tab = QWidget()
        band_layout = QGridLayout()

        # 能带线显示控制
        self.show_band_lines = QCheckBox("显示能带线")
        self.show_band_lines.setChecked(True)
        self.show_band_lines.toggled.connect(self.on_band_settings_changed)
        band_layout.addWidget(self.show_band_lines, 0, 0, 1, 3)

        # 能带线颜色
        band_layout.addWidget(QLabel("能带线颜色:"), 1, 0)
        self.band_color_btn = QPushButton()
        self.band_color_btn.setStyleSheet("background-color: #000000;")
        self.band_color_btn.clicked.connect(self.choose_band_color)
        band_layout.addWidget(self.band_color_btn, 1, 1, 1, 2)

        # 能带线样式
        band_layout.addWidget(QLabel("能带线样式:"), 2, 0)
        self.band_style_combo = QComboBox()
        self.band_style_combo.addItems(["-", "--", ":", "-."])
        self.band_style_combo.setCurrentText("-")
        self.band_style_combo.currentTextChanged.connect(self.on_band_settings_changed)
        band_layout.addWidget(self.band_style_combo, 2, 1, 1, 2)

        # 能带线宽度
        band_layout.addWidget(QLabel("能带线宽度:"), 3, 0)
        self.band_width_spin = QDoubleSpinBox()
        self.band_width_spin.setRange(0.1, 3.0)
        self.band_width_spin.setValue(0.8)
        self.band_width_spin.setSingleStep(0.1)
        self.band_width_spin.valueChanged.connect(self.on_band_settings_changed)
        band_layout.addWidget(self.band_width_spin, 3, 1, 1, 2)

        # 能带线透明度
        band_layout.addWidget(QLabel("能带线透明度:"), 4, 0)
        self.band_alpha_slider = QSlider(Qt.Horizontal)
        self.band_alpha_slider.setRange(1, 100)
        self.band_alpha_slider.setValue(60)
        self.band_alpha_slider.valueChanged.connect(self.on_band_settings_changed)
        band_layout.addWidget(self.band_alpha_slider, 4, 1)
        self.band_alpha_label = QLabel("0.6")
        band_layout.addWidget(self.band_alpha_label, 4, 2)


        band_tab.setLayout(band_layout)

        # ===== 轨道设置标签页 - 严格按照能带设置格式 =====
        orbital_tab = QWidget()
        orbital_layout = QGridLayout()

        # 轨道点显示控制 - 按照能带的复选框格式
        self.show_orbital_points = QCheckBox("显示轨道权重点")
        self.show_orbital_points.setChecked(True)
        self.show_orbital_points.toggled.connect(self.on_orbital_settings_changed)
        orbital_layout.addWidget(self.show_orbital_points, 0, 0, 1, 3)

        # 点大小因子 - 按照能带设置格式
        orbital_layout.addWidget(QLabel("点大小因子:"), 1, 0)
        self.point_size_spin = QDoubleSpinBox()
        self.point_size_spin.setRange(0.1, 5.0)
        self.point_size_spin.setValue(1.0)
        self.point_size_spin.setSingleStep(0.1)
        self.point_size_spin.setDecimals(1)
        self.point_size_spin.valueChanged.connect(self.on_orbital_settings_changed)
        orbital_layout.addWidget(self.point_size_spin, 1, 1, 1, 2)

        # 点透明度 - 按照能带透明度格式
        orbital_layout.addWidget(QLabel("点透明度:"), 2, 0)
        self.point_alpha_slider = QSlider(Qt.Horizontal)
        self.point_alpha_slider.setRange(1, 100)
        self.point_alpha_slider.setValue(70)
        self.point_alpha_slider.valueChanged.connect(self.on_orbital_settings_changed)
        self.point_alpha_slider.valueChanged.connect(self.update_alpha_label)
        orbital_layout.addWidget(self.point_alpha_slider, 2, 1)
        self.point_alpha_label = QLabel("0.7")
        orbital_layout.addWidget(self.point_alpha_label, 2, 2)

        # 最小点大小 - 按照能带设置格式
        orbital_layout.addWidget(QLabel("最小点大小:"), 3, 0)
        self.min_point_size_spin = QSpinBox()
        self.min_point_size_spin.setRange(1, 20)
        self.min_point_size_spin.setValue(3)
        self.min_point_size_spin.valueChanged.connect(self.on_orbital_settings_changed)
        orbital_layout.addWidget(self.min_point_size_spin, 3, 1, 1, 2)

        # 最大点大小 - 按照能带设置格式
        orbital_layout.addWidget(QLabel("最大点大小:"), 4, 0)
        self.max_point_size_spin = QSpinBox()
        self.max_point_size_spin.setRange(20, 200)
        self.max_point_size_spin.setValue(80)
        self.max_point_size_spin.valueChanged.connect(self.on_orbital_settings_changed)
        orbital_layout.addWidget(self.max_point_size_spin, 4, 1, 1, 2)

        # 权重阈值 - 按照能带设置格式
        orbital_layout.addWidget(QLabel("权重阈值:"), 5, 0)
        self.weight_threshold_spin = QDoubleSpinBox()
        self.weight_threshold_spin.setRange(0.001, 0.5)
        self.weight_threshold_spin.setValue(0.01)
        self.weight_threshold_spin.setDecimals(3)
        self.weight_threshold_spin.setSingleStep(0.005)
        self.weight_threshold_spin.valueChanged.connect(self.on_orbital_settings_changed)
        orbital_layout.addWidget(self.weight_threshold_spin, 5, 1, 1, 2)

        # 不在这里设置orbital_tab的布局，因为后面会重新设置

        # 删除多余的left_group代码

        # 右列 - 性能设置
        right_group = QGroupBox("性能")
        right_layout = QGridLayout()
        right_layout.setVerticalSpacing(8)   # 参照费米线区域的间距
        right_layout.setHorizontalSpacing(6) # 参照费米线区域的间距

        # 设置列宽比例，参照费米线区域的样式
        right_layout.setColumnStretch(0, 2)  # 标签列
        right_layout.setColumnStretch(1, 3)  # 控件列

        # 多核处理 - 参照费米线样式
        right_layout.addWidget(QLabel("多核处理:"), 0, 0)
        self.use_multiprocessing = QCheckBox()
        self.use_multiprocessing.setChecked(True)
        self.use_multiprocessing.setToolTip(f"使用多核处理加速绘图 (检测到{multiprocessing.cpu_count()}核)")
        self.use_multiprocessing.toggled.connect(self.on_orbital_settings_changed)
        right_layout.addWidget(self.use_multiprocessing, 0, 1)

        # [Deprecated 20250827] 旧逻辑：缓存机制（cache_enabled 复选框）UI 已移除，采用全量重绘
        # 最大点数/轨道 - 参照费米线样式
        right_layout.addWidget(QLabel("最大点数/轨道:"), 2, 0)
        self.max_points_spin = QSpinBox()
        self.max_points_spin.setRange(100, 5000)
        self.max_points_spin.setValue(500)
        self.max_points_spin.setSingleStep(100)
        self.max_points_spin.setMaximumWidth(100)  # 参照费米线区域的输入框宽度
        self.max_points_spin.setToolTip("每个轨道最大绘制点数，越少越快")
        self.max_points_spin.valueChanged.connect(self.on_orbital_settings_changed)
        right_layout.addWidget(self.max_points_spin, 2, 1)

        # [Deprecated 20250827] 旧逻辑：清除缓存按钮已移除

        right_group.setLayout(right_layout)

        # 设置右列样式
        right_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #BDC3C7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        # 原有的orbital_tab布局已删除，轨道和性能已拆分为独立标签页

        # ===== 图形设置标签页 - 一列布局带滚动 =====
        figure_tab = QWidget()
        figure_tab_layout = QVBoxLayout(figure_tab)
        figure_tab_layout.setContentsMargins(5, 5, 5, 5)

        # 创建滚动区域 - 只使用垂直滚动
        figure_scroll_area = QScrollArea()
        figure_scroll_area.setWidgetResizable(True)
        figure_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        figure_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 滚动内容容器
        figure_scroll_widget = QWidget()
        figure_layout = QGridLayout(figure_scroll_widget)
        figure_layout.setVerticalSpacing(8)  # 设置行间距
        figure_layout.setHorizontalSpacing(8)  # 设置列间距

        # 设置列宽比例，确保输入框完全显示
        figure_layout.setColumnStretch(0, 1)  # 标签列
        figure_layout.setColumnStretch(1, 2)  # 控件列，减小比例
        figure_layout.setColumnStretch(2, 0)  # 额外列，不占空间

        # 标题设置
        figure_layout.addWidget(QLabel("标题:"), 0, 0)
        self.title_edit = QLineEdit("FPLO Band Structure with Orbital Projections")
        self.title_edit.setMaximumWidth(180)  # 和XY轴标签输入框一样宽
        self.title_edit.setMinimumWidth(120)  # 和XY轴标签输入框一样宽
        self.title_edit.textChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.title_edit, 0, 1)

        # 标题字体大小
        figure_layout.addWidget(QLabel("标题字体大小:"), 1, 0)
        self.title_fontsize_spin = QSpinBox()
        self.title_fontsize_spin.setRange(8, 24)
        self.title_fontsize_spin.setValue(16)
        self.title_fontsize_spin.setMaximumWidth(100)  # 限制宽度
        self.title_fontsize_spin.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.title_fontsize_spin, 1, 1)

        # X轴标签
        figure_layout.addWidget(QLabel("X轴标签:"), 2, 0)
        self.xlabel_edit = QLineEdit("Wave vector")
        self.xlabel_edit.setMaximumWidth(180)  # 进一步限制宽度
        self.xlabel_edit.setMinimumWidth(120)  # 设置最小宽度
        self.xlabel_edit.textChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.xlabel_edit, 2, 1)

        # Y轴标签
        figure_layout.addWidget(QLabel("Y轴标签:"), 3, 0)
        self.ylabel_edit = QLineEdit("Energy (eV)")
        self.ylabel_edit.setMaximumWidth(180)  # 进一步限制宽度
        self.ylabel_edit.setMinimumWidth(120)  # 设置最小宽度
        self.ylabel_edit.textChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.ylabel_edit, 3, 1)

        # 轴标签字体大小
        figure_layout.addWidget(QLabel("轴标签字体大小:"), 4, 0)
        self.label_fontsize_spin = QSpinBox()
        self.label_fontsize_spin.setRange(8, 20)
        self.label_fontsize_spin.setValue(14)
        self.label_fontsize_spin.setMaximumWidth(100)  # 限制宽度
        self.label_fontsize_spin.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.label_fontsize_spin, 4, 1)

        # DPI设置
        figure_layout.addWidget(QLabel("图像DPI:"), 5, 0)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(150)
        self.dpi_spin.setMaximumWidth(100)  # 限制宽度
        self.dpi_spin.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.dpi_spin, 5, 1)

        # 网格透明度
        figure_layout.addWidget(QLabel("网格透明度:"), 6, 0)
        self.grid_alpha_slider = QSlider(Qt.Horizontal)
        self.grid_alpha_slider.setRange(0, 100)
        self.grid_alpha_slider.setValue(30)
        self.grid_alpha_slider.setMaximumWidth(120)  # 再缩小为现在的75% (160*0.75=120)
        self.grid_alpha_slider.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.grid_alpha_slider, 6, 1)
        self.grid_alpha_label = QLabel("0.3")
        figure_layout.addWidget(self.grid_alpha_label, 6, 2)

        # 刻度线方向
        figure_layout.addWidget(QLabel("刻度线方向:"), 7, 0)
        self.tick_direction_combo = QComboBox()
        self.tick_direction_combo.addItems(["向内", "向外", "双向"])
        self.tick_direction_combo.setCurrentText("向内")
        self.tick_direction_combo.setMaximumWidth(150)  # 限制宽度
        self.tick_direction_combo.currentTextChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.tick_direction_combo, 7, 1)

        # 刻度线宽度
        figure_layout.addWidget(QLabel("刻度线宽度:"), 8, 0)
        self.tick_width_spin = QDoubleSpinBox()
        self.tick_width_spin.setRange(0.1, 5.0)
        self.tick_width_spin.setValue(1.0)
        self.tick_width_spin.setSingleStep(0.1)
        self.tick_width_spin.setMaximumWidth(100)  # 限制宽度
        self.tick_width_spin.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.tick_width_spin, 8, 1)

        # 刻度线长度
        figure_layout.addWidget(QLabel("刻度线长度:"), 9, 0)
        self.tick_length_spin = QDoubleSpinBox()
        self.tick_length_spin.setRange(1.0, 20.0)
        self.tick_length_spin.setValue(4.0)  # matplotlib默认值
        self.tick_length_spin.setSingleStep(0.5)
        self.tick_length_spin.setMaximumWidth(100)  # 限制宽度
        self.tick_length_spin.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.tick_length_spin, 9, 1)

        # 显示刻度线
        self.show_ticks = QCheckBox("显示刻度线")
        self.show_ticks.setChecked(True)
        self.show_ticks.toggled.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.show_ticks, 10, 0, 1, 3)

        # 框线显示
        figure_layout.addWidget(QLabel("框线显示:"), 11, 0)
        frame_layout = QHBoxLayout()
        frame_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        frame_layout.setSpacing(4)  # 再减少选项间距为现在的一半 (8*0.5=4px)
        self.frame_top = QCheckBox("上")
        self.frame_bottom = QCheckBox("下")
        self.frame_left = QCheckBox("左")
        self.frame_right = QCheckBox("右")
        for frame_cb in [self.frame_top, self.frame_bottom, self.frame_left, self.frame_right]:
            frame_cb.setChecked(True)
            frame_cb.toggled.connect(self.on_figure_settings_changed)
            frame_layout.addWidget(frame_cb)
        frame_layout.addStretch()  # 添加弹性空间保证全部显示
        frame_widget = QWidget()
        frame_widget.setLayout(frame_layout)
        figure_layout.addWidget(frame_widget, 11, 1, 1, 2)

        # 框线宽度
        figure_layout.addWidget(QLabel("框线宽度:"), 12, 0)
        self.frame_width_spin = QDoubleSpinBox()
        self.frame_width_spin.setRange(0.1, 5.0)
        self.frame_width_spin.setValue(1.0)
        self.frame_width_spin.setSingleStep(0.1)
        self.frame_width_spin.setMaximumWidth(100)  # 限制宽度
        self.frame_width_spin.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.frame_width_spin, 12, 1)

        # 数值标签字体大小
        figure_layout.addWidget(QLabel("数值标签字体大小:"), 13, 0)
        self.tick_label_fontsize_spin = QSpinBox()
        self.tick_label_fontsize_spin.setRange(6, 20)
        self.tick_label_fontsize_spin.setValue(12)
        self.tick_label_fontsize_spin.setMaximumWidth(100)  # 限制宽度
        self.tick_label_fontsize_spin.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.tick_label_fontsize_spin, 13, 1)

        # 数值标签粗细
        figure_layout.addWidget(QLabel("数值标签粗细:"), 14, 0)
        self.tick_label_weight_combo = QComboBox()
        self.tick_label_weight_combo.addItems(["normal", "bold"])
        self.tick_label_weight_combo.setCurrentText("normal")
        self.tick_label_weight_combo.setMaximumWidth(150)  # 限制宽度
        self.tick_label_weight_combo.currentTextChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.tick_label_weight_combo, 14, 1)

        # X轴标签位置
        figure_layout.addWidget(QLabel("X轴标签位置:"), 15, 0)
        self.xlabel_position_combo = QComboBox()
        self.xlabel_position_combo.addItems(["bottom", "top"])
        self.xlabel_position_combo.setCurrentText("bottom")
        self.xlabel_position_combo.setMaximumWidth(150)  # 限制宽度
        self.xlabel_position_combo.currentTextChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.xlabel_position_combo, 15, 1)

        # X轴标签距离
        figure_layout.addWidget(QLabel("X轴标签距离:"), 16, 0)
        self.xlabel_pad_spin = QDoubleSpinBox()
        self.xlabel_pad_spin.setRange(0, 50)
        self.xlabel_pad_spin.setValue(10)  # 默认距离
        self.xlabel_pad_spin.setSingleStep(1)
        self.xlabel_pad_spin.setMaximumWidth(100)
        self.xlabel_pad_spin.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.xlabel_pad_spin, 16, 1)

        # Y轴标签位置
        figure_layout.addWidget(QLabel("Y轴标签位置:"), 17, 0)
        self.ylabel_position_combo = QComboBox()
        self.ylabel_position_combo.addItems(["left", "right"])
        self.ylabel_position_combo.setCurrentText("left")
        self.ylabel_position_combo.setMaximumWidth(150)  # 限制宽度
        self.ylabel_position_combo.currentTextChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.ylabel_position_combo, 17, 1)

        # Y轴标签距离
        figure_layout.addWidget(QLabel("Y轴标签距离:"), 18, 0)
        self.ylabel_pad_spin = QDoubleSpinBox()
        self.ylabel_pad_spin.setRange(0, 50)
        self.ylabel_pad_spin.setValue(10)  # 默认距离
        self.ylabel_pad_spin.setSingleStep(1)
        self.ylabel_pad_spin.setMaximumWidth(100)
        self.ylabel_pad_spin.valueChanged.connect(self.on_figure_settings_changed)
        figure_layout.addWidget(self.ylabel_pad_spin, 18, 1)

        # 设置滚动区域
        figure_scroll_area.setWidget(figure_scroll_widget)
        figure_tab_layout.addWidget(figure_scroll_area)

        # 图例设置标签页
        legend_tab = QWidget()
        legend_layout = QGridLayout()

        # 图例字体大小
        legend_layout.addWidget(QLabel("字体大小:"), 0, 0)
        self.legend_fontsize_spin = QSpinBox()
        self.legend_fontsize_spin.setRange(6, 20)
        self.legend_fontsize_spin.setValue(10)
        self.legend_fontsize_spin.valueChanged.connect(self.on_legend_settings_changed)
        legend_layout.addWidget(self.legend_fontsize_spin, 0, 1)

        # 图例字体粗细
        legend_layout.addWidget(QLabel("字体粗细:"), 0, 2)
        self.legend_fontweight_combo = QComboBox()
        self.legend_fontweight_combo.addItems(["normal", "bold"])
        self.legend_fontweight_combo.setCurrentText("normal")
        self.legend_fontweight_combo.currentTextChanged.connect(self.on_legend_settings_changed)
        legend_layout.addWidget(self.legend_fontweight_combo, 0, 3)

        # 图例位置
        legend_layout.addWidget(QLabel("位置:"), 1, 0)
        self.legend_location_combo = QComboBox()
        self.legend_location_combo.addItems([
            'upper right', 'upper left', 'lower left', 'lower right',
            'right', 'center left', 'center right', 'lower center',
            'upper center', 'center'
        ])
        self.legend_location_combo.setCurrentText('upper right')
        self.legend_location_combo.currentTextChanged.connect(self.on_legend_settings_changed)
        legend_layout.addWidget(self.legend_location_combo, 1, 1)

        # 图例边框
        self.legend_frameon = QCheckBox("显示边框")
        self.legend_frameon.setChecked(True)
        self.legend_frameon.toggled.connect(self.on_legend_settings_changed)
        legend_layout.addWidget(self.legend_frameon, 2, 0, 1, 2)

        # 图例阴影
        self.legend_shadow = QCheckBox("显示阴影")
        self.legend_shadow.setChecked(True)
        self.legend_shadow.toggled.connect(self.on_legend_settings_changed)
        legend_layout.addWidget(self.legend_shadow, 3, 0, 1, 2)

        # 图例圆角
        self.legend_fancybox = QCheckBox("圆角边框")
        self.legend_fancybox.setChecked(True)
        self.legend_fancybox.toggled.connect(self.on_legend_settings_changed)
        legend_layout.addWidget(self.legend_fancybox, 4, 0, 1, 2)

        # 图例透明度
        legend_layout.addWidget(QLabel("透明度:"), 5, 0)
        self.legend_alpha_spin = QDoubleSpinBox()
        self.legend_alpha_spin.setRange(0.0, 1.0)
        self.legend_alpha_spin.setSingleStep(0.1)
        self.legend_alpha_spin.setValue(0.9)
        self.legend_alpha_spin.valueChanged.connect(self.on_legend_settings_changed)
        legend_layout.addWidget(self.legend_alpha_spin, 5, 1)

        legend_tab.setLayout(legend_layout)

        # 轨道标签页只包含轨道设置，不包含轨道显示控制
        orbital_tab.setLayout(orbital_layout)

        # 创建性能标签页
        performance_tab = QWidget()
        performance_layout = QVBoxLayout()
        performance_layout.addWidget(right_group)  # 添加性能设置组
        performance_tab.setLayout(performance_layout)

        # 删除重复的轨道显示控制标签页，使用现有的轨道显示控制模块

        # 添加所有标签页
        settings_tabs.addTab(self.fermi_tab, "费米线")
        settings_tabs.addTab(band_tab, "能带")
        settings_tabs.addTab(orbital_tab, "轨道")
        settings_tabs.addTab(performance_tab, "性能")
        settings_tabs.addTab(figure_tab, "图形")
        settings_tabs.addTab(legend_tab, "图例")

        # 创建底部设置区域（紧凑设计）
        bottom_widget = QWidget()
        bottom_widget.setMaximumHeight(280)  # 减少底部设置区域高度
        bottom_widget.setMinimumHeight(220)  # 减少最小高度
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(3, 3, 3, 3)  # 减少边距
        bottom_layout.addWidget(settings_tabs)

        # 底部区域添加到主布局，设置伸缩因子为0（固定大小）
        main_layout.addWidget(bottom_widget, 0)

        # 设置主布局
        self.setLayout(main_layout)

        # 应用初始字体样式
        self.apply_unified_font_style(self.font_size)

    def on_view_button_clicked(self, button):
        """视图按钮点击处理 - 全新的简洁逻辑"""
        # 确定当前选中的模式
        if button == self.view_complete:
            current_mode = "complete"
            print("用户选择: 完整能带模式")
        elif button == self.view_fermi:
            current_mode = "fermi"
            print("用户选择: 费米专注模式")
        else:
            print("未知的视图按钮")
            return

        # 发送视图模式改变信号
        print(f"发送视图模式改变信号: {current_mode}")
        self.view_mode_changed.emit(current_mode)
        
        # 更新费米能带数控件的启用状态
        self.update_fermi_band_controls(current_mode)


    def update_fermi_band_controls(self, mode):
        """根据视图模式更新费米相关控件的启用状态"""
        is_fermi_mode = (mode == "fermi")
        
        
        # 启用/禁用费米窗口控件
        # 找到费米窗口标签
        fermi_window_label = None
        for i in range(self.fermi_tab.layout().count()):
            item = self.fermi_tab.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QLabel):
                if "费米窗口" in item.widget().text():
                    fermi_window_label = item.widget()
                    break
        
        if fermi_window_label:
            fermi_window_label.setEnabled(is_fermi_mode)
        
        self.fermi_window_min.setEnabled(is_fermi_mode)
        self.fermi_window_max.setEnabled(is_fermi_mode)
        
        # 更新样式以视觉上区分启用/禁用状态
        style = "" if is_fermi_mode else "color: gray;"
        if fermi_window_label:
            fermi_window_label.setStyleSheet(style)
        
        print(f"费米相关控件{'启用' if is_fermi_mode else '禁用'}")

    def get_current_view_mode(self):
        """获取当前视图模式"""
        if self.view_complete.isChecked():
            return "complete"
        elif self.view_fermi.isChecked():
            return "fermi"
        else:
            return "complete"  # 默认返回完整能带

    def set_view_mode_programmatically(self, mode):
        """程序化设置视图模式（不触发信号）"""
        if mode == "complete":
            self.view_complete.setChecked(True)
        elif mode == "fermi":
            self.view_fermi.setChecked(True)
        print(f"程序化设置视图模式为: {mode}")

    def set_orbitals(self, visualizer):
        """设置轨道信息 - 稳定版本"""
        print(f"设置轨道信息...")

        # 保存轨道信息
        self.orbital_info = visualizer.orbital_info.copy()
        self.visualizer = visualizer

        print(f"总轨道数: {len(self.orbital_info)}")

        # 重新构建轨道控制
        self.rebuild_orbital_controls()

        # 检查结果
        created_count = len(self.orbital_checkboxes)
        expected_count = len(self.orbital_info)

        print(f"轨道设置完成: {created_count}/{expected_count}")

        # 检查是否有缺失
        if created_count != expected_count:
            missing_orbitals = set(self.orbital_info.keys()) - set(self.orbital_checkboxes.keys())
            print(f"缺失轨道: {missing_orbitals}")
            return False
        else:
            print("所有轨道都已创建")
            return True

    def rebuild_orbital_controls(self):
        """重新构建轨道控制 - 稳定版本"""
        # 检查orbital_content_layout是否存在
        if not hasattr(self, 'orbital_content_layout'):
            print("错误: orbital_content_layout不存在，需要先调用create_orbital_display_area()")
            return

        print(f"orbital_content_layout存在，当前项数: {self.orbital_content_layout.count()}")

        # 清除现有控件
        self.clear_orbital_controls()

        # 获取并排序轨道
        orbital_keys = list(self.orbital_info.keys())
        orbital_keys.sort(key=self.get_orbital_sort_key)

        # 创建轨道控件
        created_count = 0
        failed_orbitals = []

        for orbital_key in orbital_keys:
            try:
                self.create_orbital_checkbox(orbital_key)
                created_count += 1
            except Exception as e:
                print(f"创建轨道 {orbital_key} 失败: {e}")
                failed_orbitals.append(orbital_key)
                continue

        if failed_orbitals:
            print(f"失败轨道: {failed_orbitals}")

        print(f"创建了 {created_count} 个轨道控件")

        # 添加弹性空间
        self.orbital_content_layout.addStretch()

        # 强制更新布局
        QApplication.processEvents()
        self.orbital_content_widget.updateGeometry()
        self.orbital_content_layout.activate()
        self.orbital_content_widget.adjustSize()
        QApplication.processEvents()

        # 更新显示
        self.update_orbital_display()

        # 强制显示所有相关widget - 多重保险
        if hasattr(self, 'orbital_display_widget'):
            self.orbital_display_widget.setVisible(True)
            self.orbital_display_widget.show()
            self.orbital_display_widget.raise_()

        if hasattr(self, 'orbital_scroll_area'):
            self.orbital_scroll_area.setVisible(True)
            self.orbital_scroll_area.show()
            self.orbital_scroll_area.raise_()

        if hasattr(self, 'orbital_content_widget'):
            self.orbital_content_widget.setVisible(True)
            self.orbital_content_widget.show()
            self.orbital_content_widget.raise_()

        # 强制显示所有轨道复选框
        for checkbox in self.orbital_checkboxes.values():
            checkbox.setVisible(True)
            checkbox.show()
            checkbox.raise_()

        # 强制更新布局和几何形状
        QApplication.processEvents()

        if hasattr(self, 'orbital_display_widget'):
            self.orbital_display_widget.updateGeometry()
            self.orbital_display_widget.update()
            self.orbital_display_widget.repaint()

        if hasattr(self, 'orbital_content_widget'):
            self.orbital_content_widget.updateGeometry()
            self.orbital_content_widget.update()
            self.orbital_content_widget.repaint()

        print(f"轨道控制重建完成，共 {len(self.orbital_checkboxes)} 个")
        print(f"强制显示后 orbital_display_widget 可见性: {self.orbital_display_widget.isVisible() if hasattr(self, 'orbital_display_widget') else 'N/A'}")

        # 检查所有复选框的最终可见性
        visible_checkboxes = sum(1 for cb in self.orbital_checkboxes.values() if cb.isVisible())
        print(f"最终可见的轨道复选框: {visible_checkboxes}/{len(self.orbital_checkboxes)}")

    def clear_orbital_controls(self):
        """清除所有轨道控件"""
        # 立即删除所有控件，不使用deleteLater()
        widgets_to_delete = []
        while self.orbital_content_layout.count():
            child = self.orbital_content_layout.takeAt(0)
            if child.widget():
                widgets_to_delete.append(child.widget())
            elif child.spacerItem():
                # 删除弹性空间
                del child

        # 立即删除所有控件
        for widget in widgets_to_delete:
            widget.setParent(None)
            del widget

        # 清空字典
        self.orbital_checkboxes.clear()

        # 强制处理事件并再次检查
        QApplication.processEvents()
        self.orbital_content_widget.updateGeometry()
        self.orbital_content_layout.update()

    def get_orbital_sort_key(self, orbital_key):
        """获取轨道排序键"""
        # 规则：元素 → ℓ优先级(s<p<d<f) → 主量子数n升序 → 原串
        try:
            if '_' in orbital_key:
                element, type_part = orbital_key.split('_', 1)
            else:
                element, type_part = orbital_key, orbital_key

            # 提取 ℓ 字母
            l_letter = type_part[-1] if (type_part and type_part[-1] in ['s', 'p', 'd', 'f']) else ''

            # 提取 n（去掉最后一个 ℓ 字母后的数字部分）
            n_part = type_part[:-1] if (len(type_part) > 1 and l_letter) else ''
            try:
                n_val = int(n_part) if n_part != '' else -1
            except Exception:
                n_val = 10**9  # 非法 n 放末尾

            l_priority = {'s': 0, 'p': 1, 'd': 2, 'f': 3}.get(l_letter, 999)
            return (element, l_priority, n_val, type_part)
        except Exception:
            return (orbital_key, 999, 10**9, orbital_key)

    def create_orbital_checkbox(self, orbital_key):
        """创建单个轨道复选框"""
        # 检查轨道信息是否存在
        if orbital_key not in self.orbital_info:
            raise ValueError(f"轨道 {orbital_key} 不在轨道信息中")

        # 获取轨道信息
        weight_indices = self.orbital_info.get(orbital_key, [])
        weight_count = len(weight_indices)

        # 检查可视化器是否有颜色信息
        if not hasattr(self.visualizer, 'orbital_colors'):
            color = '#95A5A6'
        else:
            color = self.visualizer.orbital_colors.get(orbital_key, '#95A5A6')

        # 创建复选框 - 默认不选中，减少初始化时间
        checkbox = QCheckBox(f"{orbital_key} ({weight_count})")
        checkbox.setChecked(False)

        # 设置样式 - 紧凑版本，间距减少为原来的一半
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-size: {self.font_size}px;
                padding: 3px 4px;
                color: #2C3E50;
                min-height: 20px;
                background-color: transparent;
                margin: 1px 0px;
            }}
            QCheckBox:hover {{
                background-color: #ECF0F1;
                border-radius: 4px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {color};
                border-radius: 4px;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                background-color: {color};
                border: 2px solid {color};
            }}
            QCheckBox::indicator:hover {{
                border-width: 3px;
            }}
        """)

        # 设置工具提示
        checkbox.setToolTip(f"轨道: {orbital_key}\\n权重数量: {weight_count}\\n颜色: {color}")

        # 连接信号
        checkbox.toggled.connect(lambda checked, key=orbital_key:
                               self.orbital_toggled.emit(key, checked))

        # 保存引用
        self.orbital_checkboxes[orbital_key] = checkbox

        # 强化复选框可见性设置
        checkbox.setVisible(True)
        checkbox.show()

        # 添加到布局
        print(f"添加轨道复选框到布局: {orbital_key}")
        self.orbital_content_layout.addWidget(checkbox)

        # 强制处理事件并再次检查
        QApplication.processEvents()

        print(f"布局项数量现在为: {self.orbital_content_layout.count()}")
        print(f"复选框 {orbital_key} 可见性: {checkbox.isVisible()}")
        print(f"复选框父widget: {type(checkbox.parent()).__name__ if checkbox.parent() else 'None'}")

        # 如果复选框仍然不可见，强制显示其父widget
        if not checkbox.isVisible():
            print(f"复选框 {orbital_key} 不可见，检查父widget链...")
            parent = checkbox.parent()
            while parent:
                print(f"  父widget: {type(parent).__name__}, 可见: {parent.isVisible()}")
                if not parent.isVisible():
                    parent.setVisible(True)
                    parent.show()
                parent = parent.parent()

        return checkbox

    def update_orbital_display(self):
        """更新轨道显示"""
        # 更新轨道数量
        count = len(self.orbital_checkboxes)
        self.orbital_count_label.setText(f"轨道数量: {count}")

        print(f"更新轨道显示:")
        print(f"  轨道数量: {count}")
        print(f"  布局项数量: {self.orbital_content_layout.count()}")

        # 强制更新布局
        self.orbital_content_widget.adjustSize()
        self.orbital_scroll_area.updateGeometry()

        # 检查是否需要滚动
        content_height = self.orbital_content_widget.sizeHint().height()
        content_min_height = self.orbital_content_widget.minimumSizeHint().height()
        scroll_height = self.orbital_scroll_area.viewport().height()

        print(f"  内容高度: {content_height}")
        print(f"  内容最小高度: {content_min_height}")
        print(f"  滚动区域高度: {scroll_height}")

        # 如果内容高度太小，强制设置一个合理的高度
        if count > 0 and content_height < count * 30:
            estimated_height = count * 35 + 50  # 每个轨道35像素 + 边距
            self.orbital_content_widget.setMinimumHeight(estimated_height)
            print(f"  强制设置内容最小高度: {estimated_height}")
            content_height = estimated_height

        if content_height > scroll_height:
            print("  内容超出滚动区域，滚动条将自动显示")
        else:
            print("  内容未超出滚动区域，无需滚动条")

    def refresh_orbital_scroll_area(self):
        """刷新轨道滚动区域 - 兼容旧接口"""
        self.update_orbital_display()

    # 旧的setup_orbital_controls方法已被rebuild_orbital_controls替代

    def select_all_orbitals(self):
        """全选所有轨道"""
        for checkbox in self.orbital_checkboxes.values():
            checkbox.setChecked(True)
        print("已全选所有轨道")

    def deselect_all_orbitals(self):
        """全不选所有轨道"""
        for checkbox in self.orbital_checkboxes.values():
            checkbox.setChecked(False)
        print("已全不选所有轨道")

    def invert_orbital_selection(self):
        """反选轨道"""
        for checkbox in self.orbital_checkboxes.values():
            checkbox.setChecked(not checkbox.isChecked())
        print("已反选轨道")

    def reset_zoom(self):
        """重置缩放"""
        # 这个方法会被主窗口连接到绘图组件
        self.orbital_toggled.emit("RESET_ZOOM", True)

    # 删除了字体大小改变方法

    def apply_unified_font_style(self, font_size):
        """应用统一的字体样式到所有界面元素"""
        # 创建统一的字体样式
        unified_style = f"""
            QWidget {{
                font-size: {font_size}px;
                font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
            }}
            QGroupBox {{
                font-size: {font_size}px;
                font-weight: bold;
                border: 2px solid #BDC3C7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                font-size: {font_size}px;
                font-weight: bold;
            }}
            QPushButton {{
                font-size: {font_size}px;
                padding: 4px 8px;
                border: 1px solid #BDC3C7;
                border-radius: 3px;
                background-color: #ECF0F1;
            }}
            QPushButton:hover {{
                background-color: #D5DBDB;
            }}
            QPushButton:pressed {{
                background-color: #BDC3C7;
            }}
            QLabel {{
                font-size: {font_size}px;
            }}
            QCheckBox {{
                font-size: {font_size}px;
                padding: 4px;
            }}
            QSpinBox, QDoubleSpinBox {{
                font-size: {font_size}px;
                padding: 2px;
            }}
            QComboBox {{
                font-size: {font_size}px;
                padding: 2px;
            }}
            QTabWidget::pane {{
                border: 1px solid #BDC3C7;
                border-radius: 3px;
            }}
            QTabBar::tab {{
                font-size: {font_size}px;
                padding: 6px 12px;
                margin-right: 2px;
                border: 1px solid #BDC3C7;
                border-bottom: none;
                border-radius: 3px 3px 0 0;
                background-color: #ECF0F1;
            }}
            QTabBar::tab:selected {{
                background-color: white;
                border-bottom: 1px solid white;
            }}
            QTabBar::tab:hover {{
                background-color: #D5DBDB;
            }}
        """

        # 应用样式到整个控制面板
        self.setStyleSheet(unified_style)

        # 特别处理轨道复选框，保持颜色指示器
        self.update_orbital_checkboxes_style(font_size)

        print(f"已应用统一字体样式: {font_size}px")

    def update_orbital_checkboxes_style(self, font_size):
        """更新轨道复选框样式，保持颜色指示器"""
        for orbital_key, checkbox in self.orbital_checkboxes.items():
            # 获取轨道颜色
            if hasattr(self, 'visualizer') and self.visualizer:
                color = self.visualizer.orbital_colors.get(orbital_key, '#95A5A6')
            else:
                color = '#95A5A6'

            # 设置带颜色指示器的样式
            checkbox_style = f"""
                QCheckBox {{
                    font-size: {font_size}px;
                    padding: 6px 8px;
                    color: #2C3E50;
                    min-height: 28px;
                    background-color: transparent;
                }}
                QCheckBox:hover {{
                    background-color: #ECF0F1;
                    border-radius: 4px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid {color};
                    border-radius: 4px;
                    background-color: white;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {color};
                    border: 2px solid {color};
                }}
                QCheckBox::indicator:hover {{
                    border-width: 3px;
                }}
            """
            checkbox.setStyleSheet(checkbox_style)

    # 删除了测试轨道显示相关方法

    def create_orbital_display_area(self):
        """创建全新的轨道显示控制区域"""
        print("创建新的轨道显示控制区域...")

        # 检查是否已经创建过，避免重复创建
        if hasattr(self, 'orbital_display_widget') and self.orbital_display_widget is not None:
            print("轨道显示控制区域已存在，跳过重复创建")
            return

        # 主容器 - 紧凑设计
        self.orbital_display_widget = QWidget()
        main_layout = QVBoxLayout(self.orbital_display_widget)
        main_layout.setContentsMargins(3, 3, 3, 3)  # 减少边距
        main_layout.setSpacing(3)  # 减少间距

        # 删除重复的信息栏，轨道数量已在上方显示

        # 滚动区域 - 进一步优化高度设置
        self.orbital_scroll_area = QScrollArea()
        self.orbital_scroll_area.setWidgetResizable(True)
        self.orbital_scroll_area.setMinimumHeight(250)  # 增加最小高度，确保轨道完全可见
        self.orbital_scroll_area.setMaximumHeight(400)  # 适当增加最大高度

        # 设置滚动条策略
        self.orbital_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.orbital_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 滚动内容容器
        self.orbital_content_widget = QWidget()
        self.orbital_content_layout = QVBoxLayout(self.orbital_content_widget)
        self.orbital_content_layout.setContentsMargins(6, 6, 6, 6)  # 减少边距
        self.orbital_content_layout.setSpacing(1)  # 轨道间距减少为原来的一半

        # 设置滚动区域样式
        self.orbital_scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #BDC3C7;
                border-radius: 6px;
                background-color: #FAFAFA;
            }
            QScrollBar:vertical {
                border: none;
                background: #ECF0F1;
                width: 14px;
                border-radius: 7px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #BDC3C7;
                border-radius: 7px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #95A5A6;
            }
            QScrollBar::handle:vertical:pressed {
                background: #7F8C8D;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # 设置滚动内容 - 确保正确的父子关系
        self.orbital_scroll_area.setWidget(self.orbital_content_widget)
        main_layout.addWidget(self.orbital_scroll_area)

        # 初始化轨道复选框字典
        self.orbital_checkboxes = {}

        # 强制显示所有widget - 多重保险
        self.orbital_display_widget.setVisible(True)
        self.orbital_display_widget.show()

        self.orbital_scroll_area.setVisible(True)
        self.orbital_scroll_area.show()

        self.orbital_content_widget.setVisible(True)
        self.orbital_content_widget.show()

        # 强制处理事件
        QApplication.processEvents()

        print("轨道显示控制区域创建完成")
        print(f"orbital_display_widget可见性: {self.orbital_display_widget.isVisible()}")
        print(f"orbital_scroll_area可见性: {self.orbital_scroll_area.isVisible()}")
        print(f"orbital_content_widget可见性: {self.orbital_content_widget.isVisible()}")
        print(f"orbital_content_widget父widget: {type(self.orbital_content_widget.parent()).__name__ if self.orbital_content_widget.parent() else 'None'}")

    def on_legend_settings_changed(self):
        """图例设置改变"""
        legend_settings = {
            'fontsize': self.legend_fontsize_spin.value(),
            'fontweight': self.legend_fontweight_combo.currentText(),
            'location': self.legend_location_combo.currentText(),
            'frameon': self.legend_frameon.isChecked(),
            'shadow': self.legend_shadow.isChecked(),
            'fancybox': self.legend_fancybox.isChecked(),
            'framealpha': self.legend_alpha_spin.value(),
            'facecolor': 'white',
            'edgecolor': 'black'
        }

        # 发送图例设置信号
        self.orbital_toggled.emit("LEGEND_SETTINGS", legend_settings)

    def on_fermi_settings_changed(self):
        """费米线设置改变"""
        fermi_alpha = self.fermi_alpha_slider.value() / 100.0
        self.fermi_alpha_label.setText(f"{fermi_alpha:.1f}")

        settings = {
            'fermi_energy': self.fermi_energy_spin.value(),
            'show_fermi_line': self.show_fermi_line.isChecked(),
            'fermi_line_style': self.fermi_style_combo.currentText(),
            'fermi_line_width': self.fermi_width_spin.value(),
            'fermi_line_alpha': fermi_alpha,
            'fermi_window': [self.fermi_window_min.value(), self.fermi_window_max.value()]
        }
        self.settings_changed.emit(settings)

    def on_band_settings_changed(self):
        """能带设置改变"""
        band_alpha = self.band_alpha_slider.value() / 100.0
        self.band_alpha_label.setText(f"{band_alpha:.1f}")

        settings = {
            'show_band_lines': self.show_band_lines.isChecked(),
            'band_line_style': self.band_style_combo.currentText(),
            'band_line_width': self.band_width_spin.value(),
            'band_line_alpha': band_alpha,
        }
        self.settings_changed.emit(settings)

    def update_alpha_label(self):
        """更新透明度标签"""
        point_alpha = self.point_alpha_slider.value() / 100.0
        self.point_alpha_label.setText(f"{point_alpha:.1f}")

    def on_orbital_settings_changed(self):
        """轨道权重设置改变"""
        point_size = self.point_size_spin.value()  # 直接从输入框获取值
        point_alpha = self.point_alpha_slider.value() / 100.0

        # 更新透明度标签
        self.update_alpha_label()

        # 移除颜色方案处理，因为已在顶部导航栏处理
        # [Deprecated 20250827] 设置中移除了 cache_enabled 字段（缓存机制废弃）
        settings = {
            'point_size_factor': point_size,
            'point_alpha': point_alpha,
            'point_min_size': self.min_point_size_spin.value(),
            'point_max_size': self.max_point_size_spin.value(),
            'weight_threshold': self.weight_threshold_spin.value(),
            'max_points_per_orbital': self.max_points_spin.value(),
            'use_multiprocessing': self.use_multiprocessing.isChecked(),
        }
        self.settings_changed.emit(settings)

    def on_figure_settings_changed(self):
        """图形设置改变"""
        grid_alpha = self.grid_alpha_slider.value() / 100.0
        self.grid_alpha_label.setText(f"{grid_alpha:.1f}")

        # 刻度线方向映射
        tick_direction_map = {"向内": "in", "向外": "out", "双向": "inout"}
        tick_direction = tick_direction_map.get(self.tick_direction_combo.currentText(), "in")

        settings = {
            'title': self.title_edit.text(),
            'xlabel': self.xlabel_edit.text(),
            'ylabel': self.ylabel_edit.text(),
            'title_fontsize': self.title_fontsize_spin.value(),
            'label_fontsize': self.label_fontsize_spin.value(),
            'figure_dpi': self.dpi_spin.value(),
            'grid_alpha': grid_alpha,
            # 新增的刻度线设置
            'tick_direction': tick_direction,
            'tick_width': self.tick_width_spin.value(),
            'tick_length': self.tick_length_spin.value(),
            'show_ticks': self.show_ticks.isChecked(),
            # 新增的框线设置
            'frame_top': self.frame_top.isChecked(),
            'frame_bottom': self.frame_bottom.isChecked(),
            'frame_left': self.frame_left.isChecked(),
            'frame_right': self.frame_right.isChecked(),
            'frame_width': self.frame_width_spin.value(),
            # 新增的坐标轴标签设置
            'tick_label_fontsize': self.tick_label_fontsize_spin.value(),
            'tick_label_weight': self.tick_label_weight_combo.currentText(),
            'xlabel_position': self.xlabel_position_combo.currentText(),
            'ylabel_position': self.ylabel_position_combo.currentText(),
            'xlabel_pad': self.xlabel_pad_spin.value(),
            'ylabel_pad': self.ylabel_pad_spin.value()
        }
        self.settings_changed.emit(settings)

    def choose_fermi_color(self):
        """选择费米线颜色"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.fermi_color_btn.setStyleSheet(f"background-color: {color.name()};")
            settings = {'fermi_line_color': color.name()}
            self.settings_changed.emit(settings)

    def choose_band_color(self):
        """选择能带线颜色"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.band_color_btn.setStyleSheet(f"background-color: {color.name()};")
            settings = {'band_line_color': color.name()}
            self.settings_changed.emit(settings)

# ============================================================================
# 5. 日志组件模块
# ============================================================================
# [Deprecated 20250827] LogWidget 已迁移至 gui/log_widget.py（已在顶部导入）
# 为避免命名冲突，这里仅保留一个空的旧类占位符供参考：LegacyLogWidget。
class LegacyLogWidget(QTextEdit):
    pass

# ============================================================================
# 6. 主窗口模块 - 应用程序主界面
# ============================================================================
# [Deprecated 20250827] MainWindow 已迁移至 gui/main_window.py；
# 本文件保留占位类以避免命名冲突与历史引用。
class LegacyMainWindow(QMainWindow):
    """[Deprecated] 旧主窗口占位类。实际主窗口请从 gui.main_window 导入 MainWindow."""
    pass

def check_environment():
    """检查运行环境"""
    print("检查运行环境...")

    # 检查Python版本
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Python版本: {python_version}")

    # 检查Qt环境
    try:
        from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
        print(f"Qt版本: {QT_VERSION_STR}")
        print(f"PyQt5版本: {PYQT_VERSION_STR}")
    except:
        print("无法获取Qt版本信息")

    # 检查matplotlib
    try:
        import matplotlib
        print(f"matplotlib版本: {matplotlib.__version__}")
        print(f"matplotlib后端: {matplotlib.get_backend()}")
    except:
        print("matplotlib检查失败")

    # 检查显示环境
    display = os.environ.get('DISPLAY', '未设置')
    wayland = os.environ.get('WAYLAND_DISPLAY', '未设置')
    print(f"DISPLAY: {display}")
    print(f"WAYLAND_DISPLAY: {wayland}")

def main():
    """主函数"""
    try:
        # 环境检查
        check_environment()

        # 设置Qt环境变量以提高兼容性
        os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', '')
        os.environ.setdefault('QT_PLUGIN_PATH', '')

        # 在创建QApplication之前设置高DPI支持
        try:
            if hasattr(Qt, 'AA_EnableHighDpiScaling'):
                QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
                QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
            print("高DPI支持已预设")
        except Exception as e:
            print(f"高DPI预设失败: {e}")

        # 创建应用程序
        app = QApplication(sys.argv)

        # 设置应用程序信息
        app.setApplicationName("FPLO能带权重可视化工具")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("USTC")

        # 智能样式选择
        available_styles = QApplication.instance().style().objectName()
        print(f"当前样式: {available_styles}")

        # 尝试设置最佳样式
        try:
            app.setStyle('Fusion')  # 现代跨平台样式
            print("使用Fusion样式")
        except:
            print("使用系统默认样式")

        # 高DPI支持已在QApplication创建前设置

        # 设置字体渲染优化
        try:
            app.setAttribute(Qt.AA_Use96Dpi, False)
            print("优化字体渲染")
        except:
            pass

        # 延迟导入以避免循环依赖，并使用别名规避同名占位符
        from gui.main_window import MainWindow as AppMainWindow

        # 创建主窗口
        window = AppMainWindow()

        # 设置窗口属性以提高兼容性
        window.setAttribute(Qt.WA_OpaquePaintEvent, False)
        window.setAttribute(Qt.WA_NoSystemBackground, False)

        window.show()

        # 启动应用程序
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"应用程序运行时发生错误: {str(e)}")
        print("请检查系统环境和依赖库是否正确安装")
        sys.exit(1)

# ============================================================================
# 7. 程序入口
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"GUI启动失败: {str(e)}")
        print("")
        print("可能的解决方案:")
        print("1. 检查系统环境变量")
        print("2. 更新Qt和PyQt5库")
        print("3. 检查依赖库是否正确安装")
        sys.exit(1)

# 仅保留一个入口块（上方 try/except 包装的 main() 调用）。

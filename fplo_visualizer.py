#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPLO能带权重可视化程序 - 最终版本
功能：
1. 识别+bweights文件信息（文件大小、行数、体系信息等）
2. 自动识别元素和轨道类型，动态分配颜色
3. 绘制完整能量范围的能带图和轨道权重图
4. 生成多高质量图片（1张纯能带图 + 1张权重汇总图 + 轨道分图）
5. 智能文件管理和详细信息输出

作者: zhujiawen@ustc.mail.edu.cn
版本: Final 1.0
"""

from orbital_data import (check_cancelled, parse_orbital_labels, parse_orbital_columns,
                          read_weight_header, read_weight_data, prepare_weight_points, weight_point_sizes)

import numpy as np
from weight_plot import add_weight_scale
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import re
import os
import warnings
warnings.filterwarnings('ignore')

# 设置matplotlib
import matplotlib
matplotlib.use('Agg')

class FPLOVisualizer:
    """FPLO能带权重可视化器 - 最终版本"""
    
    def __init__(self, filename='+bweights', *, cancel_check=None, configure_plot=True):
        """初始化可视化器"""
        self._cancel_check = cancel_check
        check_cancelled(self)
        self.filename = filename
        self.file_info = {}
        self.header_info = {}
        self.orbital_info = {}
        self.elements = set()
        self.orbital_types = set()
        
        # 数据容器
        self.k_points = None
        self.band_energies = None
        self.band_weights = None
        self.num_bands = 0
        self.output_folder = None
        
        # 25种精选颜色调色板
        self.color_palette = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2',
            '#A3E4D7', '#F9E79F', '#D5A6BD', '#AED6F1', '#A9DFBF',
            '#FAD7A0', '#E8DAEF', '#D1F2EB', '#FCF3CF', '#FADBD8'
        ]
        self.orbital_colors = {}
        
        # 设置matplotlib
        if configure_plot:
            self._setup_matplotlib()
        
    def _setup_matplotlib(self):
        """设置matplotlib字体和参数"""
        # 检查Times New Roman字体
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        times_fonts = ['Times New Roman', 'Times', 'serif']
        
        for font in times_fonts:
            if font in available_fonts:
                plt.rcParams['font.family'] = font
                print(f"使用字体: {font}")
                break
        else:
            plt.rcParams['font.family'] = 'DejaVu Sans'
            print("使用默认英文字体: DejaVu Sans")
        
        plt.rcParams['figure.dpi'] = 200
        plt.rcParams['savefig.dpi'] = 200
        plt.rcParams['axes.unicode_minus'] = False
        
    def analyze_file_info(self):
        """分析文件信息"""
        print("=== 分析文件信息 ===")
        
        # 文件基本信息
        file_size = os.path.getsize(self.filename)
        
        # 计算行数和数据行数
        total_lines = 0
        data_lines = 0
        comment_lines = 0
        
        with open(self.filename, 'r') as f:
            for line in f:
                check_cancelled(self)
                total_lines += 1
                line = line.strip()
                if line.startswith('#'):
                    comment_lines += 1
                elif line:
                    data_lines += 1
        
        self.file_info = {
            'filename': self.filename,
            'file_size_bytes': file_size,
            'file_size_mb': file_size / (1024 * 1024),
            'total_lines': total_lines,
            'data_lines': data_lines,
            'comment_lines': comment_lines
        }
        
        print(f"文件名: {self.file_info['filename']}")
        print(f"文件大小: {self.file_info['file_size_mb']:.2f} MB ({self.file_info['file_size_bytes']:,} 字节)")
        print(f"总行数: {self.file_info['total_lines']:,}")
        print(f"数据行数: {self.file_info['data_lines']:,}")
        print(f"注释行数: {self.file_info['comment_lines']}")
        
        return self.file_info
        
    def parse_header_and_system(self):
        """Validate the declared schema before replacing existing metadata."""
        header, columns, groups = read_weight_header(self.filename)
        self.header_info = header
        self.orbital_columns = columns
        self.orbital_info = groups
        self.elements = {column['element'] for column in columns}
        self.orbital_types = {column['shell'] for column in columns}
        self._group_weight_cache = {}
        self._assign_colors()
        print(f"原始费米能级: {header['original_fermi_energy']:.6f}; 输入按相对 EF 的 eV 读取，不额外平移")
        print(f"完整数据: {header['num_kpoints']} k点, {header['num_bands']} 能带, {len(groups)} 个原子壳层")
        

    def _parse_orbital_labels(self, orbital_text):
        """Replace groups atomically so repeated header parsing is idempotent."""
        columns = parse_orbital_columns(orbital_text)
        groups = parse_orbital_labels(orbital_text)
        self.orbital_columns = columns
        self.orbital_info = groups
        self.elements = {column['element'] for column in columns}
        self.orbital_types = {key.split('_', 1)[1] for key in groups}
        self._group_weight_cache = {}
                        
    def _assign_colors(self):
        """动态分配颜色"""
        print("\n=== 颜色分配信息 ===")
        
        color_index = 0
        elements = sorted({key.split('_', 1)[0] for key in self.orbital_info})
        orbital_types = sorted(self.orbital_types)
        
        for element in elements:
            for orbital_type in orbital_types:
                orbital_key = f"{element}_{orbital_type}"
                if orbital_key in self.orbital_info:
                    color = self.color_palette[color_index % len(self.color_palette)]
                    self.orbital_colors[orbital_key] = color
                    print(f"  {orbital_key}: {color}")
                    color_index += 1
        
        print(f"总计分配颜色: {len(self.orbital_colors)} 种")
        
    def read_and_parse_data(self, max_kpoints=None):
        """Load complete immutable arrays; max_kpoints only controls display."""
        if max_kpoints is not None and (isinstance(max_kpoints, bool) or
                not isinstance(max_kpoints, (int, np.integer)) or max_kpoints < 1):
            raise ValueError('Display k-point limit must be a positive integer or None')
        k_points, energies, weights = read_weight_data(
            self.filename, self.header_info, self.orbital_columns, owner=self)
        check_cancelled(self)
        self.k_points = k_points
        self.band_energies = energies
        self.band_weights = weights
        self.num_kpoints, self.num_bands = energies.shape
        self.plot_max_kpoints = max_kpoints
        self._group_weight_cache = {}
        self._group_weight_source = None
        self.validation_warnings = []
        if np.any(weights < 0):
            self.validation_warnings.append('输入包含负权重；保留原值，正阈值散点不显示负值。')
        print(f"完整数据已校验: {self.num_kpoints} k点, {self.num_bands} 能带；仅显示时抽样")
        return float(energies.min()), float(energies.max())
        

    def create_output_folder(self):
        """创建输出文件夹"""
        elements_str = "_".join(sorted(self.elements))
        self.output_folder = f"bweight_{elements_str}"

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            print(f"\n创建输出文件夹: {self.output_folder}")
        else:
            print(f"\n使用现有文件夹: {self.output_folder}")

        return self.output_folder

    def _plot_dense_orbital_weight_points(self, ax, k_points, energies, weights, color, min_weight=0.005):
        """Plot original samples using the shared raw-weight area scale."""
        k, energy, weight = prepare_weight_points(
            k_points, energies, weights, min_weight, getattr(self, 'plot_max_kpoints', None))
        if len(weight):
            add_weight_scale(ax)
            return ax.scatter(k, energy, s=weight_point_sizes(weight), c=color,
                              alpha=0.7, edgecolors='none', zorder=2)


    def _find_continuous_segments(self, k_points, max_gap=0.05):
        """找到k点的连续段"""
        if len(k_points) <= 1:
            return [np.array([0])]

        # 计算相邻k点的差值
        k_diffs = np.diff(k_points)

        # 找到不连续的点
        breaks = np.where(k_diffs > max_gap)[0]

        # 构建段索引
        segments = []
        start = 0

        for b in breaks:
            segments.append(np.arange(start, b+1))
            start = b+1

        # 添加最后一段
        if start < len(k_points):
            segments.append(np.arange(start, len(k_points)))

        return segments

    def _calculate_dynamic_figsize(self, energy_range, base_width=14, base_height=10,
                                  min_width=12, max_width=20, min_height=8, max_height=16):
        """根据能量范围动态计算图片尺寸"""
        energy_span = energy_range[1] - energy_range[0]

        # 基准能量范围 (20 eV)
        base_energy_span = 20.0

        # 计算缩放因子
        scale_factor = energy_span / base_energy_span

        # 应用缩放，但限制在合理范围内
        dynamic_width = base_width * (0.8 + 0.4 * scale_factor)  # 宽度变化较小
        dynamic_height = base_height * (0.7 + 0.6 * scale_factor)  # 高度变化较大

        # 限制在最小和最大值之间
        dynamic_width = max(min_width, min(max_width, dynamic_width))
        dynamic_height = max(min_height, min(max_height, dynamic_height))

        print(f"能量范围: {energy_span:.1f} eV, 图片尺寸: {dynamic_width:.1f} x {dynamic_height:.1f} 英寸")

        return (dynamic_width, dynamic_height)

    def plot_pure_band_structure(self, figsize=None, dpi=300):
        """绘制纯能带结构图 - 使用完整能量范围"""
        print("\n=== 绘制纯能带结构图 ===")

        # 使用完整能量范围
        all_energies = self.band_energies.flatten()
        energy_range = (np.min(all_energies), np.max(all_energies))

        # 动态计算图片尺寸
        if figsize is None:
            figsize = self._calculate_dynamic_figsize(energy_range, base_width=14, base_height=10)

        fig, ax = plt.subplots(figsize=figsize)

        # 绘制黑色能带骨架
        band_count = 0
        for band_idx in range(self.num_bands):
            band_energies = self.band_energies[:, band_idx]
            ax.plot(self.k_points, band_energies, 'k-', linewidth=1.0, alpha=0.9, zorder=1)
            band_count += 1

        # 添加费米能级
        if 'fermi_energy' in self.header_info:
            ax.axhline(y=self.header_info['fermi_energy'], color='red',
                      linestyle='--', alpha=0.9, linewidth=2.5, zorder=2, label='Fermi level')

        # 设置图形属性
        ax.set_xlabel('k-point path', fontsize=14, fontweight='bold')
        ax.set_ylabel('Energy (eV)', fontsize=14, fontweight='bold')
        ax.set_title('FPLO Band Structure (Complete Energy Range)', fontsize=16, fontweight='bold', pad=20)
        ax.set_ylim(energy_range)
        ax.grid(True, alpha=0.3, zorder=0)

        # 添加信息文本
        info_text = (f"Bands: {band_count}\n"
                    f"Energy range: {energy_range[0]:.1f} ~ {energy_range[1]:.1f} eV\n"
                    f"Fermi level: 0.0 eV (reference)\n"
                    f"k-points: {len(self.k_points)}\n"
                    f"Elements: {', '.join(sorted(self.elements))}")

        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=12,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # 图例
        if 'fermi_energy' in self.header_info:
            ax.legend(loc='upper right', fontsize=12, frameon=True, fancybox=True, shadow=True)

        plt.tight_layout()
        output_path = os.path.join(self.output_folder, '01_band_structure.png')
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        print(f"保存: {output_path}")
        print(f"能量范围: {energy_range[0]:.3f} ~ {energy_range[1]:.3f} eV")
        return output_path

    def plot_weight_summary(self, figsize=None, dpi=300):
        """绘制权重汇总图 - 使用完整能量范围"""
        print("\n=== 绘制权重汇总图 ===")

        # 使用完整能量范围
        all_energies = self.band_energies.flatten()
        energy_range = (np.min(all_energies), np.max(all_energies))

        # 动态计算图片尺寸
        if figsize is None:
            figsize = self._calculate_dynamic_figsize(energy_range, base_width=16, base_height=12)

        fig, ax = plt.subplots(figsize=figsize)

        # 绘制黑色能带骨架
        for band_idx in range(self.num_bands):
            band_energies = self.band_energies[:, band_idx]
            ax.plot(self.k_points, band_energies, 'k-', linewidth=0.8, alpha=0.7, zorder=1)

        # 绘制所有轨道权重
        max_weight = 0
        min_weight = float('inf')
        legend_added = set()

        for orbital_key, indices in self.orbital_info.items():
            if not indices:
                continue

            color = self.orbital_colors.get(orbital_key, '#95A5A6')
            has_visible_weight = False

            for band_idx in range(self.num_bands):
                band_energies = self.band_energies[:, band_idx]
                orbital_weights = np.sum(self.band_weights[:, band_idx, :][:, indices], axis=1)

                # 权重阈值
                mask = orbital_weights > 0.01

                if np.any(mask):
                    has_visible_weight = True
                    current_max = np.max(orbital_weights[mask])
                    max_weight = max(max_weight, current_max)
                    min_weight = min(min_weight, np.min(orbital_weights[mask]))

                    k_filtered = self.k_points[mask]
                    e_filtered = band_energies[mask]
                    w_filtered = orbital_weights[mask]

                    # 改进的散点绘制方法 - 密集插值点
                    self._plot_dense_orbital_weight_points(
                        ax, k_filtered, e_filtered, w_filtered, color
                    )

            # 添加图例
            if has_visible_weight and orbital_key not in legend_added:
                ax.plot([], [], color=color, linestyle='-', linewidth=3,
                       alpha=0.8, label=orbital_key.replace('_', ' '))
                legend_added.add(orbital_key)

        # 添加费米能级
        if 'fermi_energy' in self.header_info:
            ax.axhline(y=self.header_info['fermi_energy'], color='red',
                      linestyle='--', alpha=0.9, linewidth=2.5, zorder=3, label='Fermi level')

        # 设置图形属性
        ax.set_xlabel('k-point path', fontsize=14, fontweight='bold')
        ax.set_ylabel('Energy (eV)', fontsize=14, fontweight='bold')
        ax.set_title('FPLO Band Structure with Orbital Weight Distribution (Complete Range)',
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_ylim(energy_range)
        ax.grid(True, alpha=0.3, zorder=0)

        # 添加信息文本
        elements_str = ", ".join(sorted(self.elements))
        orbitals_str = ", ".join(sorted(self.orbital_types))
        weight_range_str = f"{min_weight:.3f} ~ {max_weight:.3f}" if max_weight > 0 else "N/A"

        info_text = (f"Elements: {elements_str}\n"
                    f"Orbitals: {orbitals_str}\n"
                    f"Energy range: {energy_range[0]:.1f} ~ {energy_range[1]:.1f} eV\n"
                    f"Weight range: {weight_range_str}")

        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=11,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

        # 创建有序图例
        handles, labels = ax.get_legend_handles_labels()

        # 按顺序排列：费米能级 -> 轨道（按字母顺序）
        ordered_items = []

        # 费米能级
        for handle, label in zip(handles, labels):
            if label == 'Fermi level':
                ordered_items.append((handle, label))
                break

        # 轨道（按字母顺序）
        orbital_items = [(handle, label) for handle, label in zip(handles, labels)
                        if label != 'Fermi level']
        orbital_items.sort(key=lambda x: x[1])
        ordered_items.extend(orbital_items)

        if ordered_items:
            ordered_handles, ordered_labels = zip(*ordered_items)
            legend = ax.legend(ordered_handles, ordered_labels,
                              bbox_to_anchor=(1.02, 1), loc='upper left',
                              fontsize=11, frameon=True, fancybox=True, shadow=True)
            legend.get_frame().set_alpha(0.9)

        plt.tight_layout()
        output_path = os.path.join(self.output_folder, '02_weight_summary.png')
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        print(f"保存: {output_path}")
        print(f"权重范围: {weight_range_str}")
        print(f"能量范围: {energy_range[0]:.3f} ~ {energy_range[1]:.3f} eV")
        return output_path, weight_range_str

    def plot_individual_orbitals(self, figsize=None, dpi=200):
        """绘制各轨道分图 - 使用完整能量范围"""
        print("\n=== 绘制各轨道分图 ===")

        # 使用完整能量范围
        all_energies = self.band_energies.flatten()
        energy_range = (np.min(all_energies), np.max(all_energies))

        # 动态计算图片尺寸
        if figsize is None:
            figsize = self._calculate_dynamic_figsize(energy_range, base_width=12, base_height=9)

        elements = sorted({key.split('_', 1)[0] for key in self.orbital_info})
        orbital_types = sorted(self.orbital_types)

        figure_count = 3
        output_paths = []

        for element in elements:
            for orbital_type in orbital_types:
                orbital_key = f"{element}_{orbital_type}"

                if orbital_key not in self.orbital_info:
                    continue

                indices = self.orbital_info[orbital_key]
                if not indices:
                    continue

                fig, ax = plt.subplots(figsize=figsize)

                # 绘制黑色能带骨架
                for band_idx in range(self.num_bands):
                    band_energies = self.band_energies[:, band_idx]
                    ax.plot(self.k_points, band_energies, 'k-',
                           linewidth=0.6, alpha=0.5, zorder=1)

                # 绘制该轨道的权重
                color = self.orbital_colors.get(orbital_key, '#95A5A6')
                max_weight = 0
                min_weight = float('inf')
                has_data = False

                for band_idx in range(self.num_bands):
                    band_energies = self.band_energies[:, band_idx]
                    orbital_weights = np.sum(self.band_weights[:, band_idx, :][:, indices], axis=1)

                    # 更低的阈值用于单轨道图
                    mask = orbital_weights > 0.005

                    if np.any(mask):
                        has_data = True
                        current_max = np.max(orbital_weights[mask])
                        max_weight = max(max_weight, current_max)
                        min_weight = min(min_weight, np.min(orbital_weights[mask]))

                        k_filtered = self.k_points[mask]
                        e_filtered = band_energies[mask]
                        w_filtered = orbital_weights[mask]

                        # 使用密集散点绘制方法
                        self._plot_dense_orbital_weight_points(
                            ax, k_filtered, e_filtered, w_filtered, color
                        )

                # 添加费米能级
                if 'fermi_energy' in self.header_info:
                    ax.axhline(y=self.header_info['fermi_energy'], color='red',
                              linestyle='--', alpha=0.8, linewidth=2, zorder=3)

                # 设置图形属性
                ax.set_xlabel('k-point path', fontsize=12, fontweight='bold')
                ax.set_ylabel('Energy (eV)', fontsize=12, fontweight='bold')
                ax.set_title(f'{element} {orbital_type} Orbital Weight Distribution (Complete Range)',
                            fontsize=14, fontweight='bold', pad=15)
                ax.set_ylim(energy_range)
                ax.grid(True, alpha=0.3, zorder=0)

                # 添加信息文本
                if has_data:
                    weight_range_str = f"{min_weight:.4f} ~ {max_weight:.4f}"
                    info_text = (f"Element: {element}\n"
                                f"Orbital: {orbital_type}\n"
                                f"Energy range: {energy_range[0]:.1f} ~ {energy_range[1]:.1f} eV\n"
                                f"Weight range: {weight_range_str}")
                else:
                    info_text = (f"Element: {element}\n"
                                f"Orbital: {orbital_type}\n"
                                f"Energy range: {energy_range[0]:.1f} ~ {energy_range[1]:.1f} eV\n"
                                f"No significant weight")

                ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

                # 添加图例
                legend_items = []
                legend_items.append((plt.Line2D([0], [0], color='k', linewidth=0.6, alpha=0.5), 'Band structure'))
                legend_items.append((plt.Line2D([0], [0], color='red', linestyle='--', linewidth=2, alpha=0.8), 'Fermi level'))
                if has_data:
                    legend_items.append((plt.Line2D([0], [0], color=color, linewidth=3, alpha=0.9), f'{element} {orbital_type}'))

                handles, labels = zip(*legend_items)
                ax.legend(handles, labels, loc='upper right', fontsize=10,
                         frameon=True, fancybox=True, shadow=True)

                plt.tight_layout()
                output_path = os.path.join(self.output_folder, f'{figure_count:02d}_{element}_{orbital_type}.png')
                plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
                plt.close()

                print(f"保存: {output_path}")
                if has_data:
                    print(f"  权重范围: {weight_range_str}")
                else:
                    print(f"  无显著权重")

                output_paths.append(output_path)
                figure_count += 1

        return output_paths

    def run_complete_analysis(self, max_kpoints=150):
        """运行完整的FPLO分析"""
        print("=" * 60)
        print("FPLO能带权重可视化分析 - 最终版本")
        print("=" * 60)

        # 1. 分析文件信息
        self.analyze_file_info()

        # 2. 解析头部和体系信息
        self.parse_header_and_system()

        # 3. 读取和解析数据
        energy_min, energy_max = self.read_and_parse_data(max_kpoints=max_kpoints)

        # 4. 创建输出文件夹
        self.create_output_folder()

        # 5. 绘制所有图形
        print("\n" + "=" * 60)
        print("开始绘制图形")
        print("=" * 60)

        # 纯能带结构图
        band_path = self.plot_pure_band_structure()

        # 权重汇总图
        summary_path, weight_range = self.plot_weight_summary()

        # 各轨道分图
        orbital_paths = self.plot_individual_orbitals()

        # 6. 输出完整结果摘要
        self._print_final_summary(band_path, summary_path, orbital_paths, weight_range, energy_min, energy_max)

        return {
            'file_info': self.file_info,
            'system_info': {
                'elements': sorted(self.elements),
                'orbital_types': sorted(self.orbital_types),
                'orbital_colors': self.orbital_colors,
                'num_bands': self.num_bands,
                'fermi_energy': self.header_info.get('fermi_energy'),
                'energy_range': (energy_min, energy_max)
            },
            'output_folder': self.output_folder,
            'files': {
                'band_structure': band_path,
                'weight_summary': summary_path,
                'orbital_plots': orbital_paths
            },
            'weight_range': weight_range
        }

    def _print_final_summary(self, band_path, summary_path, orbital_paths, weight_range, energy_min, energy_max):
        """打印最终结果摘要"""
        print("\n" + "=" * 60)
        print("分析完成 - 结果摘要")
        print("=" * 60)

        print(f"\n输出文件夹: {self.output_folder}")
        print(f"文件信息: {self.file_info['file_size_mb']:.2f} MB, {self.file_info['data_lines']:,} 数据行")
        print(f"体系信息: {len(self.elements)} 元素, {len(self.orbital_types)} 轨道类型")
        print(f"能量范围: {energy_min:.3f} ~ {energy_max:.3f} eV (完整范围)")
        print(f"权重范围: {weight_range}")

        print(f"\n生成图片:")
        print(f"  1. {os.path.basename(band_path)} - 纯能带结构图 (300 DPI)")
        print(f"  2. {os.path.basename(summary_path)} - 权重汇总图 (300 DPI)")

        for i, path in enumerate(orbital_paths, 3):
            filename = os.path.basename(path)
            element_orbital = filename.replace('.png', '').split('_', 1)[1]
            print(f"  {i}. {filename} - {element_orbital} 轨道分图 (200 DPI)")

        print(f"\n总计生成: {2 + len(orbital_paths)} 张图片")

        print(f"\n颜色分配:")
        for orbital_key, color in self.orbital_colors.items():
            element, orbital = orbital_key.split('_')
            print(f"  {element} {orbital}: {color}")

        print(f"\n所有图片使用完整能量范围: {energy_min:.1f} ~ {energy_max:.1f} eV")
        print("黑色能带骨架 + 彩色轨道权重分布")
        print("智能文件管理和详细信息标注")


def main():
    """主程序入口"""
    import sys

    # 检查文件是否存在
    filename = '+bweights'
    if not os.path.exists(filename):
        print(f"错误: 找不到文件 '{filename}'")
        print("请确保+bweights文件在当前目录下")
        sys.exit(1)

    try:
        # 创建可视化器并运行完整分析
        visualizer = FPLOVisualizer(filename)
        results = visualizer.run_complete_analysis(max_kpoints=150)

        print(f"\nFPLO能带可视化分析成功完成！")
        print(f"查看输出文件夹: {results['output_folder']}")

    except Exception as e:
        print(f"分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

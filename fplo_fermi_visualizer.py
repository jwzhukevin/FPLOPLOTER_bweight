#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPLO费米面附近能带可视化程序 - Wannier投影专用版本
专门关注费米面附近的能带结构，用于轨道wannier投影分析

功能：
1. 智能识别费米面附近的重要能带
2. 自动选择合适的能量窗口
3. 突出显示价带顶和导带底
4. 优化轨道权重显示，便于wannier投影分析
5. 生成适合科研分析的高质量图片

版本: Fermi-Focused 1.0
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import re
import os
import warnings
warnings.filterwarnings('ignore')

# 设置matplotlib
import matplotlib
matplotlib.use('Agg')

class FPLOFermiVisualizer:
    """FPLO费米面附近能带可视化器 - Wannier投影专用"""
    
    def __init__(self, filename='+bweights'):
        """初始化可视化器"""
        self.filename = filename
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
        
        # 费米面分析相关
        self.fermi_energy = 0
        self.valence_bands = []
        self.conduction_bands = []
        self.energy_window = None
        self.user_fermi_window = None  # 用户设置的费米窗口
        self.default_fermi_window = 4.0  # 默认费米窗口大小 (eV)
        
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
        self._setup_matplotlib()

        # 读取和解析数据
        print(f"正在加载费米专注可视化器数据: {filename}")

        # 先解析头部和体系信息
        self.parse_header_and_system()

        # 读取和解析数据（这会调用_analyze_fermi_region）
        self.read_and_parse_data()

        print(f"费米专注可视化器初始化完成")
        
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
        
    def parse_header_and_system(self):
        """解析头部和体系信息"""
        print("=== 解析体系信息 ===")
        
        with open(self.filename, 'r') as f:
            # 解析第一行头部信息
            header_line = f.readline().strip()
            if header_line.startswith('#'):
                parts = header_line.split()
                self.header_info = {
                    'num_bands': int(parts[1]),
                    'original_fermi_energy': float(parts[2]),  # 原始费米能级（仅作记录）
                    'fermi_energy': 0.0,  # 实际费米能级设为0（因为数据已减去费米能）
                    'num_kpoints': int(parts[3]),
                    'num_orbitals': int(parts[4])
                }
                self.fermi_energy = 0.0  # 费米能级设为0
                print(f"原始费米能级: {self.header_info['original_fermi_energy']:.6f} eV (已从数据中减去)")
                print(f"当前费米能级: {self.fermi_energy:.6f} eV (数据参考点)")

            # 解析第二行轨道标签
            orbital_line = f.readline().strip()
            if orbital_line.startswith('#'):
                self._parse_orbital_labels(orbital_line[1:].strip())
        
        print(f"费米能级: {self.fermi_energy:.6f} eV (数据参考点)")
        print(f"能带数量: {self.header_info['num_bands']}")
        print(f"识别到元素: {sorted(self.elements)}")
        print(f"识别到轨道类型: {sorted(self.orbital_types)}")
        
        # 动态分配颜色
        self._assign_colors()
        
    def _parse_orbital_labels(self, orbital_text):
        """解析轨道标签 - 处理元素名后有空格的格式"""
        orbital_parts = orbital_text.split()

        # 跳过前两列 (k点和能量标签)
        if len(orbital_parts) >= 2:
            # 检查是否是标准的k点和能量标签
            if orbital_parts[0] in ['#', 'ik'] or 'e(k' in orbital_parts[1]:
                print(f"跳过前两列标签: {orbital_parts[0]} {orbital_parts[1]}")
                orbital_parts = orbital_parts[2:]  # 从第三列开始

        print(f"解析轨道标签: {len(orbital_parts)} 个部分")

        orbital_index = 0
        i = 0

        while i < len(orbital_parts):
            current_part = orbital_parts[i]

            # 检查当前部分是否是元素名（单字母或双字母）
            element_match = re.match(r'^([A-Z][a-z]?)$', current_part)

            if element_match and i + 1 < len(orbital_parts):
                element = element_match.group(1)
                next_part = orbital_parts[i + 1]

                # 检查下一部分是否是轨道信息 (数字)轨道字母+量子数
                orbital_match = re.search(r'\((\d+)\)(\d*)([spdf])(\d+/\d+[+-]\d+/\d+)', next_part)

                if orbital_match:
                    orbital_type = orbital_match.group(3)

                    self.elements.add(element)
                    self.orbital_types.add(orbital_type)

                    orbital_key = f"{element}_{orbital_type}"
                    if orbital_key not in self.orbital_info:
                        self.orbital_info[orbital_key] = []

                    self.orbital_info[orbital_key].append(orbital_index)
                    orbital_index += 1

                    # 调试信息 (可选，生产环境可注释掉)
                    # print(f"    解析: {element} {next_part} → 元素: {element}, 轨道: {orbital_type}")

                    i += 2  # 跳过已处理的两个部分
                    continue
                else:
                    print(f"    警告: 元素 {element} 后的轨道信息格式不正确: {next_part}")

            # 如果不是元素+轨道的组合，检查是否是连在一起的格式
            elif '(' in current_part and ')' in current_part:
                # 处理没有空格分隔的格式，如 "V(004)4p3/2-3/2"
                element_match = re.search(r'^([A-Z][a-z]?)\(', current_part)
                if element_match:
                    element = element_match.group(1)

                    orbital_match = re.search(r'\)(\d*)([spdf])\d+/\d+[+-]\d+/\d+', current_part)
                    if orbital_match:
                        orbital_type = orbital_match.group(2)

                        self.elements.add(element)
                        self.orbital_types.add(orbital_type)

                        orbital_key = f"{element}_{orbital_type}"
                        if orbital_key not in self.orbital_info:
                            self.orbital_info[orbital_key] = []

                        self.orbital_info[orbital_key].append(orbital_index)
                        orbital_index += 1

                        # print(f"    解析: {current_part} → 元素: {element}, 轨道: {orbital_type}")
                    else:
                        print(f"    警告: 无法解析轨道类型: {current_part}")
                else:
                    print(f"    警告: 无法解析元素: {current_part}")
            else:
                # 跳过不符合格式的部分
                if current_part.strip():
                    print(f"    跳过: {current_part} (格式不符)")

            i += 1
                        
    def _assign_colors(self):
        """动态分配颜色"""
        color_index = 0
        elements = sorted(self.elements)
        orbital_types = sorted(self.orbital_types)
        
        for element in elements:
            for orbital_type in orbital_types:
                orbital_key = f"{element}_{orbital_type}"
                if orbital_key in self.orbital_info:
                    color = self.color_palette[color_index % len(self.color_palette)]
                    self.orbital_colors[orbital_key] = color
                    color_index += 1
        
        print(f"颜色分配完成，共分配 {len(self.orbital_colors)} 种颜色")
        
    def read_and_parse_data(self, max_kpoints=None):
        """读取和解析数据"""
        print("\n=== 读取和解析数据 ===")
        
        # 读取所有数据
        all_data = []
        with open(self.filename, 'r') as f:
            f.readline()  # 跳过头部
            f.readline()
            
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 3:
                        k_point = float(parts[0])
                        energy = float(parts[1])
                        weights = [float(w) for w in parts[2:]]
                        all_data.append([k_point, energy] + weights)
        
        all_data = np.array(all_data)
        print(f"读取数据点: {len(all_data):,}")
        
        # 识别能带数量
        num_bands = 0
        for i, row in enumerate(all_data):
            if abs(row[0]) < 1e-6:  # k点接近0
                num_bands += 1
            else:
                break
        
        print(f"识别能带数量: {num_bands}")
        
        # 计算k点数量并应用采样
        total_points = len(all_data)
        num_kpoints = total_points // num_bands
        print(f"每条能带k点数: {num_kpoints}")
        
        if max_kpoints and num_kpoints > max_kpoints:
            k_sample_step = num_kpoints // max_kpoints
            print(f"应用k点采样，步长: {k_sample_step}")
        else:
            k_sample_step = 1
        
        # 重新组织数据
        sampled_kpoints = list(range(0, num_kpoints, k_sample_step))
        self.k_points = []
        self.band_energies = []
        self.band_weights = []
        
        for k_idx in sampled_kpoints:
            energies_at_k = []
            weights_at_k = []
            
            for band_idx in range(num_bands):
                data_idx = k_idx * num_bands + band_idx
                if data_idx < len(all_data):
                    row = all_data[data_idx]
                    k_point = row[0]
                    energy = row[1]
                    weights = row[2:]
                    
                    energies_at_k.append(energy)
                    weights_at_k.append(weights)
                    
                    if band_idx == 0:
                        self.k_points.append(k_point)
            
            self.band_energies.append(energies_at_k)
            self.band_weights.append(weights_at_k)
        
        self.k_points = np.array(self.k_points)
        self.band_energies = np.array(self.band_energies)
        self.band_weights = np.array(self.band_weights)
        self.num_bands = num_bands
        self.num_kpoints = len(self.k_points)
        self.weights_data = self.band_weights  # 为了兼容新函数

        print(f"数据重组完成: {self.num_kpoints} k点, {self.num_bands} 能带")
        
        return self._analyze_fermi_region()
        
    def _analyze_fermi_region(self):
        """分析费米面附近区域"""
        print("\n=== 费米面区域分析 ===")

        # 找到所有能带在所有k点的能量
        all_energies = self.band_energies.flatten()

        # 分析价带和导带 (费米能级为0 eV)
        valence_energies = all_energies[all_energies <= 0.0]  # 费米能级以下
        conduction_energies = all_energies[all_energies > 0.0]  # 费米能级以上

        if len(valence_energies) > 0:
            vbm = np.max(valence_energies)  # 价带顶
            print(f"价带顶 (VBM): {vbm:.6f} eV (相对费米能级)")
        else:
            vbm = 0.0
            print("未找到价带 (所有能带都在费米能级以上)")

        if len(conduction_energies) > 0:
            cbm = np.min(conduction_energies)  # 导带底
            print(f"导带底 (CBM): {cbm:.6f} eV (相对费米能级)")
        else:
            cbm = 0.0
            print("未找到导带 (所有能带都在费米能级以下)")

        # 计算带隙
        band_gap = cbm - vbm
        print(f"带隙: {band_gap:.6f} eV")

        # 智能选择能量窗口 - 新的逻辑
        energy_window = self._find_optimal_energy_window(vbm, cbm, band_gap)
        self.energy_window = energy_window

        # 识别费米面附近的重要能带
        self._identify_important_bands()

        return energy_window, vbm, cbm, band_gap

    def _find_optimal_energy_window(self, vbm, cbm, band_gap):
        """智能寻找最优能量窗口 - 改进版本"""
        print("\n=== 改进的智能能量窗口选择 ===")

        # 如果用户设置了费米窗口，优先使用用户设置
        if self.user_fermi_window is not None:
            print(f"使用用户设置的费米窗口: {self.user_fermi_window:.1f} eV")
            fermi_half_window = self.user_fermi_window / 2
            energy_window = (
                self.fermi_energy - fermi_half_window,
                self.fermi_energy + fermi_half_window
            )

            window_size = energy_window[1] - energy_window[0]
            print(f"用户费米窗口: {energy_window[0]:.3f} ~ {energy_window[1]:.3f} eV")
            print(f"窗口大小: {window_size:.3f} eV")

            return energy_window

        # 分类材料类型
        material_type = self._classify_material_type(vbm, cbm, band_gap)
        print(f"材料类型识别: {material_type}")

        # 计算多维度特征
        features = self._calculate_multi_dimensional_features()

        # 使用改进的算法选择窗口
        energy_window = self._smart_window_selection(features, material_type, vbm, cbm, band_gap)

        window_size = energy_window[1] - energy_window[0]
        print(f"智能自动窗口: {energy_window[0]:.3f} ~ {energy_window[1]:.3f} eV")
        print(f"窗口大小: {window_size:.3f} eV")

        return energy_window

    def set_fermi_window(self, window_size):
        """
        设置费米窗口大小

        Args:
            window_size (float): 费米窗口大小 (eV)，以费米能级为中心的对称窗口
        """
        print(f"\n=== 设置用户费米窗口 ===")
        print(f"费米窗口大小: ±{window_size/2:.1f} eV (总共 {window_size:.1f} eV)")

        self.user_fermi_window = window_size

        # 重新计算能量窗口
        fermi_half_window = window_size / 2
        self.energy_window = (
            self.fermi_energy - fermi_half_window,
            self.fermi_energy + fermi_half_window
        )

        print(f"新的能量窗口: {self.energy_window[0]:.3f} ~ {self.energy_window[1]:.3f} eV")

        # 重新识别重要能带
        self._identify_important_bands()

        return self.energy_window

    def get_fermi_window_info(self):
        """
        获取费米窗口信息

        Returns:
            dict: 费米窗口相关信息
        """
        if self.energy_window is None:
            return None

        window_size = self.energy_window[1] - self.energy_window[0]
        fermi_center = (self.energy_window[0] + self.energy_window[1]) / 2

        return {
            'window_size': window_size,
            'fermi_center': fermi_center,
            'energy_range': self.energy_window,
            'is_user_set': self.user_fermi_window is not None,
            'user_window_size': self.user_fermi_window
        }

    def _classify_material_type(self, vbm, cbm, band_gap):
        """分类材料类型"""
        # 检查是否有能带跨越费米面
        fermi_crossing_bands = []
        for band_idx in range(self.num_bands):
            band_energies = self.band_energies[:, band_idx]
            if np.min(band_energies) <= self.fermi_energy <= np.max(band_energies):
                fermi_crossing_bands.append(band_idx)

        if len(fermi_crossing_bands) > 0:
            return "metal"  # 有能带跨越费米面，是金属

        # 根据带隙大小分类
        if band_gap < 0.1:
            return "metal"  # 极小带隙，视为金属
        elif band_gap < 1.5:
            return "semiconductor"  # 小到中等带隙，是半导体
        else:
            return "insulator"  # 大带隙，是绝缘体

    def _calculate_multi_dimensional_features(self):
        """计算多维度特征 - 简化版本"""
        # 基础能带密度
        energy_density = self._calculate_band_density()

        # 轨道权重密度
        orbital_weight_density = self._calculate_orbital_weight_density()

        # 简化版本：不计算能带交叉密度和色散
        print("简化计算：跳过能带交叉密度和色散计算")

        return {
            'energy_density': energy_density,
            'orbital_weight_density': orbital_weight_density
        }

    def _calculate_band_density(self, energy_step=0.1):
        """计算能带密度分布"""
        all_energies = self.band_energies.flatten()
        energy_min = np.min(all_energies)
        energy_max = np.max(all_energies)

        # 创建能量网格
        energy_grid = np.arange(energy_min, energy_max + energy_step, energy_step)
        density = np.zeros(len(energy_grid))

        # 计算每个能量点的能带密度
        for i, energy in enumerate(energy_grid):
            # 统计在该能量附近的能带数量
            nearby_energies = all_energies[np.abs(all_energies - energy) <= energy_step/2]
            density[i] = len(nearby_energies)

        return energy_grid, density

    def _calculate_orbital_weight_density(self, energy_step=0.1):
        """计算轨道权重密度分布"""
        all_energies = self.band_energies.flatten()
        energy_min = np.min(all_energies)
        energy_max = np.max(all_energies)

        energy_grid = np.arange(energy_min, energy_max + energy_step, energy_step)
        weight_density = np.zeros(len(energy_grid))

        print("计算轨道权重密度...")

        for i, energy in enumerate(energy_grid):
            total_weight = 0
            count = 0

            # 遍历所有k点和能带
            for k_idx in range(self.num_kpoints):
                for band_idx in range(self.num_bands):
                    band_energy = self.band_energies[k_idx, band_idx]
                    if abs(band_energy - energy) <= energy_step:
                        # 计算该点的总轨道权重
                        if k_idx < len(self.weights_data) and band_idx < len(self.weights_data[k_idx]):
                            # 获取该k点该能带的所有轨道权重
                            band_weights = self.weights_data[k_idx][band_idx]
                            # 确保band_weights是数组
                            if isinstance(band_weights, (list, np.ndarray)):
                                # 只计算显著权重
                                significant_weights = np.array(band_weights)[np.array(band_weights) > 0.005]
                                total_weight += np.sum(significant_weights)
                                count += 1

            weight_density[i] = total_weight / max(count, 1)

        return energy_grid, weight_density

    # 删除了能带交叉密度和色散计算函数以提高性能

    def _smart_window_selection(self, features, material_type, vbm, cbm, band_gap):
        """智能窗口选择 - 简化版轨道权重引导"""
        print(f"使用轨道权重引导算法选择窗口 (材料类型: {material_type})...")

        # 获取特征数据
        energy_grid, band_density = features['energy_density']
        _, weight_density = features['orbital_weight_density']

        # 计算简化的综合评分
        scores = self._calculate_simplified_scores(
            energy_grid, band_density, weight_density
        )

        # 基于材料类型的自适应窗口选择
        energy_window = self._adaptive_boundary_selection(
            energy_grid, scores, material_type, vbm, cbm, band_gap
        )

        return energy_window

    def _calculate_simplified_scores(self, energy_grid, band_density, weight_density):
        """计算简化的评分 - 只使用轨道权重和能带密度"""
        print("计算轨道权重引导评分...")

        # 归一化特征 (避免除零错误)
        band_density_norm = band_density / max(np.max(band_density), 1e-6)
        weight_density_norm = weight_density / max(np.max(weight_density), 1e-6)

        # 费米面附近加权 (高斯分布)
        fermi_proximity = np.exp(-np.abs(energy_grid - self.fermi_energy) / 2.0)

        # 简化的评分权重
        weights = {
            'fermi_proximity': 0.40,    # 费米面附近很重要
            'orbital_weight': 0.50,     # 轨道权重最重要
            'band_density': 0.10        # 能带密度较重要
        }

        # 计算简化评分 (分数越高越重要)
        scores = (weights['fermi_proximity'] * fermi_proximity +
                 weights['orbital_weight'] * weight_density_norm +
                 weights['band_density'] * band_density_norm)

        print(f"评分范围: {np.min(scores):.3f} ~ {np.max(scores):.3f}")
        return scores

    def _adaptive_boundary_selection(self, energy_grid, scores, material_type, vbm, cbm, band_gap):
        """自适应边界选择"""
        print(f"自适应边界选择 (材料类型: {material_type})...")

        # 找到费米面在能量网格中的位置
        fermi_idx = np.argmin(np.abs(energy_grid - self.fermi_energy))

        # 根据材料类型确定基础窗口大小
        if material_type == "metal":
            base_window_half = 3.0  # 金属: ±3 eV
            search_range_half = 6.0  # 搜索范围: ±6 eV
        elif material_type == "semiconductor":
            base_window_half = 4.0  # 半导体: ±4 eV
            search_range_half = 8.0  # 搜索范围: ±8 eV
        else:  # insulator
            base_window_half = 5.0  # 绝缘体: ±5 eV
            search_range_half = 10.0  # 搜索范围: ±10 eV

        # 转换为索引
        energy_step = energy_grid[1] - energy_grid[0]
        base_idx_half = int(base_window_half / energy_step)
        search_idx_half = int(search_range_half / energy_step)

        # 寻找上边界
        upper_boundary = self._find_smart_upper_boundary(
            energy_grid, scores, fermi_idx, base_idx_half, search_idx_half, material_type, cbm, band_gap
        )

        # 寻找下边界
        lower_boundary = self._find_smart_lower_boundary(
            energy_grid, scores, fermi_idx, base_idx_half, search_idx_half, material_type, vbm, band_gap
        )

        # 确保最小窗口大小
        window_size = upper_boundary - lower_boundary
        min_window = 4.0  # 最小4 eV窗口
        if window_size < min_window:
            center = (upper_boundary + lower_boundary) / 2
            upper_boundary = center + min_window / 2
            lower_boundary = center - min_window / 2

        print(f"自适应窗口: {lower_boundary:.3f} ~ {upper_boundary:.3f} eV")
        print(f"窗口大小: {window_size:.3f} eV")

        return (lower_boundary, upper_boundary)

    def _find_smart_upper_boundary(self, energy_grid, scores, fermi_idx, base_idx_half, search_idx_half, material_type, cbm, band_gap):
        """智能寻找上边界"""
        # 确定搜索起始位置
        if material_type != "metal" and band_gap > 0.1:
            # 对于半导体/绝缘体，从导带底上方开始搜索
            start_energy = cbm + 0.3
            start_idx = np.argmin(np.abs(energy_grid - start_energy))
        else:
            # 对于金属，从费米面上方开始搜索
            start_idx = fermi_idx + int(1.0 / (energy_grid[1] - energy_grid[0]))

        # 搜索范围
        end_idx = min(len(energy_grid) - 1, fermi_idx + search_idx_half)

        # 寻找评分较低的区域作为边界 (评分低意味着不重要)
        best_boundary_idx = fermi_idx + base_idx_half
        min_score = float('inf')

        for idx in range(max(start_idx, fermi_idx + base_idx_half // 2), end_idx):
            # 计算局部平均评分 (1 eV窗口)
            window_half = int(0.5 / (energy_grid[1] - energy_grid[0]))
            window_start = max(0, idx - window_half)
            window_end = min(len(scores), idx + window_half)
            local_score = np.mean(scores[window_start:window_end])

            # 寻找评分最低的区域，但要确保距离费米面足够远
            if local_score < min_score and energy_grid[idx] > self.fermi_energy + 2.0:
                min_score = local_score
                best_boundary_idx = idx

        # 确保边界合理
        upper_boundary = energy_grid[best_boundary_idx]
        upper_boundary = max(upper_boundary, self.fermi_energy + 3.0)  # 至少3 eV
        upper_boundary = min(upper_boundary, self.fermi_energy + 12.0)  # 最多12 eV

        print(f"上边界: {upper_boundary:.3f} eV (评分: {min_score:.3f})")
        return upper_boundary

    def _find_smart_lower_boundary(self, energy_grid, scores, fermi_idx, base_idx_half, search_idx_half, material_type, vbm, band_gap):
        """智能寻找下边界"""
        # 确定搜索起始位置
        if material_type != "metal" and band_gap > 0.1:
            # 对于半导体/绝缘体，从价带顶下方开始搜索
            start_energy = vbm - 0.3
            start_idx = np.argmin(np.abs(energy_grid - start_energy))
        else:
            # 对于金属，从费米面下方开始搜索
            start_idx = fermi_idx - int(1.0 / (energy_grid[1] - energy_grid[0]))

        # 搜索范围
        end_idx = max(0, fermi_idx - search_idx_half)

        # 寻找评分较低的区域作为边界
        best_boundary_idx = fermi_idx - base_idx_half
        min_score = float('inf')

        for idx in range(min(start_idx, fermi_idx - base_idx_half // 2), end_idx, -1):
            # 计算局部平均评分 (1 eV窗口)
            window_half = int(0.5 / (energy_grid[1] - energy_grid[0]))
            window_start = max(0, idx - window_half)
            window_end = min(len(scores), idx + window_half)
            local_score = np.mean(scores[window_start:window_end])

            # 寻找评分最低的区域，但要确保距离费米面足够远
            if local_score < min_score and energy_grid[idx] < self.fermi_energy - 2.0:
                min_score = local_score
                best_boundary_idx = idx

        # 确保边界合理
        lower_boundary = energy_grid[best_boundary_idx]
        lower_boundary = min(lower_boundary, self.fermi_energy - 3.0)  # 至少-3 eV
        lower_boundary = max(lower_boundary, self.fermi_energy - 12.0)  # 最多-12 eV

        print(f"下边界: {lower_boundary:.3f} eV (评分: {min_score:.3f})")
        return lower_boundary

    def _find_upper_limit(self, energy_density, cbm, band_gap):
        """寻找上限：从费米面向上寻找能带稀疏区域"""
        energy_grid, density = energy_density

        # 从费米面开始向上搜索
        fermi_idx = np.argmin(np.abs(energy_grid - self.fermi_energy))

        # 如果有明显带隙，先跳过导带底
        if band_gap > 0.1:
            start_energy = cbm + 0.5  # 从导带底上方0.5 eV开始
            print(f"检测到带隙 {band_gap:.3f} eV，从导带底上方开始搜索")
        else:
            start_energy = self.fermi_energy + 1.0  # 金属情况从费米面上方1 eV开始
            print("金属材料，从费米面上方开始搜索")

        start_idx = np.argmin(np.abs(energy_grid - start_energy))

        # 寻找能带稀疏区域
        min_density = float('inf')
        optimal_upper = start_energy + 6.0  # 默认上限

        # 在合理范围内搜索 (最多向上15 eV)
        search_range = min(len(energy_grid) - start_idx, int(15.0 / 0.1))

        for i in range(start_idx, start_idx + search_range):
            if i >= len(density):
                break

            # 计算局部平均密度 (窗口大小为1 eV)
            window_size = int(1.0 / 0.1)
            window_start = max(0, i - window_size//2)
            window_end = min(len(density), i + window_size//2)
            local_density = np.mean(density[window_start:window_end])

            # 寻找密度最小的区域
            if local_density < min_density and energy_grid[i] > start_energy + 2.0:
                min_density = local_density
                optimal_upper = energy_grid[i]

        # 确保上限合理 (至少比费米面高4 eV，最多高15 eV)
        optimal_upper = max(optimal_upper, self.fermi_energy + 4.0)
        optimal_upper = min(optimal_upper, self.fermi_energy + 15.0)

        print(f"上限搜索: 最稀疏区域在 {optimal_upper:.3f} eV (密度: {min_density:.1f})")
        return optimal_upper

    def _find_lower_limit(self, energy_density, vbm, band_gap):
        """寻找下限：从费米面向下寻找能带稀疏区域"""
        energy_grid, density = energy_density

        # 从费米面开始向下搜索
        fermi_idx = np.argmin(np.abs(energy_grid - self.fermi_energy))

        # 如果有明显带隙，先跳过价带顶
        if band_gap > 0.1:
            start_energy = vbm - 0.5  # 从价带顶下方0.5 eV开始
            print(f"检测到带隙 {band_gap:.3f} eV，从价带顶下方开始搜索")
        else:
            start_energy = self.fermi_energy - 1.0  # 金属情况从费米面下方1 eV开始
            print("金属材料，从费米面下方开始搜索")

        start_idx = np.argmin(np.abs(energy_grid - start_energy))

        # 寻找能带稀疏区域
        min_density = float('inf')
        optimal_lower = start_energy - 6.0  # 默认下限

        # 在合理范围内搜索 (最多向下15 eV)
        search_range = min(start_idx, int(15.0 / 0.1))

        for i in range(start_idx, max(0, start_idx - search_range), -1):
            if i < 0:
                break

            # 计算局部平均密度 (窗口大小为1 eV)
            window_size = int(1.0 / 0.1)
            window_start = max(0, i - window_size//2)
            window_end = min(len(density), i + window_size//2)
            local_density = np.mean(density[window_start:window_end])

            # 寻找密度最小的区域
            if local_density < min_density and energy_grid[i] < start_energy - 2.0:
                min_density = local_density
                optimal_lower = energy_grid[i]

        # 确保下限合理 (至少比费米面低4 eV，最多低15 eV)
        optimal_lower = min(optimal_lower, self.fermi_energy - 4.0)
        optimal_lower = max(optimal_lower, self.fermi_energy - 15.0)

        print(f"下限搜索: 最稀疏区域在 {optimal_lower:.3f} eV (密度: {min_density:.1f})")
        return optimal_lower
        
    def _identify_important_bands(self):
        """识别费米面附近的重要能带"""
        print("\n=== 识别重要能带 ===")
        
        important_bands = []
        
        for band_idx in range(self.num_bands):
            band_energies = self.band_energies[:, band_idx]
            
            # 检查能带是否在能量窗口内
            in_window = np.any((band_energies >= self.energy_window[0]) & 
                              (band_energies <= self.energy_window[1]))
            
            # 检查能带是否跨越费米面
            crosses_fermi = (np.min(band_energies) <= self.fermi_energy <= np.max(band_energies))
            
            # 检查能带是否接近费米面
            min_distance_to_fermi = np.min(np.abs(band_energies - self.fermi_energy))
            close_to_fermi = min_distance_to_fermi <= 3.0  # 3 eV内
            
            if in_window and (crosses_fermi or close_to_fermi):
                important_bands.append(band_idx)
                
                if crosses_fermi:
                    print(f"能带 {band_idx}: 跨越费米面")
                else:
                    print(f"能带 {band_idx}: 接近费米面 (最小距离: {min_distance_to_fermi:.3f} eV)")
        
        self.important_bands = important_bands
        print(f"识别到 {len(important_bands)} 条重要能带")
        
        return important_bands

    def create_output_folder(self):
        """创建输出文件夹"""
        elements_str = "_".join(sorted(self.elements))
        self.output_folder = f"fermi_{elements_str}"

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            print(f"\n创建输出文件夹: {self.output_folder}")
        else:
            print(f"\n使用现有文件夹: {self.output_folder}")

        return self.output_folder

    def _smooth_orbital_weights(self, k_points, energies, weights, method='gaussian'):
        """平滑轨道权重数据，解决跳跃点问题"""
        if len(k_points) < 3:
            return k_points, energies, weights

        if method == 'gaussian':
            # 高斯平滑 - 对权重和能量进行平滑处理
            try:
                from scipy.ndimage import gaussian_filter1d

                # 根据数据点数量自适应调整sigma
                sigma = max(1.0, len(k_points) / 50)

                # 对权重进行高斯平滑
                weights_smooth = gaussian_filter1d(weights, sigma=sigma)

                # 对能量进行轻微平滑，保持能带形状
                energies_smooth = gaussian_filter1d(energies, sigma=sigma*0.3)

                return k_points, energies_smooth, weights_smooth
            except ImportError:
                print("警告: scipy不可用，跳过高斯平滑")
                return k_points, energies, weights

        # 删除了插值平滑方法

        else:
            # 默认不平滑
            return k_points, energies, weights

    def _plot_orbital_weight_points(self, ax, k_points, energies, weights, color, min_weight=0.005, plot_settings=None):
        """绘制轨道权重散点图"""
        if len(k_points) < 2:
            return

        # 过滤掉权重过小的点
        significant_mask = weights > min_weight
        if not np.any(significant_mask):
            return

        k_significant = k_points[significant_mask]
        e_significant = energies[significant_mask]
        w_significant = weights[significant_mask]

        # 计算点的大小
        base_size = 8
        max_size = 120
        w_max = np.max(w_significant) if len(w_significant) > 0 else 1.0
        if w_max > 0:
            w_normalized = w_significant / w_max
            point_sizes = base_size + w_normalized * (max_size - base_size)
        else:
            point_sizes = np.ones_like(w_significant) * base_size

        # 绘制散点
        scatter = ax.scatter(k_significant, e_significant,
                           s=point_sizes,
                           c=color,
                           alpha=0.8,
                           edgecolors='none',
                           zorder=3)

        return scatter

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
                                  min_width=10, max_width=18, min_height=7, max_height=14):
        """根据能量范围动态计算图片尺寸"""
        energy_span = energy_range[1] - energy_range[0]

        # 基准能量范围 (8 eV，费米面版本的典型窗口)
        base_energy_span = 8.0

        # 计算缩放因子
        scale_factor = energy_span / base_energy_span

        # 应用缩放，费米面版本变化更敏感
        dynamic_width = base_width * (0.7 + 0.6 * scale_factor)  # 宽度变化中等
        dynamic_height = base_height * (0.6 + 0.8 * scale_factor)  # 高度变化较大

        # 限制在最小和最大值之间
        dynamic_width = max(min_width, min(max_width, dynamic_width))
        dynamic_height = max(min_height, min(max_height, dynamic_height))

        print(f"费米面能量范围: {energy_span:.1f} eV, 图片尺寸: {dynamic_width:.1f} x {dynamic_height:.1f} 英寸")

        return (dynamic_width, dynamic_height)

    def plot_fermi_band_structure(self, figsize=None, dpi=300):
        """绘制费米面附近的能带结构图"""
        print("\n=== 绘制费米面附近能带结构图 ===")

        # 动态计算图片尺寸
        if figsize is None:
            figsize = self._calculate_dynamic_figsize(self.energy_window, base_width=14, base_height=10)

        fig, ax = plt.subplots(figsize=figsize)

        # 绘制能带骨架，突出重要能带
        important_count = 0
        other_count = 0

        for band_idx in range(self.num_bands):
            band_energies = self.band_energies[:, band_idx]

            # 只绘制在能量窗口内的能带
            mask = (band_energies >= self.energy_window[0]) & (band_energies <= self.energy_window[1])
            if not np.any(mask):
                continue

            k_filtered = self.k_points[mask]
            e_filtered = band_energies[mask]

            if band_idx in self.important_bands:
                # 重要能带用粗黑线
                ax.plot(k_filtered, e_filtered, 'k-', linewidth=1.5, alpha=0.9, zorder=2)
                important_count += 1
            else:
                # 其他能带用细灰线
                ax.plot(k_filtered, e_filtered, color='gray', linewidth=0.8, alpha=0.6, zorder=1)
                other_count += 1

        # 添加费米能级
        ax.axhline(y=self.fermi_energy, color='red', linestyle='--',
                  alpha=0.9, linewidth=2.5, zorder=3, label='Fermi level')

        # 设置图形属性
        ax.set_xlabel('k-point path', fontsize=14, fontweight='bold')
        ax.set_ylabel('Energy (eV)', fontsize=14, fontweight='bold')
        ax.set_title('FPLO Band Structure (Fermi Region for Wannier Projection)',
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_ylim(self.energy_window)
        ax.grid(True, alpha=0.3, zorder=0)

        # 添加信息文本
        window_size = self.energy_window[1] - self.energy_window[0]
        info_text = (f"Fermi level: {self.fermi_energy:.3f} eV (reference)\n"
                    f"Energy window: {self.energy_window[0]:.1f} ~ {self.energy_window[1]:.1f} eV\n"
                    f"Window size: {window_size:.1f} eV\n"
                    f"Important bands: {important_count}\n"
                    f"Other bands: {other_count}")

        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=12,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # 图例
        legend_elements = [
            plt.Line2D([0], [0], color='k', linewidth=1.5, label='Important bands'),
            plt.Line2D([0], [0], color='gray', linewidth=0.8, label='Other bands'),
            plt.Line2D([0], [0], color='red', linestyle='--', linewidth=2.5, label='Fermi level')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=12,
                 frameon=True, fancybox=True, shadow=True)

        plt.tight_layout()
        output_path = os.path.join(self.output_folder, '01_fermi_bands.png')
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        print(f"保存: {output_path}")
        print(f"重要能带: {important_count} 条")
        print(f"其他能带: {other_count} 条")
        return output_path

    def plot_fermi_orbital_weights(self, figsize=None, dpi=300):
        """绘制费米面附近的轨道权重图"""
        print("\n=== 绘制费米面附近轨道权重图 ===")

        # 动态计算图片尺寸
        if figsize is None:
            figsize = self._calculate_dynamic_figsize(self.energy_window, base_width=16, base_height=12)

        fig, ax = plt.subplots(figsize=figsize)

        # 绘制重要能带的骨架
        for band_idx in self.important_bands:
            band_energies = self.band_energies[:, band_idx]
            mask = (band_energies >= self.energy_window[0]) & (band_energies <= self.energy_window[1])
            if np.any(mask):
                k_filtered = self.k_points[mask]
                e_filtered = band_energies[mask]
                ax.plot(k_filtered, e_filtered, 'k-', linewidth=0.8, alpha=0.7, zorder=1)

        # 绘制轨道权重，只关注重要能带
        max_weight = 0
        min_weight = float('inf')
        legend_added = set()

        for orbital_key, indices in self.orbital_info.items():
            if not indices:
                continue

            color = self.orbital_colors.get(orbital_key, '#95A5A6')
            has_visible_weight = False

            for band_idx in self.important_bands:  # 只处理重要能带
                band_energies = self.band_energies[:, band_idx]
                orbital_weights = np.sum(self.band_weights[:, band_idx, :][:, indices], axis=1)

                # 能量窗口内的权重
                mask = (band_energies >= self.energy_window[0]) & (band_energies <= self.energy_window[1])
                mask = mask & (orbital_weights > 0.01)  # 权重阈值

                if np.any(mask):
                    has_visible_weight = True
                    current_max = np.max(orbital_weights[mask])
                    max_weight = max(max_weight, current_max)
                    min_weight = min(min_weight, np.min(orbital_weights[mask]))

                    k_filtered = self.k_points[mask]
                    e_filtered = band_energies[mask]
                    w_filtered = orbital_weights[mask]

                    # 改进的散点绘制方法 - 每个k点绘制权重点
                    plot_settings = getattr(self, 'plot_settings', None)
                    self._plot_orbital_weight_points(
                        ax, k_filtered, e_filtered, w_filtered, color,
                        min_weight=0.005, plot_settings=plot_settings
                    )

            # 添加图例
            if has_visible_weight and orbital_key not in legend_added:
                ax.plot([], [], color=color, linestyle='-', linewidth=3,
                       alpha=0.9, label=orbital_key.replace('_', ' '))
                legend_added.add(orbital_key)

        # 添加费米能级
        ax.axhline(y=self.fermi_energy, color='red', linestyle='--',
                  alpha=0.9, linewidth=2.5, zorder=3, label='Fermi level')

        # 设置图形属性
        ax.set_xlabel('k-point path', fontsize=14, fontweight='bold')
        ax.set_ylabel('Energy (eV)', fontsize=14, fontweight='bold')
        ax.set_title('FPLO Orbital Weights (Fermi Region for Wannier Projection)',
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_ylim(self.energy_window)
        ax.grid(True, alpha=0.3, zorder=0)

        # 添加信息文本
        elements_str = ", ".join(sorted(self.elements))
        orbitals_str = ", ".join(sorted(self.orbital_types))
        weight_range_str = f"{min_weight:.3f} ~ {max_weight:.3f}" if max_weight > 0 else "N/A"
        window_size = self.energy_window[1] - self.energy_window[0]

        info_text = (f"Elements: {elements_str}\n"
                    f"Orbitals: {orbitals_str}\n"
                    f"Fermi level: {self.fermi_energy:.3f} eV (reference)\n"
                    f"Energy window: {window_size:.1f} eV\n"
                    f"Weight range: {weight_range_str}\n"
                    f"Important bands: {len(self.important_bands)}")

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
        output_path = os.path.join(self.output_folder, '02_fermi_weights.png')
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        print(f"保存: {output_path}")
        print(f"权重范围: {weight_range_str}")
        return output_path, weight_range_str

    def plot_fermi_individual_orbitals(self, figsize=None, dpi=200):
        """绘制费米面附近的各轨道分图"""
        print("\n=== 绘制费米面附近各轨道分图 ===")

        # 动态计算图片尺寸
        if figsize is None:
            figsize = self._calculate_dynamic_figsize(self.energy_window, base_width=12, base_height=9)

        elements = sorted(self.elements)
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

                # 绘制重要能带的骨架
                for band_idx in self.important_bands:
                    band_energies = self.band_energies[:, band_idx]
                    mask = (band_energies >= self.energy_window[0]) & (band_energies <= self.energy_window[1])
                    if np.any(mask):
                        k_filtered = self.k_points[mask]
                        e_filtered = band_energies[mask]
                        ax.plot(k_filtered, e_filtered, 'k-', linewidth=0.6, alpha=0.5, zorder=1)

                # 绘制该轨道的权重，只关注重要能带
                color = self.orbital_colors.get(orbital_key, '#95A5A6')
                max_weight = 0
                min_weight = float('inf')
                has_data = False

                for band_idx in self.important_bands:  # 只处理重要能带
                    band_energies = self.band_energies[:, band_idx]
                    orbital_weights = np.sum(self.band_weights[:, band_idx, :][:, indices], axis=1)

                    # 能量窗口内的权重
                    mask = (band_energies >= self.energy_window[0]) & (band_energies <= self.energy_window[1])
                    mask = mask & (orbital_weights > 0.005)  # 更低的阈值

                    if np.any(mask):
                        has_data = True
                        current_max = np.max(orbital_weights[mask])
                        max_weight = max(max_weight, current_max)
                        min_weight = min(min_weight, np.min(orbital_weights[mask]))

                        k_filtered = self.k_points[mask]
                        e_filtered = band_energies[mask]
                        w_filtered = orbital_weights[mask]

                        # 使用散点绘制方法
                        plot_settings = getattr(self, 'plot_settings', None)
                        self._plot_orbital_weight_points(
                            ax, k_filtered, e_filtered, w_filtered, color,
                            min_weight=0.005, plot_settings=plot_settings
                        )

                # 添加费米能级
                ax.axhline(y=self.fermi_energy, color='red', linestyle='--',
                          alpha=0.8, linewidth=2, zorder=3)

                # 设置图形属性
                ax.set_xlabel('k-point path', fontsize=12, fontweight='bold')
                ax.set_ylabel('Energy (eV)', fontsize=12, fontweight='bold')
                ax.set_title(f'{element} {orbital_type} Orbital (Fermi Region for Wannier)',
                            fontsize=14, fontweight='bold', pad=15)
                ax.set_ylim(self.energy_window)
                ax.grid(True, alpha=0.3, zorder=0)

                # 添加信息文本
                window_size = self.energy_window[1] - self.energy_window[0]
                if has_data:
                    weight_range_str = f"{min_weight:.4f} ~ {max_weight:.4f}"
                    info_text = (f"Element: {element}\n"
                                f"Orbital: {orbital_type}\n"
                                f"Fermi level: {self.fermi_energy:.3f} eV (reference)\n"
                                f"Energy window: {window_size:.1f} eV\n"
                                f"Weight range: {weight_range_str}\n"
                                f"Important bands: {len(self.important_bands)}")
                else:
                    info_text = (f"Element: {element}\n"
                                f"Orbital: {orbital_type}\n"
                                f"Fermi level: {self.fermi_energy:.3f} eV (reference)\n"
                                f"Energy window: {window_size:.1f} eV\n"
                                f"No significant weight\n"
                                f"Important bands: {len(self.important_bands)}")

                ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

                # 添加图例
                legend_items = []
                legend_items.append((plt.Line2D([0], [0], color='k', linewidth=0.6, alpha=0.5), 'Important bands'))
                legend_items.append((plt.Line2D([0], [0], color='red', linestyle='--', linewidth=2, alpha=0.8), 'Fermi level'))
                if has_data:
                    legend_items.append((plt.Line2D([0], [0], color=color, linewidth=4, alpha=0.9), f'{element} {orbital_type}'))

                handles, labels = zip(*legend_items)
                ax.legend(handles, labels, loc='upper right', fontsize=10,
                         frameon=True, fancybox=True, shadow=True)

                plt.tight_layout()
                output_path = os.path.join(self.output_folder, f'{figure_count:02d}_{element}_{orbital_type}_fermi.png')
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

    def run_fermi_analysis(self, max_kpoints=150):
        """运行费米面附近的完整分析"""
        print("=" * 70)
        print("FPLO费米面附近能带可视化分析 - Wannier投影专用版本")
        print("=" * 70)

        # 1. 解析头部和体系信息
        self.parse_header_and_system()

        # 2. 读取和解析数据，分析费米面区域
        energy_window, vbm, cbm, band_gap = self.read_and_parse_data(max_kpoints=max_kpoints)

        # 3. 创建输出文件夹
        self.create_output_folder()

        # 4. 绘制所有图形
        print("\n" + "=" * 70)
        print("开始绘制费米面附近图形")
        print("=" * 70)

        # 费米面附近能带结构图
        band_path = self.plot_fermi_band_structure()

        # 费米面附近轨道权重图
        weight_path, weight_range = self.plot_fermi_orbital_weights()

        # 各轨道分图
        orbital_paths = self.plot_fermi_individual_orbitals()

        # 5. 输出完整结果摘要
        self._print_fermi_summary(band_path, weight_path, orbital_paths,
                                 weight_range, vbm, cbm, band_gap)

        return {
            'fermi_info': {
                'fermi_energy': self.fermi_energy,
                'energy_window': energy_window,
                'vbm': vbm,
                'cbm': cbm,
                'band_gap': band_gap,
                'important_bands': self.important_bands
            },
            'system_info': {
                'elements': sorted(self.elements),
                'orbital_types': sorted(self.orbital_types),
                'orbital_colors': self.orbital_colors,
                'num_bands': self.num_bands
            },
            'output_folder': self.output_folder,
            'files': {
                'fermi_bands': band_path,
                'fermi_weights': weight_path,
                'orbital_plots': orbital_paths
            },
            'weight_range': weight_range
        }

    def _print_fermi_summary(self, band_path, weight_path, orbital_paths,
                           weight_range, vbm, cbm, band_gap):
        """打印费米面分析结果摘要"""
        print("\n" + "=" * 70)
        print("费米面分析完成 - Wannier投影专用结果摘要")
        print("=" * 70)

        print(f"\n📁 输出文件夹: {self.output_folder}")
        print(f"🧬 体系信息: {len(self.elements)} 元素, {len(self.orbital_types)} 轨道类型")

        # 费米面信息
        print(f"\n⚡ 费米面分析:")
        print(f"  费米能级: {self.fermi_energy:.6f} eV (数据参考点)")
        if band_gap < 0.1:
            print(f"  材料类型: 金属/半金属")
        else:
            print(f"  材料类型: 半导体/绝缘体")
            print(f"  价带顶 (VBM): {vbm:.6f} eV (相对费米能级)")
            print(f"  导带底 (CBM): {cbm:.6f} eV (相对费米能级)")
            print(f"  带隙: {band_gap:.6f} eV")

        window_size = self.energy_window[1] - self.energy_window[0]
        print(f"  智能能量窗口: {self.energy_window[0]:.3f} ~ {self.energy_window[1]:.3f} eV")
        print(f"  窗口大小: {window_size:.3f} eV")
        print(f"  重要能带: {len(self.important_bands)} 条")

        print(f"\n🎨 权重范围: {weight_range}")

        print(f"\n📈 生成图片 (Wannier投影专用):")
        print(f"  1. {os.path.basename(band_path)} - 费米面附近能带图 (300 DPI)")
        print(f"  2. {os.path.basename(weight_path)} - 费米面附近权重图 (300 DPI)")

        for i, path in enumerate(orbital_paths, 3):
            filename = os.path.basename(path)
            element_orbital = filename.replace('_fermi.png', '').split('_', 1)[1]
            print(f"  {i}. {filename} - {element_orbital} 费米面轨道图 (200 DPI)")

        print(f"\n总计生成: {2 + len(orbital_paths)} 张图片")

        print(f"\n🎨 颜色分配:")
        for orbital_key, color in self.orbital_colors.items():
            element, orbital = orbital_key.split('_')
            print(f"  {element} {orbital}: {color}")

        print(f"\n✅ 专注费米面附近 {window_size:.1f} eV 能量窗口")
        print("✅ 突出显示重要能带，便于Wannier投影分析")
        print("✅ 智能识别价带顶和导带底")
        print("✅ 优化轨道权重显示，适合科研分析")


def main():
    """主程序入口"""
    import sys

    # 检查文件是否存在
    filename = '+bweights'
    if not os.path.exists(filename):
        print(f"❌ 错误: 找不到文件 '{filename}'")
        print("请确保+bweights文件在当前目录下")
        sys.exit(1)

    try:
        # 创建费米面可视化器并运行分析
        visualizer = FPLOFermiVisualizer(filename)
        results = visualizer.run_fermi_analysis(max_kpoints=150)

        print(f"\n🎉 FPLO费米面能带分析成功完成！")
        print(f"📁 查看输出文件夹: {results['output_folder']}")
        print(f"🔬 专为Wannier投影分析优化")

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

# FPLO能带权重可视化程序

**作者**: zhujiawen@ustc.mail.edu.cn

## 📋 程序概述

本项目提供两个专业的FPLO能带权重可视化程序，分别针对不同的科研需求进行优化：

### 1. **完整版本** - `fplo_visualizer.py`
- **用途**: 材料电子结构全面分析
- **特点**: 显示完整能量范围的所有能带和轨道权重
- **适用**: 全貌分析、深层电子态研究、教学演示

### 2. **费米面版本** - `fplo_fermi_visualizer.py`
- **用途**: Wannier投影专用分析
- **特点**: 智能关注费米面附近，突出重要能带
- **适用**: 电子输运、拓扑性质、超导研究

## 🚀 快速开始

### 环境要求
```bash
pip install numpy matplotlib
```

### 使用方法
```bash
# 完整版本 - 全能量范围分析
python fplo_visualizer.py

# 费米面版本 - 费米面附近分析
python fplo_fermi_visualizer.py
```

确保 `+bweights` 文件在当前目录下。

## 🔬 完整版本详解

### 功能特点
- **完整能量范围**: 显示从深层核态到高能激发态的所有电子结构
- **全能带显示**: 处理所有208条能带，不遗漏任何信息
- **科学准确性**: 提供材料电子结构的完整图像


### 适用场景
✅ 第一次分析新材料，需要了解全貌  
✅ X射线光谱分析，需要深层电子态信息  
✅ 教学演示，展示完整电子结构概念  
✅ 方法学研究，验证计算方法完整性  
✅ 核心能级分析，研究内层电子性质  

## ⚡ 费米面版本详解

### 功能特点
- **智能能量窗口**: 自动寻找能带稀疏区域作为上下限
- **重要能带识别**: 智能筛选费米面附近的关键能带
- **材料类型识别**: 自动判断金属/半导体并分析带隙
- **Wannier优化**: 专门为轨道投影分析优化

### 智能算法
```
能量窗口选择逻辑:
1. 识别价带顶(VBM)和导带底(CBM)
2. 计算能带密度分布
3. 从费米面向上寻找能带稀疏区域作为上限
4. 从费米面向下寻找能带稀疏区域作为下限
5. 确保窗口包含重要的电子态
```

### 差异化设计
**完整版本**:
- 所有能带等权重显示
- 黑色能带骨架 + 彩色权重分布
- 完整能量范围标注

**费米面版本**:
- 重要能带粗线突出显示
- 其他能带细灰线淡化
- 费米面特征详细标注

## 🔧 程序化使用

### 完整版本
```python
from fplo_visualizer import FPLOVisualizer

visualizer = FPLOVisualizer('+bweights')
results = visualizer.run_complete_analysis(max_kpoints=150)

print(f"输出文件夹: {results['output_folder']}")
print(f"能量范围: {results['system_info']['energy_range']}")
```

### 费米面版本
```python
from fplo_fermi_visualizer import FPLOFermiVisualizer

visualizer = FPLOFermiVisualizer('+bweights')
results = visualizer.run_fermi_analysis(max_kpoints=150)

fermi_info = results['fermi_info']
print(f"费米能级: {fermi_info['fermi_energy']:.6f} eV")
print(f"带隙: {fermi_info['band_gap']:.6f} eV")
print(f"重要能带: {len(fermi_info['important_bands'])} 条")
```

## 📋 使用建议

### 研究流程建议
1. **第一步**: 使用完整版本了解材料全貌
2. **第二步**: 使用费米面版本进行精细分析
3. **第三步**: 结合两版本结果进行综合讨论

### 论文发表建议
- **主图**: 使用费米面版本的高质量图片
- **补充材料**: 提供完整版本的全能量范围图
- **方法部分**: 说明能量窗口选择的科学依据

### 选择指南
**选择完整版本**:
- 需要分析深层电子态
- 第一次研究新材料
- 需要完整的电子结构图像

**选择费米面版本**:
- 进行Wannier投影分析
- 研究电子输运性质
- 分析拓扑或超导性质

## 🎉 总结

两个程序各有优势，互为补充：

- **完整版本**: 全面、完整、教育性强
- **费米面版本**: 专业、高效、针对性强

根据具体研究目标选择合适的版本，或者两个版本结合使用，获得最全面和深入的分析结果！

---

**快速使用**:
```bash
python fplo_visualizer.py        # 完整分析
python fplo_fermi_visualizer.py  # 费米面分析
```

# FPLO能带权重可视化工具

**作者**: zhujiawen@ustc.mail.edu.cn

## 简介

FPLO能带权重可视化工具是一个图形用户界面(GUI)应用程序，用于可视化和分析FPLO计算的能带结构和轨道权重。该工具提供了丰富的交互功能，包括放大缩小、轨道显示控制、图像导出等。

## 功能特点

- **交互式可视化**: 支持放大、缩小、平移等操作
- **轨道控制**: 可以单独控制每个元素和轨道的显示/隐藏
- **实时反馈**: 程序运行过程中提供详细的状态信息和警告
- **图像导出**: 支持多种格式(PNG, PDF, SVG)的高质量图像导出
- **图像定制**: 可以调整标题、刻度、线条颜色、粗细等属性
- **多视图模式**: 支持完整能带结构和费米面附近两种视图模式

## 安装方法

### 方法1: 使用预编译的可执行文件

1. 下载对应平台的可执行文件
2. 赋予执行权限: `chmod +x FPLO_Visualizer`
3. 运行程序: `./FPLO_Visualizer`

### 方法2: 从源码安装

```bash
# 克隆仓库
git clone https://github.com/username/fplo-visualizer.git
cd fplo-visualizer

# 安装依赖
pip install -r requirements.txt

# 运行程序
python fplo_gui_main.py
```

### 方法3: 从源码打包

```bash
# 克隆仓库
git clone https://github.com/username/fplo-visualizer.git
cd fplo-visualizer

# 在Linux上打包
chmod +x build_linux.sh
./build_linux.sh

# 运行打包后的程序
./dist/FPLO_Visualizer
```

## 使用方法

1. **打开文件**: 点击"文件" > "打开+bweight文件"，选择FPLO计算生成的+bweight文件
2. **查看能带**: 程序会自动加载并显示能带结构和轨道权重
3. **控制轨道显示**: 使用右侧面板的复选框控制各元素轨道的显示/隐藏
4. **调整显示参数**: 使用滑块调整点大小、透明度等参数
5. **切换视图**: 点击"视图"菜单切换不同的显示模式
6. **导出图像**: 点击"文件" > "导出图像"，选择保存格式和位置

## 界面说明

![界面说明](resources/images/interface_guide.png)

1. **菜单栏**: 包含文件操作和视图切换选项
2. **工具栏**: 提供放大、缩小、平移等交互工具
3. **绘图区域**: 显示能带结构和轨道权重
4. **控制面板**: 控制轨道显示和绘图参数
5. **日志区域**: 显示程序运行状态和警告信息
6. **状态栏**: 显示当前状态和进度

## 常见问题

**Q: 程序无法启动怎么办?**  
A: 检查是否安装了所有依赖，特别是PyQt5和matplotlib。

**Q: 图像导出失败怎么办?**  
A: 确保目标文件夹有写入权限，并且文件名合法。

**Q: 如何调整图像大小?**  
A: 可以通过调整窗口大小，或在导出前设置DPI和图像尺寸。

## 开发者信息

如需贡献代码或报告问题，请访问项目GitHub仓库:
https://github.com/username/fplo-visualizer

## 许可证

MIT License

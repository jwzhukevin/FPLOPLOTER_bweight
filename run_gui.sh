#!/bin/bash
# FPLO能带权重可视化工具 - 统一启动脚本
# 作者: zhujiawen@ustc.mail.edu.cn
# 版本: 2.0.0
# 功能: 自动检测环境，配置优化参数，启动GUI程序

echo "🔬 FPLO能带权重可视化工具 v2.0.0"
echo "作者: zhujiawen@ustc.mail.edu.cn"
echo "=================================================="

# 🔍 环境检查
echo "🔍 检查运行环境..."

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到python3"
    echo "请先安装Python 3.7或更高版本"
    echo "Ubuntu/Debian: sudo apt install python3"
    echo "CentOS/RHEL: sudo yum install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python版本: $PYTHON_VERSION"

# 检查必要的Python包
echo "🔍 检查Python依赖..."
MISSING_PACKAGES=""

for package in PyQt5 matplotlib numpy scipy; do
    if ! python3 -c "import $package" 2>/dev/null; then
        MISSING_PACKAGES="$MISSING_PACKAGES $package"
    fi
done

if [ -n "$MISSING_PACKAGES" ]; then
    echo "❌ 缺少Python包:$MISSING_PACKAGES"
    echo "Ubuntu 请执行如下命令安装:"
    echo "  sudo apt update && sudo apt install -y python3-pyqt5 python3-matplotlib python3-numpy python3-scipy python3-pip"
    echo "或使用pip安装:"
    echo "  pip3 install -r requirements.txt"
    exit 1
fi

echo "✅ Python依赖检查通过"

# ⚙️ 性能优化配置
echo "⚙️ 配置性能优化参数..."

# 检测CPU核心数
CPU_CORES=$(nproc)
MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
echo "🖥️ 系统配置: ${CPU_CORES}核心, ${MEMORY_GB}GB内存"

# 设置环境变量
export QT_QUICK_BACKEND=software    # 使用软件渲染，减少GPU负载
export QT_SCALE_FACTOR=1.0           # 固定缩放因子，避免界面问题
export MPLBACKEND=Qt5Agg             # 指定matplotlib后端
export OMP_NUM_THREADS=$CPU_CORES    # OpenMP线程数
export NUMBA_NUM_THREADS=$CPU_CORES  # Numba线程数
export PYTHONOPTIMIZE=1              # 启用Python优化
export PYTHONDONTWRITEBYTECODE=1     # 不生成.pyc文件

# 根据系统配置给出建议
if [ $MEMORY_GB -lt 8 ]; then
    echo "💡 内存较少，建议使用保守设置"
    PERFORMANCE_MODE="conservative"
elif [ $MEMORY_GB -lt 16 ]; then
    echo "💡 内存适中，使用平衡设置"
    PERFORMANCE_MODE="balanced"
else
    echo "💡 内存充足，可使用高性能设置"
    PERFORMANCE_MODE="high"
fi

# 🖥️ 图形环境检测（Ubuntu精简版）
echo "🖥️ 检测图形环境..."

# 测试当前环境是否可用
test_gui_environment() {
    echo "🧪 测试图形环境..."
    if python3 -c "from PyQt5.QtWidgets import QApplication; app=QApplication([]); app.quit()" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

if test_gui_environment; then
    echo "✅ 图形环境可用"
    GUI_MODE="native"
else
    echo "⚠️ 图形环境检测失败，尝试继续启动（可能为服务器/无头环境）"
    GUI_MODE="fallback"
fi

echo "🎯 图形模式: ${GUI_MODE}"

# 🚀 启动程序
echo ""
echo "🚀 启动FPLO可视化工具..."
echo "=================================================="

# 根据性能模式给出提示
case $PERFORMANCE_MODE in
    "conservative")
        echo "💡 当前使用保守模式，建议设置:"
        echo "   - 最大点数/轨道: 300"
        echo "   - 插值密度: 1"
        echo "   - 关闭插值功能"
        ;;
    "balanced")
        echo "💡 当前使用平衡模式，建议设置:"
        echo "   - 最大点数/轨道: 500"
        echo "   - 插值密度: 1-2"
        echo "   - 适度使用插值"
        ;;
    "high")
        echo "💡 当前使用高性能模式，可以设置:"
        echo "   - 最大点数/轨道: 1000+"
        echo "   - 插值密度: 2-5"
        echo "   - 启用所有功能"
        ;;
esac

echo ""
echo "⚡ 性能优化已启用:"
echo "   🖥️ 多核处理: ${CPU_CORES}核心"
echo "   💾 缓存机制: 已启用"
echo "   🎯 智能采样: 已启用"
echo "   📊 权重过滤: 阈值0.02"
echo ""
echo "📖 使用提示:"
echo "   • 按F1查看详细使用说明"
echo "   • 使用Shift+拖拽进行框选放大"
echo "   • 在右侧面板调整性能参数"
echo ""

# 检查是否存在主程序文件
if [ ! -f "fplo_gui_main.py" ]; then
    echo "❌ 错误: 找不到fplo_gui_main.py"
    echo "请确保在正确的目录中运行此脚本"
    exit 1
fi

# 启动程序
python3 fplo_gui_main.py

# 程序退出后的清理
EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 程序正常退出"
else
    echo "❌ 程序异常退出 (退出码: $EXIT_CODE)"
fi

echo "感谢使用FPLO可视化工具！"

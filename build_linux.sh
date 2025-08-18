#!/bin/bash
# FPLO能带权重可视化工具Linux打包脚本 - WSL兼容版本
# 作者: zhujiawen@ustc.mail.edu.cn

echo "=== FPLO能带权重可视化工具打包脚本 (WSL兼容版) ==="

# 检查Python3是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到python3命令。请安装Python 3:"
    echo "sudo apt update && sudo apt install python3 python3-pip python3-venv python3-full"
    exit 1
fi

# 检查pip3是否安装
if ! command -v pip3 &> /dev/null; then
    echo "错误: 未找到pip3命令。请安装pip3:"
    echo "sudo apt install python3-pip"
    exit 1
fi

# 确保有python3-venv
echo "检查并安装必要的包..."
sudo apt update
sudo apt install -y python3-venv python3-full python3-pip python3-pyqt5

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv --system-site-packages venv
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip3 install --break-system-packages -r requirements.txt

# 检查PyInstaller是否安装
if ! command -v pyinstaller &> /dev/null; then
    echo "安装PyInstaller..."
    pip3 install --break-system-packages pyinstaller
fi

# 创建资源目录
mkdir -p resources/icons

# 创建一个简单的图标
echo "创建应用图标..."
cat > resources/icons/app_icon.py << 'EOL'
# 简单的Python图标生成脚本
from PIL import Image, ImageDraw
img = Image.new('RGBA', (128, 128), color=(255, 255, 255, 0))
draw = ImageDraw.Draw(img)
draw.rectangle([(20, 20), (108, 108)], fill=(65, 105, 225))
draw.ellipse([(40, 40), (88, 88)], fill=(255, 255, 255))
img.save('resources/icons/app_icon.png')
EOL

# 尝试生成图标
if command -v python3 &> /dev/null; then
    pip3 install --break-system-packages pillow
    python3 resources/icons/app_icon.py
else
    echo "警告: 无法生成图标，将使用默认图标"
    touch resources/icons/app_icon.png
fi

# 使用PyInstaller打包
echo "开始打包..."
pyinstaller --name="FPLO_Visualizer" \
            --windowed \
            --onefile \
            --add-data "fplo_visualizer.py:." \
            --add-data "fplo_fermi_visualizer.py:." \
            --icon=resources/icons/app_icon.png \
            fplo_gui_main.py

echo "打包完成! 可执行文件位于 dist/FPLO_Visualizer"
echo "运行方式: ./dist/FPLO_Visualizer"

# 退出虚拟环境
deactivate

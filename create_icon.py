#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建FPLO可视化工具的自定义图标
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor, QPen, QFont, QLinearGradient
from PyQt5.QtCore import Qt, QRect
import sys

def create_fplo_icon(size=64):
    """创建FPLO图标"""
    # 创建指定大小的图标
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # 创建渐变背景
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor(70, 130, 180))   # 钢蓝色
    gradient.setColorAt(0.5, QColor(100, 149, 237)) # 矢车菊蓝
    gradient.setColorAt(1, QColor(65, 105, 225))   # 皇家蓝
    
    # 绘制圆形背景
    painter.setBrush(QBrush(gradient))
    painter.setPen(QPen(QColor(25, 25, 112), max(1, size//16)))  # 深蓝色边框
    margin = size // 8
    painter.drawEllipse(margin, margin, size - 2*margin, size - 2*margin)
    
    # 绘制主要文字"F"
    painter.setPen(QPen(Qt.white))
    font_size = max(12, size // 3)
    painter.setFont(QFont("Arial", font_size, QFont.Bold))
    
    # 计算文字位置
    text_rect = QRect(0, 0, size, size)
    painter.drawText(text_rect, Qt.AlignCenter, "F")
    
    # 绘制小的装饰元素（代表能带结构）
    painter.setPen(QPen(QColor(255, 255, 255, 150), max(1, size//32)))
    
    # 绘制几条代表能带的曲线
    for i in range(3):
        y_offset = size//4 + i * size//8
        painter.drawLine(size//6, y_offset, size*5//6, y_offset + size//16)
    
    painter.end()
    return pixmap

def create_multiple_icons():
    """创建多种尺寸的图标"""
    app = QApplication(sys.argv)
    
    # 创建不同尺寸的图标
    sizes = [16, 24, 32, 48, 64, 128, 256]
    
    for size in sizes:
        pixmap = create_fplo_icon(size)
        filename = f"icon_{size}x{size}.png"
        pixmap.save(filename, "PNG")
        print(f"创建图标: {filename}")
    
    # 创建标准的icon.png (64x64)
    main_icon = create_fplo_icon(64)
    main_icon.save("icon.png", "PNG")
    print("创建主图标: icon.png")
    
    # 创建ICO格式（Windows）
    try:
        # 创建包含多个尺寸的ICO文件
        ico_pixmap = create_fplo_icon(32)
        ico_pixmap.save("icon.ico", "ICO")
        print("创建ICO图标: icon.ico")
    except Exception as e:
        print(f"创建ICO图标失败: {e}")
    
    print("\n图标创建完成！")
    print("可用的图标文件:")
    print("- icon.png (主图标，64x64)")
    print("- icon.ico (Windows图标)")
    print("- icon_*x*.png (各种尺寸)")
    
    return app

def create_custom_icon_with_text(text="FPLO", bg_color=(70, 130, 180), text_color=(255, 255, 255)):
    """创建自定义文字图标"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # 背景
    painter.setBrush(QBrush(QColor(*bg_color)))
    painter.setPen(QPen(QColor(0, 0, 0, 100), 2))
    painter.drawEllipse(2, 2, size-4, size-4)
    
    # 文字
    painter.setPen(QPen(QColor(*text_color)))
    font_size = max(8, size // len(text))
    painter.setFont(QFont("Arial", font_size, QFont.Bold))
    painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, text)
    
    painter.end()
    
    filename = f"custom_icon_{text.lower()}.png"
    pixmap.save(filename, "PNG")
    print(f"创建自定义图标: {filename}")
    
    return pixmap

if __name__ == "__main__":
    print("FPLO可视化工具图标创建器")
    print("=" * 40)
    
    # 创建标准图标
    app = create_multiple_icons()
    
    # 创建一些自定义变体
    print("\n创建自定义变体...")
    create_custom_icon_with_text("FPLO", (34, 139, 34), (255, 255, 255))    # 绿色
    create_custom_icon_with_text("FB", (220, 20, 60), (255, 255, 255))      # 红色
    create_custom_icon_with_text("FP", (255, 140, 0), (255, 255, 255))      # 橙色
    
    print("\n使用说明:")
    print("1. 将生成的icon.png或icon.ico放在程序目录下")
    print("2. 或者放在assets/或images/文件夹中")
    print("3. 重启程序即可看到新图标")
    print("4. 支持的格式: PNG, ICO")
    print("5. 推荐尺寸: 32x32, 64x64")
    
    print("\n图标搜索路径:")
    print("- icon.png")
    print("- icon.ico") 
    print("- assets/icon.png")
    print("- assets/icon.ico")
    print("- images/icon.png")
    print("- images/icon.ico")

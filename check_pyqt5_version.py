#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查PyQt5版本和EchoMode支持
"""

try:
    from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
    print(f"Qt版本: {QT_VERSION_STR}")
    print(f"PyQt5版本: {PYQT_VERSION_STR}")
except ImportError:
    print("PyQt5未安装")

try:
    from PyQt5.QtWidgets import QLineEdit, QInputDialog
    
    print("\n=== 测试EchoMode支持 ===")
    
    # 测试方法1: QLineEdit.EchoMode.Password
    try:
        echo_mode1 = QLineEdit.EchoMode.Password
        print(f"✅ QLineEdit.EchoMode.Password = {echo_mode1}")
    except AttributeError as e:
        print(f"❌ QLineEdit.EchoMode.Password 不支持: {e}")
    
    # 测试方法2: QLineEdit.Password
    try:
        echo_mode2 = QLineEdit.Password
        print(f"✅ QLineEdit.Password = {echo_mode2}")
    except AttributeError as e:
        print(f"❌ QLineEdit.Password 不支持: {e}")
    
    # 测试方法3: 直接使用数值
    echo_mode3 = 2  # QLineEdit.Password的数值
    print(f"✅ 数值方式 = {echo_mode3}")
    
    # 测试所有可能的EchoMode值
    print("\n=== 所有EchoMode值 ===")
    try:
        print(f"Normal: {QLineEdit.Normal}")
        print(f"NoEcho: {QLineEdit.NoEcho}")
        print(f"Password: {QLineEdit.Password}")
        print(f"PasswordEchoOnEdit: {QLineEdit.PasswordEchoOnEdit}")
    except AttributeError as e:
        print(f"某些EchoMode不支持: {e}")
    
    # 检查QInputDialog的属性
    print("\n=== QInputDialog属性 ===")
    input_dialog_attrs = [attr for attr in dir(QInputDialog) if 'Echo' in attr or 'Password' in attr]
    print(f"QInputDialog相关属性: {input_dialog_attrs}")
    
except ImportError as e:
    print(f"导入PyQt5失败: {e}")

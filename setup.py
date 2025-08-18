#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPLO能带权重可视化工具安装脚本
作者: zhujiawen@ustc.mail.edu.cn
"""

from setuptools import setup, find_packages

setup(
    name="fplo-visualizer",
    version="1.0.0",
    description="FPLO能带权重可视化工具",
    author="zhujiawen@ustc.mail.edu.cn",
    author_email="zhujiawen@ustc.mail.edu.cn",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.20.0",
        "matplotlib>=3.4.0",
        "PyQt5>=5.15.0",
        "scipy>=1.7.0",
    ],
    entry_points={
        'console_scripts': [
            'fplo-visualizer=fplo_gui_main:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)

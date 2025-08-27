# -*- coding: utf-8 -*-
"""
日志组件模块：
- LogWidget: 连接到 log_manager 的日志显示组件

保持与原实现一致。
"""

from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QFont

from log_manager import (
    logger,
    log_info,
    log_warning,
    log_error,
)


class LogWidget(QTextEdit):
    """日志显示组件 - 连接到日志管理器"""

    def __init__(self):
        super().__init__()
        self.setMaximumHeight(150)
        self.setFont(QFont("Consolas", 9))
        self.setReadOnly(True)

        # 连接到日志管理器
        logger.log_message.connect(self.on_log_message)

        # 显示初始化信息
        self.append("<span style='color: green;'>[SYSTEM] 日志系统已启动</span>")

    def on_log_message(self, level, message):
        """处理日志管理器的消息"""
        import datetime
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')

        # 根据日志级别设置颜色
        color_map = {
            'DEBUG': '#888888',
            'INFO': '#0066CC',
            'WARNING': '#FF8800',
            'ERROR': '#CC0000',
            'CRITICAL': '#FF0000',
            'STATUS': '#008800',
            'USER': '#6600CC',
            'PERF': '#CC6600',
            'DATA': '#0088CC'
        }

        color = color_map.get(level, '#000000')
        self.append(f"<span style='color: {color};'>[{timestamp}] [{level}] {message}</span>")

        # 自动滚动到底部
        self.moveCursor(self.textCursor().End)

    def log_info(self, message):
        """兼容性方法 - 重定向到日志管理器"""
        log_info(message)

    def log_warning(self, message):
        """兼容性方法 - 重定向到日志管理器"""
        log_warning(message)

    def log_error(self, message):
        """兼容性方法 - 重定向到日志管理器"""
        log_error(message)

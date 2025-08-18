#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPLO可视化工具日志管理器
负责管理程序运行日志和用户操作日志
"""

import os
import sys
import logging
import datetime
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal

class LogManager(QObject):
    """日志管理器 - 统一管理所有日志输出"""
    
    # 信号定义
    log_message = pyqtSignal(str, str)  # (level, message)
    
    def __init__(self):
        super().__init__()
        
        # 创建log文件夹
        self.log_dir = Path("log")
        self.log_dir.mkdir(exist_ok=True)
        
        # 程序启动时间
        self.start_time = datetime.datetime.now()
        
        # 当前体系信息
        self.system_elements = []
        self.current_filename = None
        
        # 日志文件相关
        self.log_file = None
        self.file_logger = None
        
        # 初始化日志系统
        self._setup_logging()
        
        print(f"日志管理器初始化完成，日志目录: {self.log_dir.absolute()}")
    
    def _setup_logging(self):
        """设置日志系统"""
        # 创建临时日志文件（程序结束时会重命名）
        temp_log_file = self.log_dir / f"temp_log_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
        self.log_file = temp_log_file
        
        # 配置文件日志记录器
        self.file_logger = logging.getLogger('fplo_visualizer')
        self.file_logger.setLevel(logging.DEBUG)
        
        # 清除已有的处理器
        for handler in self.file_logger.handlers[:]:
            self.file_logger.removeHandler(handler)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        self.file_logger.addHandler(file_handler)
        
        # 记录程序启动
        self.file_logger.info("="*60)
        self.file_logger.info("FPLO可视化工具启动")
        self.file_logger.info(f"启动时间: {self.start_time}")
        self.file_logger.info(f"Python版本: {sys.version}")
        self.file_logger.info("="*60)
    
    def set_system_info(self, filename, elements=None):
        """设置当前体系信息"""
        self.current_filename = filename
        if elements:
            self.system_elements = sorted(list(set(elements)))
            
        self.info(f"加载体系文件: {filename}")
        if elements:
            self.info(f"体系元素: {', '.join(self.system_elements)}")
    
    def debug(self, message):
        """调试信息 - 只记录到文件"""
        self.file_logger.debug(message)
    
    def info(self, message):
        """一般信息 - 显示在日志区域并记录到文件"""
        self.file_logger.info(message)
        self.log_message.emit("INFO", message)
    
    def warning(self, message):
        """警告信息 - 显示在日志区域并记录到文件"""
        self.file_logger.warning(message)
        self.log_message.emit("WARNING", message)
    
    def error(self, message):
        """错误信息 - 显示在日志区域并记录到文件"""
        self.file_logger.error(message)
        self.log_message.emit("ERROR", message)
    
    def critical(self, message):
        """严重错误 - 显示在日志区域、记录到文件并打印到终端"""
        self.file_logger.critical(message)
        self.log_message.emit("CRITICAL", message)
        print(f"CRITICAL: {message}")  # 严重错误仍然打印到终端
    
    def status(self, message):
        """状态信息 - 显示在日志区域并打印到终端"""
        self.file_logger.info(f"STATUS: {message}")
        self.log_message.emit("STATUS", message)
        print(f"状态: {message}")  # 状态信息打印到终端
    
    def user_action(self, action, details=""):
        """用户操作记录"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        message = f"[{timestamp}] 用户操作: {action}"
        if details:
            message += f" - {details}"
        
        self.file_logger.info(message)
        self.log_message.emit("USER", f"操作: {action}" + (f" - {details}" if details else ""))
    
    def performance(self, operation, duration, details=""):
        """性能记录"""
        message = f"性能: {operation} 耗时 {duration:.2f}秒"
        if details:
            message += f" - {details}"
        
        self.file_logger.info(message)
        self.log_message.emit("PERF", message)
    
    def data_info(self, info_type, data):
        """数据信息记录"""
        message = f"数据: {info_type} - {data}"
        self.file_logger.info(message)
        self.log_message.emit("DATA", message)
    
    def finalize_log(self):
        """程序结束时整理日志文件"""
        end_time = datetime.datetime.now()
        duration = end_time - self.start_time
        
        # 记录程序结束信息
        self.file_logger.info("="*60)
        self.file_logger.info("FPLO可视化工具结束")
        self.file_logger.info(f"结束时间: {end_time}")
        self.file_logger.info(f"运行时长: {duration}")
        self.file_logger.info("="*60)
        
        # 关闭文件处理器
        for handler in self.file_logger.handlers[:]:
            handler.close()
            self.file_logger.removeHandler(handler)
        
        # 生成最终文件名
        if self.system_elements:
            elements_str = "_".join(self.system_elements)
        else:
            elements_str = "Unknown"
        
        start_str = self.start_time.strftime('%Y%m%d_%H%M%S')
        end_str = end_time.strftime('%Y%m%d_%H%M%S')
        
        final_filename = f"{elements_str}_{start_str}_{end_str}.log"
        final_path = self.log_dir / final_filename
        
        # 重命名日志文件
        try:
            if self.log_file.exists():
                self.log_file.rename(final_path)
                print(f"日志已保存到: {final_path}")
        except Exception as e:
            print(f"保存日志文件失败: {e}")
    
    def get_recent_logs(self, count=50):
        """获取最近的日志条目（用于界面显示）"""
        try:
            if self.log_file and self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    return lines[-count:] if len(lines) > count else lines
        except Exception as e:
            print(f"读取日志文件失败: {e}")
        return []
    
    def clear_old_logs(self, days=30):
        """清理旧日志文件"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            
            for log_file in self.log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    self.info(f"清理旧日志文件: {log_file.name}")
                    
        except Exception as e:
            self.error(f"清理旧日志文件失败: {e}")


# 全局日志管理器实例
logger = LogManager()


def setup_global_logger():
    """设置全局日志管理器"""
    return logger


def log_debug(message):
    """全局调试日志函数"""
    logger.debug(message)


def log_info(message):
    """全局信息日志函数"""
    logger.info(message)


def log_warning(message):
    """全局警告日志函数"""
    logger.warning(message)


def log_error(message):
    """全局错误日志函数"""
    logger.error(message)


def log_critical(message):
    """全局严重错误日志函数"""
    logger.critical(message)


def log_status(message):
    """全局状态日志函数"""
    logger.status(message)


def log_user_action(action, details=""):
    """全局用户操作日志函数"""
    logger.user_action(action, details)


def log_performance(operation, duration, details=""):
    """全局性能日志函数"""
    logger.performance(operation, duration, details)


def log_data_info(info_type, data):
    """全局数据信息日志函数"""
    logger.data_info(info_type, data)

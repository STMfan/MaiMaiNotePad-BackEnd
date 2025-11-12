"""
完善的日志配置模块
提供控制台和文件日志记录功能
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
import sys
import traceback
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 添加颜色
        if hasattr(record, 'levelname'):
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # 格式化消息
        formatted = super().format(record)
        return formatted


def setup_logger(
    name: str = "maimnp",
    level: str = "INFO",
    log_dir: str = "./logs",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_dir: 日志文件目录
        max_file_size: 单个日志文件最大大小
        backup_count: 保留的日志文件备份数量
        console_output: 是否输出到控制台
    
    Returns:
        配置好的日志记录器
    """
    # 创建日志目录
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 日志格式
    detailed_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    simple_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(simple_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # 文件处理器 - 所有日志
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, f"{name}.log"),
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(detailed_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # 文件处理器 - 仅错误日志
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, f"{name}_error.log"),
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(detailed_format)
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)
    
    return logger


def log_exception(
    logger: logging.Logger,
    message: str,
    exception: Optional[Exception] = None,
    reraise: bool = False
) -> None:
    """
    记录异常信息
    
    Args:
        logger: 日志记录器
        message: 错误消息
        exception: 异常对象
        reraise: 是否重新抛出异常
    """
    if exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is None:
            # 如果没有当前异常，使用传入的异常
            logger.error(f"{message}: {type(exception).__name__}: {str(exception)}")
            if reraise:
                raise exception
        else:
            # 使用当前异常
            logger.error(f"{message}: {exc_type.__name__}: {exc_value}")
            logger.debug(traceback.format_exc())
            if reraise:
                raise
    else:
        logger.error(message)


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    user_id: Optional[str] = None,
    status_code: int = 200,
    processing_time: Optional[float] = None
) -> None:
    """
    记录API请求
    
    Args:
        logger: 日志记录器
        method: HTTP方法
        path: 请求路径
        user_id: 用户ID
        status_code: 响应状态码
        processing_time: 处理时间(毫秒)
    """
    user_info = f"user={user_id}" if user_id else "anonymous"
    time_info = f"time={processing_time:.2f}ms" if processing_time else ""
    
    logger.info(
        f"API Request: {method} {path} - {user_info} - status={status_code} {time_info}"
    )


def log_file_operation(
    logger: logging.Logger,
    operation: str,
    file_path: str,
    user_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """
    记录文件操作
    
    Args:
        logger: 日志记录器
        operation: 操作类型 (upload, delete, read, etc.)
        file_path: 文件路径
        user_id: 用户ID
        success: 操作是否成功
        error_message: 错误消息
    """
    user_info = f"user={user_id}" if user_id else "anonymous"
    
    if success:
        logger.info(f"File {operation}: {file_path} - {user_info}")
    else:
        logger.error(f"File {operation} failed: {file_path} - {user_info} - error={error_message}")


def log_database_operation(
    logger: logging.Logger,
    operation: str,
    table: str,
    record_id: Optional[str] = None,
    user_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """
    记录数据库操作
    
    Args:
        logger: 日志记录器
        operation: 操作类型 (create, read, update, delete)
        table: 表名
        record_id: 记录ID
        user_id: 用户ID
        success: 操作是否成功
        error_message: 错误消息
    """
    user_info = f"user={user_id}" if user_id else "system"
    record_info = f"id={record_id}" if record_id else ""
    
    if success:
        logger.info(f"DB {operation}: {table} {record_info} - {user_info}")
    else:
        logger.error(f"DB {operation} failed: {table} {record_info} - {user_info} - error={error_message}")


# 创建全局日志记录器
app_logger = setup_logger("maimnp", level="INFO")
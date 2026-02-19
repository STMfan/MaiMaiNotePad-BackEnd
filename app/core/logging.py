"""
Logging configuration module
Provides console and file logging functionality
"""

import logging
import logging.handlers
import os
from pathlib import Path
import sys
import traceback
from typing import Optional

from app.core.config import settings


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Purple
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color
        if hasattr(record, 'levelname'):
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # Format message
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
    Setup logger with console and file handlers.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        max_file_size: Maximum size of a single log file
        backup_count: Number of backup log files to keep
        console_output: Whether to output to console
    
    Returns:
        Configured logger instance
    """
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Log formats
    detailed_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    simple_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(simple_format)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler - all logs
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
    
    # File handler - error logs only
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
    Log exception information.
    
    Args:
        logger: Logger instance
        message: Error message
        exception: Exception object
        reraise: Whether to re-raise the exception
    """
    if exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is None:
            # If no current exception, use the passed exception
            logger.error(f"{message}: {type(exception).__name__}: {str(exception)}")
            if reraise:
                raise exception
        else:
            # Use current exception
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
    Log API request.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        user_id: User ID
        status_code: Response status code
        processing_time: Processing time in milliseconds
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
    Log file operation.
    
    Args:
        logger: Logger instance
        operation: Operation type (upload, delete, read, etc.)
        file_path: File path
        user_id: User ID
        success: Whether operation succeeded
        error_message: Error message if failed
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
    Log database operation.
    
    Args:
        logger: Logger instance
        operation: Operation type (create, read, update, delete)
        table: Table name
        record_id: Record ID
        user_id: User ID
        success: Whether operation succeeded
        error_message: Error message if failed
    """
    user_info = f"user={user_id}" if user_id else "system"
    record_info = f"id={record_id}" if record_id else ""
    
    if success:
        logger.info(f"DB {operation}: {table} {record_info} - {user_info}")
    else:
        logger.error(f"DB {operation} failed: {table} {record_info} - {user_info} - error={error_message}")


# Create global logger instance
app_logger = setup_logger("maimnp", level=settings.LOG_LEVEL)
app_logger.info("Logging system initialized")
app_logger.info(f"Log level set to {settings.LOG_LEVEL}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
异常处理工具模块

提供统一的异常处理机制，包括：
- 结构化错误信息生成
- 异常类型精确捕获
- 资源管理优化
- 统一的异常处理流程
"""

import os
import sys
import traceback
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple


class ErrorInfo:
    """结构化错误信息类"""
    def __init__(self, exception: Exception, module: str, function: str, line: int):
        self.exception = exception
        self.exception_type = type(exception).__name__
        self.module = module
        self.function = function
        self.line = line
        self.timestamp = datetime.now().isoformat()
        self.message = str(exception)
        self.traceback = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp,
            "exception_type": self.exception_type,
            "module": self.module,
            "function": self.function,
            "line": self.line,
            "message": self.message,
            "traceback": self.traceback
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"[{self.timestamp}] {self.exception_type} in {self.module}.{self.function}:{self.line} - {self.message}"


def get_error_info(exception: Exception) -> ErrorInfo:
    """获取错误信息
    
    参数：
    - exception: Exception, 异常对象
    
    返回：
    - ErrorInfo, 结构化错误信息
    """
    # 获取调用栈信息
    tb_lines = traceback.extract_tb(exception.__traceback__)
    if tb_lines:
        # 获取最接近异常发生的栈帧
        last_frame = tb_lines[-1]
        module = last_frame.filename.split(os.sep)[-1].replace('.py', '')
        function = last_frame.name
        line = last_frame.lineno
    else:
        module = "unknown"
        function = "unknown"
        line = 0
    
    return ErrorInfo(exception, module, function, line)


def log_error(error_info: ErrorInfo, logger: Optional[logging.Logger] = None):
    """记录错误信息
    
    参数：
    - error_info: ErrorInfo, 结构化错误信息
    - logger: Optional[logging.Logger], 日志记录器
    """
    if not logger:
        logger = logging.getLogger(__name__)
    
    logger.error(str(error_info))
    logger.debug(f"Traceback:\n{error_info.traceback}")


def handle_exception(exception: Exception, logger: Optional[logging.Logger] = None, 
                    context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
    """处理异常
    
    参数：
    - exception: Exception, 异常对象
    - logger: Optional[logging.Logger], 日志记录器
    - context: Optional[Dict[str, Any]], 上下文信息
    
    返回：
    - ErrorInfo, 结构化错误信息
    """
    error_info = get_error_info(exception)
    
    # 记录上下文信息
    if context:
        context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
        error_info.message = f"{error_info.message} | Context: {context_str}"
    
    # 记录错误
    log_error(error_info, logger)
    
    return error_info


def safe_execute(func, *args, **kwargs) -> Tuple[Optional[Any], Optional[ErrorInfo]]:
    """安全执行函数
    
    参数：
    - func: callable, 要执行的函数
    - *args: 函数参数
    - **kwargs: 函数关键字参数
    
    返回：
    - Tuple[Optional[Any], Optional[ErrorInfo]], (返回值, 错误信息)
    """
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        error_info = get_error_info(e)
        return None, error_info


class ResourceManager:
    """资源管理器
    
    确保资源在使用后正确释放，即使发生异常
    """
    
    def __init__(self):
        self.resources = []
    
    def register(self, resource, close_method='close'):
        """注册资源
        
        参数：
        - resource: 资源对象
        - close_method: str, 关闭方法名
        """
        self.resources.append((resource, close_method))
        return resource
    
    def __enter__(self):
        """进入上下文"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，释放所有资源"""
        for resource, close_method in reversed(self.resources):
            try:
                if hasattr(resource, close_method):
                    getattr(resource, close_method)()
            except Exception as e:
                # 记录释放资源时的错误，但不影响主流程
                error_info = get_error_info(e)
                logger = logging.getLogger(__name__)
                logger.warning(f"释放资源失败: {error_info}")
        return False  # 不抑制异常


def handle_specific_exceptions(func):
    """装饰器：记录常见异常类型的结构化日志，并重新抛出异常。
    
    【设计原则】
    该装饰器只负责"记录"，不负责"吞掉"异常。
    异常被记录后会原样重新抛出，由调用方决定如何处理
    （返回默认值、向用户报错、还是继续传播）。
    
    这样做的原因：
    - 以前统一 return None，导致 open_document() 在 FileNotFoundError 时
      也返回 None，调用方无法区分"文件不存在"和"其他错误"。
    - 现在各业务方法在 except 块中自己决定返回 False/None/默认值，
      并且可以针对不同异常类型采取不同策略。
    
    【用法】
    @handle_specific_exceptions
    def my_func(...) -> bool:
        ...
        # 如果抛出 FileNotFoundError，装饰器会记录日志后重新 raise
        # 调用方需要 try/except，或让异常继续向上传播
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _LOGGED_EXCEPTIONS = (
            FileNotFoundError,
            PermissionError,
            IOError,
            ValueError,
            TypeError,
        )
        try:
            return func(*args, **kwargs)
        except _LOGGED_EXCEPTIONS as e:
            logger = logging.getLogger(func.__module__)
            handle_exception(e, logger, {
                "function": func.__name__,
            })
            raise  # 重新抛出，由调用方决定如何响应
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            handle_exception(e, logger, {
                "function": func.__name__,
            })
            raise

    return wrapper
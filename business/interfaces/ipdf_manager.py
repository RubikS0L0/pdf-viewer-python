#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF管理器接口

定义PDF文档管理的核心功能
"""

from abc import ABC, abstractmethod
from typing import Optional
from PyQt6.QtCore import QMutex


class IPDFManager(ABC):
    """PDF管理器接口"""
    
    @abstractmethod
    def open(self, file_path: str) -> bool:
        """打开PDF文档
        
        参数：
        - file_path: str, PDF文件路径
        
        返回：
        - bool: 打开成功返回True，否则返回False
        """
        pass
    
    @abstractmethod
    def close(self) -> bool:
        """关闭PDF文档
        
        返回：
        - bool: 关闭成功返回True，否则返回False
        """
        pass
    
    @property
    @abstractmethod
    def page_count(self) -> int:
        """获取文档页数"""
        pass
    
    @property
    @abstractmethod
    def is_open(self) -> bool:
        """检查是否有文档打开"""
        pass
    
    @abstractmethod
    def get_document(self) -> Optional[object]:
        """获取文档对象
        
        返回：
        - Optional[object]: PDF文档对象
        """
        pass
    
    @abstractmethod
    def get_document_mutex(self) -> Optional[QMutex]:
        """获取文档访问锁
        
        返回：
        - Optional[QMutex]: 文档访问锁
        """
        pass
    
    @abstractmethod
    def get_file_path(self) -> Optional[str]:
        """获取当前打开的文件路径
        
        返回：
        - Optional[str]: 文件路径
        """
        pass

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
页面缓存接口

定义PDF页面缓存的核心功能
"""

from abc import ABC, abstractmethod
from typing import Optional
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QMutex


class IPageCache(ABC):
    """页面缓存接口"""
    
    @abstractmethod
    def get_page(self, page_num: int, zoom_level: float) -> Optional[QPixmap]:
        """从缓存中获取页面
        
        参数：
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别
        
        返回：
        - QPixmap: 缓存的QPixmap对象，不存在则返回None
        """
        pass
    
    @abstractmethod
    def add_page(self, page_num: int, zoom_level: float, pixmap: QPixmap) -> bool:
        """添加页面到缓存
        
        参数：
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别
        - pixmap: QPixmap, 要缓存的QPixmap对象
        
        返回：
        - bool: 添加成功返回True，否则返回False
        """
        pass
    
    @abstractmethod
    def remove_page(self, page_num: int, zoom_level: Optional[float] = None) -> int:
        """从缓存中移除页面
        
        参数：
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，None表示移除该页面的所有缩放级别
        
        返回：
        - int: 移除的缓存项数量
        """
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """
        清空缓存
        
        返回：
        - int: 清空的缓存项数量
        """
        pass
    
    @abstractmethod
    def get_cache_size(self) -> int:
        """
        获取当前缓存大小
        
        返回：
        - int: 当前缓存项数量
        """
        pass
    
    @abstractmethod
    def contains(self, page_num: int, zoom_level: float) -> bool:
        """
        检查缓存中是否包含指定页面
        
        参数：
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        
        返回：
        - bool: 包含返回True，否则返回False
        """
        pass
    
    @abstractmethod
    def preload_pages(self, doc: object, page_num: int, zoom_level: float, doc_mutex: QMutex, preload_range: int = 2) -> int:
        """
        预加载页面到缓存
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 当前页面编号
        - zoom_level: float, 缩放级别
        - doc_mutex: QMutex, 文档访问锁
        - preload_range: int, 预加载范围，前后各preload_range页
        
        返回：
        - int: 预加载成功的页面数量
        """
        pass

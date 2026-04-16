#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
页面渲染器接口

定义PDF页面渲染的核心功能
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Tuple
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QMutex


class IPageRenderer(ABC):
    """页面渲染器接口"""
    
    @abstractmethod
    def render_page(self, doc: object, page_num: int, zoom_level: float = 1.0, doc_mutex: Optional[QMutex] = None) -> Optional[QPixmap]:
        """渲染指定页码的页面（同步方法）
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        
        返回：
        - QPixmap: 渲染后的QPixmap对象，渲染失败则返回None
        """
        pass
    
    @abstractmethod
    def render_page_to_image(self, doc: object, page_num: int, zoom_level: float = 1.0, doc_mutex: Optional[QMutex] = None) -> Optional[QImage]:
        """渲染页面为QImage对象（同步方法）
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        
        返回：
        - QImage: 渲染后的QImage对象，渲染失败则返回None
        """
        pass
    
    @abstractmethod
    def render_page_progressive(self, doc: object, page_num: int, zoom_level: float = 1.0, doc_mutex: Optional[QMutex] = None, callback: Optional[Callable] = None) -> Optional[QPixmap]:
        """渐进式渲染页面
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        - callback: callable, 每级渲染完成后的回调函数
        
        返回：
        - QPixmap: 最终渲染结果
        """
        pass
    
    @abstractmethod
    def queue_progressive_render(self, doc: object, page_num: int, zoom_level: float = 1.0, doc_mutex: Optional[QMutex] = None, priority: int = 0, callback: Optional[Callable] = None) -> int:
        """将渐进式渲染请求加入队列
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        - priority: int, 优先级，数字越小优先级越高
        - callback: callable, 每级渲染完成后的回调函数
        
        返回：
        - int: 请求ID
        """
        pass
    
    @abstractmethod
    def get_page_size(self, doc: object, page_num: int, zoom_level: float = 1.0, doc_mutex: Optional[QMutex] = None) -> Tuple[float, float]:
        """获取指定缩放级别下的页面尺寸
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        
        返回：
        - tuple: (width, height)，页面尺寸，获取失败则返回(0, 0)
        """
        pass
    
    @abstractmethod
    def batch_render(self, doc: object, page_nums: list, zoom_level: float = 1.0, doc_mutex: Optional[QMutex] = None, priority: int = 0, callback: Optional[Callable] = None) -> list:
        """批量渲染页面
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_nums: list, 页面编号列表
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        - priority: int, 优先级，数字越小优先级越高
        - callback: callable, 每个页面渲染完成后的回调函数
        
        返回：
        - list: 请求ID列表
        """
        pass

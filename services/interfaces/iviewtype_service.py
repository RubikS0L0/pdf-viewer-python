#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视图类型服务接口

为视图类型提供所需的功能，替代直接依赖PDFMainWindow
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from PyQt6.QtGui import QPixmap


class IViewtypeService(ABC):
    """视图类型服务接口"""
    
    @abstractmethod
    def get_current_page(self) -> int:
        """获取当前页码"""
        pass
    
    @abstractmethod
    def get_total_pages(self) -> int:
        """获取总页数"""
        pass
    
    @abstractmethod
    def get_zoom_level(self) -> float:
        """获取当前缩放级别"""
        pass
    
    @abstractmethod
    def set_zoom_level(self, zoom_level: float) -> None:
        """设置缩放级别"""
        pass
    
    @abstractmethod
    def get_page_pixmap(self, page_num: int) -> QPixmap:
        """获取指定页码的页面Pixmap（同步方法）"""
        pass
    
    @abstractmethod
    def get_page_pixmap_async(self, page_num: int, callback) -> int:
        """异步获取指定页码的页面Pixmap"""
        pass
    
    @abstractmethod
    def get_two_pages_pixmap_async(self, page1_num: int, page2_num: int, callback) -> None:
        """异步获取双页的合并Pixmap"""
        pass
    
    @abstractmethod
    def get_page_size(self, page_num: int, zoom_level: float) -> Tuple[float, float]:
        """获取指定页码的页面尺寸"""
        pass
    
    @abstractmethod
    def update_content_layout(self) -> None:
        """更新内容布局"""
        pass
    
    @abstractmethod
    def show_page(self, page_num: int) -> None:
        """显示指定页码的页面"""
        pass
    
    @abstractmethod
    def get_detection_results(self) -> dict:
        """获取检测结果"""
        pass
    
    @abstractmethod
    def get_results_mutex(self):
        """获取结果互斥锁"""
        pass
    
    @abstractmethod
    def get_selecting(self) -> bool:
        """获取选择状态"""
        pass
    
    @abstractmethod
    def set_selecting(self, value: bool) -> None:
        """设置选择状态"""
        pass
    
    @abstractmethod
    def get_select_start_pdf(self):
        """获取选择起始PDF坐标"""
        pass
    
    @abstractmethod
    def set_select_start_pdf(self, value) -> None:
        """设置选择起始PDF坐标"""
        pass
    
    @abstractmethod
    def get_select_end_pdf(self):
        """获取选择结束PDF坐标"""
        pass
    
    @abstractmethod
    def set_select_end_pdf(self, value) -> None:
        """设置选择结束PDF坐标"""
        pass

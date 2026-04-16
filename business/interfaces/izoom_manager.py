#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缩放管理器接口

定义PDF页面缩放管理的核心功能
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Tuple


class IZoomManager(ABC):
    """缩放管理器接口"""
    
    @abstractmethod
    def add_observer(self, observer: object) -> None:
        """添加观察者
        
        参数：
        - observer: object, 观察者对象，必须实现on_zoom_changed方法
        """
        pass
    
    @abstractmethod
    def remove_observer(self, observer: object) -> None:
        """移除观察者
        
        参数：
        - observer: object, 观察者对象
        """
        pass
    
    @abstractmethod
    def set_zoom_level(self, zoom_level: float, zoom_mode: str = "custom") -> float:
        """设置缩放级别
        
        参数：
        - zoom_level: float, 缩放级别
        - zoom_mode: str, 缩放模式，默认为"custom"
        
        返回：
        - float: 实际设置的缩放级别（经过限制后）
        """
        pass
    
    @abstractmethod
    def get_zoom_level(self) -> float:
        """获取当前缩放级别
        
        返回：
        - float: 当前缩放级别
        """
        pass
    
    @abstractmethod
    def get_zoom_mode(self) -> str:
        """获取当前缩放模式
        
        返回：
        - str: 当前缩放模式
        """
        pass
    
    @abstractmethod
    def zoom_in(self, step: Optional[float] = None) -> float:
        """
        放大页面
        
        参数：
        - step: float, 放大步长
        
        返回：
        - float: 放大后的缩放级别
        """
        pass
    
    @abstractmethod
    def zoom_out(self, step: Optional[float] = None) -> float:
        """
        缩小页面
        
        参数：
        - step: float, 缩小步长
        
        返回：
        - float: 缩小后的缩放级别
        """
        pass
    
    @abstractmethod
    def reset_zoom(self) -> float:
        """
        重置缩放级别为实际大小
        
        返回：
        - float: 重置后的缩放级别（1.0）
        """
        pass
    
    @abstractmethod
    def calculate_fit_page_zoom(self, page_size: Tuple[float, float], viewport_size: Tuple[float, float]) -> float:
        """
        计算适合页面的缩放级别
        
        参数：
        - page_size: tuple, 页面尺寸 (width, height)
        - viewport_size: tuple, 视口尺寸 (width, height)
        
        返回：
        - float: 适合页面的缩放级别
        """
        pass
    
    @abstractmethod
    def calculate_fit_width_zoom(self, page_width: float, viewport_width: float) -> float:
        """
        计算适合宽度的缩放级别
        
        参数：
        - page_width: float, 页面宽度
        - viewport_width: float, 视口宽度
        
        返回：
        - float: 适合宽度的缩放级别
        """
        pass

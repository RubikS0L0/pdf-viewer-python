#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
事件总线

提供事件发布和订阅机制，基于PyQt的信号槽机制，
用于在不同组件之间传递事件，避免直接调用导致的耦合。
"""

import logging
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, List, Callable, Any


class EventBus(QObject):
    """事件总线类"""
    
    # 定义事件信号
    # 缩放事件: (zoom_level: float, zoom_mode: str)
    zoom_changed = pyqtSignal(float, str)
    
    # 渲染完成事件: (page_num: int, result: object, is_final: bool)
    render_completed = pyqtSignal(int, object, bool)
    
    # 页面更新事件: (page_num: int)
    page_updated = pyqtSignal(int)
    
    # 文档打开事件: (file_path: str, page_count: int)
    document_opened = pyqtSignal(str, int)
    
    # 文档关闭事件
    document_closed = pyqtSignal()
    
    def __init__(self):
        """初始化事件总线"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # 存储自定义事件的订阅者
        self._custom_events: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_name: str, callback: Callable) -> None:
        """订阅自定义事件
        
        参数：
        - event_name: str, 事件名称
        - callback: Callable, 事件回调函数
        """
        if event_name not in self._custom_events:
            self._custom_events[event_name] = []
        
        if callback not in self._custom_events[event_name]:
            self._custom_events[event_name].append(callback)
    
    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """取消订阅自定义事件
        
        参数：
        - event_name: str, 事件名称
        - callback: Callable, 事件回调函数
        """
        if event_name in self._custom_events:
            if callback in self._custom_events[event_name]:
                self._custom_events[event_name].remove(callback)
    
    def publish(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        """发布自定义事件
        
        参数：
        - event_name: str, 事件名称
        - *args: 位置参数
        - **kwargs: 关键字参数
        """
        if event_name in self._custom_events:
            for callback in self._custom_events[event_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"执行事件回调失败: {str(e)}")

    
    def publish_zoom_changed(self, zoom_level: float, zoom_mode: str = "custom") -> None:
        """发布缩放变化事件
        
        参数：
        - zoom_level: float, 缩放级别
        - zoom_mode: str, 缩放模式
        """
        from utils.constants import Constants
        # 避免频繁的事件发布，只有当缩放级别或模式真正变化时才发布
        if not hasattr(self, '_last_zoom_level') or not hasattr(self, '_last_zoom_mode'):
            self._last_zoom_level = zoom_level
            self._last_zoom_mode = zoom_mode
            self.zoom_changed.emit(zoom_level, zoom_mode)
        elif abs(self._last_zoom_level - zoom_level) > Constants.ZOOM_CHANGE_THRESHOLD.value or self._last_zoom_mode != zoom_mode:
            self._last_zoom_level = zoom_level
            self._last_zoom_mode = zoom_mode
            self.zoom_changed.emit(zoom_level, zoom_mode)
    
    def publish_render_completed(self, page_num: int, result: object, is_final: bool = True) -> None:
        """发布渲染完成事件
        
        参数：
        - page_num: int, 页面编号
        - result: object, 渲染结果
        - is_final: bool, 是否为最终结果
        """
        self.render_completed.emit(page_num, result, is_final)
    
    def publish_page_updated(self, page_num: int) -> None:
        """发布页面更新事件
        
        参数：
        - page_num: int, 页面编号
        """
        self.page_updated.emit(page_num)
    
    def publish_document_opened(self, file_path: str, page_count: int) -> None:
        """发布文档打开事件
        
        参数：
        - file_path: str, 文件路径
        - page_count: int, 页面数量
        """
        self.document_opened.emit(file_path, page_count)
    
    def publish_document_closed(self) -> None:
        """发布文档关闭事件"""
        self.document_closed.emit()


# 创建全局事件总线实例
event_bus = EventBus()

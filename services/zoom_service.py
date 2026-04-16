#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缩放服务

负责管理缩放级别和模式，提供缩放操作接口，
通过事件总线发布缩放事件，避免直接调用导致的耦合。
"""

import logging
import threading
from typing import Optional
from utils.constants import Constants
from services.event_bus import event_bus


class ZoomService:
    """缩放服务类"""
    
    def __init__(self):
        """初始化缩放服务"""
        self.logger = logging.getLogger(__name__)
        
        # 当前缩放级别，默认为1.0
        self._zoom_level = 1.0
        
        # 缩放模式：actual/fit_page/fit_width/custom
        self._zoom_mode = "actual"
        
        # 使用线程锁保证原子操作
        self._lock = threading.RLock()
        
        # 缩放历史
        self._zoom_history = []
        self._history_index = -1
        self._max_history_size = 10
        
        # 观察者列表
        self._observers = []
        self._observers_lock = threading.RLock()
    
    def add_observer(self, observer):
        """添加观察者
        
        参数：
        - observer: object, 观察者对象，必须实现on_zoom_changed方法
        """
        with self._observers_lock:
            if observer not in self._observers:
                self._observers.append(observer)
    
    def remove_observer(self, observer):
        """移除观察者
        
        参数：
        - observer: object, 观察者对象
        """
        with self._observers_lock:
            if observer in self._observers:
                self._observers.remove(observer)
    
    def _notify_observers(self, zoom_level: float, zoom_mode: str):
        """通知所有观察者缩放级别变化
        
        参数：
        - zoom_level: float, 缩放级别
        - zoom_mode: str, 缩放模式
        """
        with self._observers_lock:
            observers = self._observers.copy()
        
        for observer in observers:
            if hasattr(observer, 'on_zoom_changed'):
                try:
                    observer.on_zoom_changed(zoom_level)
                except Exception as e:
                    self.logger.error(f"通知观察者缩放变化失败: {str(e)}")
    
    def get_zoom_level(self) -> float:
        """获取当前缩放级别
        
        返回：
        - float: 当前缩放级别
        """
        with self._lock:
            return self._zoom_level
    
    def get_zoom_mode(self) -> str:
        """获取当前缩放模式
        
        返回：
        - str: 当前缩放模式
        """
        with self._lock:
            return self._zoom_mode
    
    def set_zoom_level(self, zoom_level: float, zoom_mode: str = "custom") -> float:
        """设置缩放级别
        
        参数：
        - zoom_level: float, 缩放级别
        - zoom_mode: str, 缩放模式，默认为"custom"
        
        返回：
        - float: 实际设置的缩放级别（经过限制后）
        """
        try:
            with self._lock:
                # 限制缩放级别在合理范围内
                actual_zoom = self._clamp_zoom_level(zoom_level)
                
                old_zoom = self._zoom_level
                old_mode = self._zoom_mode
                
                # 只有当缩放级别或模式真正变化时才更新
                if abs(old_zoom - actual_zoom) > Constants.ZOOM_CHANGE_THRESHOLD.value or old_mode != zoom_mode:
                    # 更新缩放级别和模式
                    self._zoom_level = actual_zoom
                    self._zoom_mode = zoom_mode
                    
                    # 记录缩放历史
                    self._add_to_history(actual_zoom, zoom_mode)
                    
                    # 通知观察者
                    self._notify_observers(actual_zoom, zoom_mode)
                    
                    # 发布缩放事件
                    event_bus.publish_zoom_changed(actual_zoom, zoom_mode)
                
                return actual_zoom
        except Exception as e:
            self.logger.error(f"设置缩放级别失败：{str(e)}")
            return self._zoom_level
    
    def zoom_in(self, step: Optional[float] = None) -> float:
        """
        放大页面
        
        参数：
        - step: float, 放大步长，默认为Constants.ZOOM_DELTA
        
        返回：
        - float: 放大后的缩放级别
        """
        try:
            with self._lock:
                # 使用默认步长或传入的步长
                zoom_delta = step or Constants.ZOOM_DELTA.value
                
                # 计算新的缩放级别
                old_zoom = self._zoom_level
                new_zoom = self._zoom_level * zoom_delta
                
                # 限制缩放级别并设置
                actual_zoom = self._clamp_zoom_level(new_zoom)
                
                # 更新缩放级别和模式
                self._zoom_level = actual_zoom
                self._zoom_mode = "custom"
                
                # 记录缩放历史
                self._add_to_history(actual_zoom, "custom")
                
                # 如果缩放级别发生变化，通知观察者并发布缩放事件
                if abs(old_zoom - actual_zoom) > Constants.ZOOM_CHANGE_THRESHOLD.value:
                    self._notify_observers(actual_zoom, "custom")
                    event_bus.publish_zoom_changed(actual_zoom, "custom")
                
                return actual_zoom
        except Exception as e:
            self.logger.error(f"放大页面失败：{str(e)}")
            return self._zoom_level
    
    def zoom_out(self, step: Optional[float] = None) -> float:
        """缩小页面
        
        参数：
        - step: float, 缩小步长，默认为1/Constants.ZOOM_DELTA
        
        返回：
        - float: 缩小后的缩放级别
        """
        try:
            with self._lock:
                # 使用默认步长或传入的步长
                zoom_delta = step or (1.0 / Constants.ZOOM_DELTA.value)
                
                # 计算新的缩放级别
                old_zoom = self._zoom_level
                new_zoom = self._zoom_level * zoom_delta
                
                # 限制缩放级别并设置
                actual_zoom = self._clamp_zoom_level(new_zoom)
                
                # 更新缩放级别和模式
                self._zoom_level = actual_zoom
                self._zoom_mode = "custom"
                
                # 记录缩放历史
                self._add_to_history(actual_zoom, "custom")
                
                # 如果缩放级别发生变化，通知观察者并发布缩放事件
                if abs(old_zoom - actual_zoom) > Constants.ZOOM_CHANGE_THRESHOLD.value:
                    self._notify_observers(actual_zoom, "custom")
                    event_bus.publish_zoom_changed(actual_zoom, "custom")
                
                return actual_zoom
        except Exception as e:
            self.logger.error(f"缩小页面失败：{str(e)}")
            return self._zoom_level
    
    def reset_zoom(self) -> float:
        """重置缩放级别为实际大小
        
        返回：
        - float: 重置后的缩放级别（1.0）
        """
        try:
            with self._lock:
                old_zoom = self._zoom_level
                old_mode = self._zoom_mode
                
                # 重置缩放级别和模式
                self._zoom_level = 1.0
                self._zoom_mode = "actual"
                
                # 记录缩放历史
                self._add_to_history(1.0, "actual")
                
                # 如果缩放级别或模式发生变化，通知观察者并发布缩放事件
                if abs(old_zoom - 1.0) > Constants.ZOOM_CHANGE_THRESHOLD.value or old_mode != "actual":
                    self._notify_observers(1.0, "actual")
                    event_bus.publish_zoom_changed(1.0, "actual")
                
                return self._zoom_level
        except Exception as e:
            self.logger.error(f"重置缩放级别失败：{str(e)}")
            return self._zoom_level
    
    def fit_page(self, page_size: tuple, viewport_size: tuple) -> float:
        """计算并设置适合页面的缩放级别
        
        参数：
        - page_size: tuple, 页面尺寸 (width, height)
        - viewport_size: tuple, 视口尺寸 (width, height)
        
        返回：
        - float: 适合页面的缩放级别
        """
        try:
            page_width, page_height = page_size
            viewport_width, viewport_height = viewport_size
            
            # 添加边距，确保页面在视口中有适当的留白
            margin = Constants.PAGE_MARGIN.value  # 使用常量定义边距
            
            # 预留滚动条空间（假设滚动条宽度为 15 像素）
            scrollbar_width = 15
            scrollbar_height = 15
            
            # 计算可用空间（考虑边距和滚动条）
            available_width = viewport_width - 2 * margin - scrollbar_width
            available_height = viewport_height - 2 * margin - scrollbar_height
            
            # 确保可用空间不为负
            available_width = max(available_width, 50)
            available_height = max(available_height, 50)
            
            # 计算宽度和高度方向的缩放比例
            width_ratio = available_width / page_width
            height_ratio = available_height / page_height
            
            # 取较小的比例，确保整个页面都能显示
            fit_zoom = min(width_ratio, height_ratio)
            
            # 设置缩放级别
            return self.set_zoom_level(fit_zoom, "fit_page")
        except Exception as e:
            self.logger.error(f"计算适合页面的缩放级别失败：{str(e)}")
            return self._zoom_level
    
    def fit_width(self, page_width: float, viewport_width: float) -> float:
        """计算并设置适合宽度的缩放级别
        
        参数：
        - page_width: float, 页面宽度
        - viewport_width: float, 视口宽度
        
        返回：
        - float: 适合宽度的缩放级别
        """
        try:
            # 添加边距，确保页面在视口中有适当的留白
            margin = Constants.PAGE_MARGIN.value  # 使用常量定义边距
            available_width = viewport_width - 2 * margin
            
            # 计算宽度方向的缩放比例
            width_ratio = available_width / page_width
            
            # 设置缩放级别
            return self.set_zoom_level(width_ratio, "fit_width")
        except Exception as e:
            self.logger.error(f"计算适合宽度的缩放级别失败：{str(e)}")
            return self._zoom_level
    
    def _clamp_zoom_level(self, zoom_level: float) -> float:
        """限制缩放级别在合理范围内
        
        参数：
        - zoom_level: float, 原始缩放级别
        
        返回：
        - float: 限制后的缩放级别
        """
        min_zoom = Constants.MIN_ZOOM.value
        max_zoom = Constants.MAX_ZOOM.value
        
        clamped_zoom = max(min(zoom_level, max_zoom), min_zoom)
        
        # 格式化缩放级别，确保一致性
        formatted_zoom = round(clamped_zoom * 100) / 100
        
        return formatted_zoom
    
    def _add_to_history(self, zoom_level: float, zoom_mode: str) -> None:
        """添加缩放操作到历史记录
        
        参数：
        - zoom_level: float, 缩放级别
        - zoom_mode: str, 缩放模式
        """
        # 移除当前索引之后的历史记录
        if self._history_index < len(self._zoom_history) - 1:
            self._zoom_history = self._zoom_history[:self._history_index + 1]
        
        # 添加新的历史记录
        self._zoom_history.append((zoom_level, zoom_mode))
        
        # 限制历史记录大小
        if len(self._zoom_history) > self._max_history_size:
            self._zoom_history.pop(0)
        
        # 更新历史索引
        self._history_index = len(self._zoom_history) - 1
    
    def zoom_undo(self) -> bool:
        """撤销上一次缩放操作
        
        返回：
        - bool: 是否成功撤销
        """
        try:
            with self._lock:
                if self._history_index > 0:
                    self._history_index -= 1
                    zoom_level, zoom_mode = self._zoom_history[self._history_index]
                    old_zoom = self._zoom_level
                    old_mode = self._zoom_mode
                    
                    # 恢复缩放级别和模式
                    self._zoom_level = zoom_level
                    self._zoom_mode = zoom_mode
                    
                    # 通知观察者并发布缩放事件
                    self._notify_observers(zoom_level, zoom_mode)
                    event_bus.publish_zoom_changed(zoom_level, zoom_mode)
                    
                    return True
                return False
        except Exception as e:
            self.logger.error(f"撤销缩放操作失败：{str(e)}")
            return False
    
    def zoom_redo(self) -> bool:
        """重做上一次缩放操作
        
        返回：
        - bool: 是否成功重做
        """
        try:
            with self._lock:
                if self._history_index < len(self._zoom_history) - 1:
                    self._history_index += 1
                    zoom_level, zoom_mode = self._zoom_history[self._history_index]
                    old_zoom = self._zoom_level
                    old_mode = self._zoom_mode
                    
                    # 恢复缩放级别和模式
                    self._zoom_level = zoom_level
                    self._zoom_mode = zoom_mode
                    
                    # 通知观察者并发布缩放事件
                    self._notify_observers(zoom_level, zoom_mode)
                    event_bus.publish_zoom_changed(zoom_level, zoom_mode)
                    
                    return True
                return False
        except Exception as e:
            self.logger.error(f"重做缩放操作失败：{str(e)}")
            return False

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视口管理器服务类

提供集中化的视口尺寸管理功能，包括：
1. 视口尺寸获取的统一接口
2. 视口尺寸变化的自动监听和通知机制
3. 完善的错误处理和边界条件处理

使用方法：
1. 初始化ViewportManager并设置scroll_area
2. 通过get_viewport_width()、get_viewport_height()等方法获取视口尺寸
3. 通过add_observer()方法添加尺寸变化的观察者
4. 观察者需实现on_viewport_size_changed(width, height)方法
"""

import logging
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QEvent
from typing import Optional, List, Callable, Tuple


class ViewportManager(QObject):
    """视口管理器服务类"""
    
    # 视口尺寸变化信号
    viewport_size_changed = pyqtSignal(float, float)
    
    def __init__(self):
        """初始化视口管理器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # 视口尺寸缓存
        self._viewport_width = 0.0
        self._viewport_height = 0.0
        self._viewport_size = (0.0, 0.0)
        
        # 滚动区域引用
        self._scroll_area = None
        
        # 观察者列表
        self._observers = []
        self._observers_lock = threading.RLock()
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 尺寸变化监听标志
        self._listening_enabled = False
    
    def set_scroll_area(self, scroll_area) -> bool:
        """设置滚动区域
        
        参数：
        - scroll_area: QScrollArea, 滚动区域对象
        
        返回：
        - bool: 设置成功返回True，否则返回False
        """
        try:
            with self._lock:
                # 移除旧的滚动区域的事件过滤器
                if self._scroll_area:
                    self._scroll_area.removeEventFilter(self)
                
                # 设置新的滚动区域
                self._scroll_area = scroll_area
                
                # 安装事件过滤器，监听滚动区域的尺寸变化
                if self._scroll_area:
                    self._scroll_area.installEventFilter(self)
                    self._listening_enabled = True
                    # 初始获取视口尺寸
                    self.update_viewport_size()
                    return True
                else:
                    self._listening_enabled = False
                    return False
        except Exception as e:
            self.logger.error(f"设置滚动区域失败: {str(e)}")
            return False
    
    def get_scroll_area(self):
        """获取滚动区域
        
        返回：
        - QScrollArea: 滚动区域对象
        """
        with self._lock:
            return self._scroll_area
    
    def update_viewport_size(self) -> bool:
        """更新视口尺寸
        
        返回：
        - bool: 更新成功返回True，否则返回False
        """
        try:
            with self._lock:
                if not self._scroll_area:
                    self.logger.warning("滚动区域未设置，无法更新视口尺寸")
                    return False
                
                # 检查scroll_area是否有效
                try:
                    # 尝试访问scroll_area的基本属性，检查是否有效
                    _ = self._scroll_area.objectName()
                except RuntimeError as e:
                    if 'wrapped C/C++ object has been deleted' in str(e):
                        self.logger.debug("scroll_area已被删除，无法更新视口尺寸")
                        return False
                    else:
                        raise
                
                # 获取视口
                try:
                    viewport = self._scroll_area.viewport()
                    if not viewport:
                        self.logger.warning("无法获取视口对象")
                        return False
                    
                    # 获取视口尺寸
                    width = viewport.width()
                    height = viewport.height()
                except RuntimeError as e:
                    if 'wrapped C/C++ object has been deleted' in str(e):
                        self.logger.debug("视口已被删除，无法更新视口尺寸")
                        return False
                    else:
                        raise
                
                # 检查尺寸是否变化
                if width == self._viewport_width and height == self._viewport_height:
                    # 尺寸未变化，无需更新
                    return True
                
                # 更新缓存的尺寸
                old_width = self._viewport_width
                old_height = self._viewport_height
                self._viewport_width = width
                self._viewport_height = height
                self._viewport_size = (width, height)
                
                self.logger.debug(f"视口尺寸更新: ({old_width}, {old_height}) -> ({width}, {height})")
                
                # 通知观察者
                self._notify_observers(width, height)
                
                # 发射信号
                self.viewport_size_changed.emit(width, height)
                
                return True
        except RuntimeError as e:
            if 'wrapped C/C++ object has been deleted' in str(e):
                # 忽略已删除对象的错误
                self.logger.debug("忽略已删除对象的错误")
                return False
            else:
                self.logger.error(f"更新视口尺寸失败: {str(e)}")
                return False
        except Exception as e:
            self.logger.error(f"更新视口尺寸失败: {str(e)}")
            return False
    
    def get_viewport_width(self) -> float:
        """获取当前视口宽度
        
        返回：
        - float: 视口宽度
        """
        with self._lock:
            return self._viewport_width
    
    def get_viewport_height(self) -> float:
        """获取当前视口高度
        
        返回：
        - float: 视口高度
        """
        with self._lock:
            return self._viewport_height
    
    def get_viewport_size(self) -> Tuple[float, float]:
        """获取当前视口尺寸
        
        返回：
        - Tuple[float, float]: 视口尺寸 (width, height)
        """
        with self._lock:
            return self._viewport_size
    
    def get_viewport_center(self) -> Tuple[float, float]:
        """获取当前视口中心坐标
        
        返回：
        - Tuple[float, float]: 视口中心坐标 (x, y)
        """
        with self._lock:
            center_x = self._viewport_width / 2
            center_y = self._viewport_height / 2
            return (center_x, center_y)
    
    def add_observer(self, observer) -> bool:
        """添加视口尺寸变化的观察者
        
        参数：
        - observer: object, 观察者对象，需实现on_viewport_size_changed(width, height)方法
        
        返回：
        - bool: 添加成功返回True，否则返回False
        """
        try:
            with self._observers_lock:
                # 检查观察者是否已存在
                if observer in self._observers:
                    return True
                
                # 检查观察者是否实现了必要的方法
                if not hasattr(observer, 'on_viewport_size_changed'):
                    self.logger.warning("观察者未实现on_viewport_size_changed方法")
                    return False
                
                # 添加观察者
                self._observers.append(observer)
                self.logger.debug(f"添加视口尺寸变化观察者: {observer.__class__.__name__}")
                return True
        except Exception as e:
            self.logger.error(f"添加观察者失败: {str(e)}")
            return False
    
    def remove_observer(self, observer) -> bool:
        """移除视口尺寸变化的观察者
        
        参数：
        - observer: object, 观察者对象
        
        返回：
        - bool: 移除成功返回True，否则返回False
        """
        try:
            with self._observers_lock:
                if observer in self._observers:
                    self._observers.remove(observer)
                    self.logger.debug(f"移除视口尺寸变化观察者: {observer.__class__.__name__}")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"移除观察者失败: {str(e)}")
            return False
    
    def _notify_observers(self, width: float, height: float) -> None:
        """通知所有观察者视口尺寸变化
        
        参数：
        - width: float, 新的视口宽度
        - height: float, 新的视口高度
        """
        try:
            with self._observers_lock:
                observers = self._observers.copy()
            
            for observer in observers:
                if hasattr(observer, 'on_viewport_size_changed'):
                    try:
                        observer.on_viewport_size_changed(width, height)
                    except Exception as e:
                        self.logger.error(f"通知观察者视口尺寸变化失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"通知观察者失败: {str(e)}")
    
    def eventFilter(self, obj, event) -> bool:
        """事件过滤器，用于监听视口尺寸变化
        
        参数：
        - obj: QObject, 事件源对象
        - event: QEvent, 事件对象
        
        返回：
        - bool: 是否拦截事件
        """
        if not self._listening_enabled:
            return super().eventFilter(obj, event)
        
        # 监听调整大小事件
        if event.type() == QEvent.Type.Resize:
            # 延迟更新，避免频繁触发
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self.update_viewport_size)
        
        return super().eventFilter(obj, event)
    
    def enable_listening(self, enabled: bool) -> None:
        """启用或禁用尺寸变化监听
        
        参数：
        - enabled: bool, 是否启用监听
        """
        with self._lock:
            self._listening_enabled = enabled
            if enabled and self._scroll_area:
                # 立即更新一次视口尺寸
                self.update_viewport_size()
    
    def is_listening_enabled(self) -> bool:
        """检查是否启用了尺寸变化监听
        
        返回：
        - bool: 是否启用了监听
        """
        with self._lock:
            return self._listening_enabled
    
    def clear(self) -> None:
        """清理资源
        """
        try:
            self.logger.debug("开始清理视口管理器资源")
            with self._lock:
                # 移除事件过滤器
                if self._scroll_area:
                    try:
                        # 尝试访问scroll_area的基本属性，检查是否有效
                        # 这会触发RuntimeError如果对象已被删除
                        _ = self._scroll_area.objectName()
                        self._scroll_area.removeEventFilter(self)
                        self.logger.debug("成功移除事件过滤器")
                    except RuntimeError as e:
                        if 'wrapped C/C++ object has been deleted' in str(e):
                            # 忽略已删除对象的错误
                            self.logger.debug("scroll_area已被删除，跳过事件过滤器移除")
                            pass
                        else:
                            raise
                    except Exception as e:
                        # 忽略其他可能的异常
                        self.logger.debug(f"移除事件过滤器时发生异常: {str(e)}")
                        pass
                
                # 清空观察者列表
                with self._observers_lock:
                    self._observers.clear()
                    self.logger.debug("成功清空观察者列表")
                
                # 重置状态
                self._scroll_area = None
                self._viewport_width = 0.0
                self._viewport_height = 0.0
                self._viewport_size = (0.0, 0.0)
                self._listening_enabled = False
                
                self.logger.debug("视口管理器资源已清理")
        except RuntimeError as e:
            if 'wrapped C/C++ object has been deleted' in str(e):
                # 忽略已删除对象的错误
                self.logger.debug("忽略已删除对象的错误")
                pass
            else:
                self.logger.error(f"清理资源失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"清理资源失败: {str(e)}")
    
    def __del__(self):
        """析构函数，清理资源
        """
        try:
            self.clear()
        except Exception:
            # 忽略析构函数中的异常
            pass


# 创建全局视口管理器实例
viewport_manager = ViewportManager()

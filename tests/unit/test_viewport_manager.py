#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ViewportManager单元测试

测试ViewportManager的核心功能
"""

import pytest
from PyQt6.QtWidgets import QApplication, QScrollArea, QWidget
from PyQt6.QtCore import QEvent, QSize
from ui.viewport_manager import ViewportManager


class TestViewportManager:
    """ViewportManager单元测试类"""
    
    @classmethod
    def setup_class(cls):
        """设置测试类环境"""
        # 创建QApplication实例
        cls.app = QApplication([])
    
    @classmethod
    def teardown_class(cls):
        """清理测试类环境"""
        # 清理QApplication实例
        cls.app.quit()
    
    def setup_method(self):
        """设置测试环境"""
        self.viewport_manager = ViewportManager()
        self.scroll_area = QScrollArea()
        self.widget = QWidget()
        self.scroll_area.setWidget(self.widget)
    
    def teardown_method(self):
        """清理测试环境"""
        self.viewport_manager.clear()
    
    def test_initial_state(self):
        """测试初始状态"""
        assert self.viewport_manager.get_viewport_width() == 0.0
        assert self.viewport_manager.get_viewport_height() == 0.0
        assert self.viewport_manager.get_viewport_size() == (0.0, 0.0)
        assert self.viewport_manager.get_viewport_center() == (0.0, 0.0)
        assert not self.viewport_manager.is_listening_enabled()
        assert self.viewport_manager.get_scroll_area() is None
    
    def test_set_scroll_area(self):
        """测试设置滚动区域"""
        # 测试设置有效的滚动区域
        result = self.viewport_manager.set_scroll_area(self.scroll_area)
        assert result is True
        assert self.viewport_manager.get_scroll_area() == self.scroll_area
        assert self.viewport_manager.is_listening_enabled()
        
        # 测试设置None
        result = self.viewport_manager.set_scroll_area(None)
        assert result is False
        assert self.viewport_manager.get_scroll_area() is None
        assert not self.viewport_manager.is_listening_enabled()
    
    def test_get_viewport_size(self):
        """测试获取视口尺寸"""
        # 设置滚动区域
        self.viewport_manager.set_scroll_area(self.scroll_area)
        
        # 手动调整滚动区域大小
        self.scroll_area.resize(800, 600)
        
        # 更新视口尺寸
        self.viewport_manager.update_viewport_size()
        
        # 测试获取视口尺寸
        width = self.viewport_manager.get_viewport_width()
        height = self.viewport_manager.get_viewport_height()
        size = self.viewport_manager.get_viewport_size()
        center = self.viewport_manager.get_viewport_center()
        
        assert width > 0
        assert height > 0
        assert size == (width, height)
        assert center == (width / 2, height / 2)
    
    def test_observer_pattern(self):
        """测试观察者模式"""
        # 创建测试观察者
        class TestObserver:
            def __init__(self):
                self.width = 0.0
                self.height = 0.0
                self.called = False
            
            def on_viewport_size_changed(self, width, height):
                self.width = width
                self.height = height
                self.called = True
        
        observer = TestObserver()
        
        # 添加观察者
        result = self.viewport_manager.add_observer(observer)
        assert result is True
        
        # 设置滚动区域
        self.viewport_manager.set_scroll_area(self.scroll_area)
        
        # 调整滚动区域大小
        self.scroll_area.resize(800, 600)
        
        # 更新视口尺寸
        self.viewport_manager.update_viewport_size()
        
        # 检查观察者是否被通知
        assert observer.called
        assert observer.width > 0
        assert observer.height > 0
        
        # 移除观察者
        result = self.viewport_manager.remove_observer(observer)
        assert result is True
        
        # 重置观察者状态
        observer.called = False
        
        # 再次更新视口尺寸
        self.scroll_area.resize(900, 700)
        self.viewport_manager.update_viewport_size()
        
        # 检查观察者是否不再被通知
        assert not observer.called
    
    def test_invalid_observer(self):
        """测试无效的观察者"""
        # 创建无效的观察者（没有实现on_viewport_size_changed方法）
        class InvalidObserver:
            pass
        
        invalid_observer = InvalidObserver()
        
        # 添加无效观察者
        result = self.viewport_manager.add_observer(invalid_observer)
        assert result is False
    
    def test_event_filter(self):
        """测试事件过滤器"""
        # 测试事件过滤器的基本功能
        # 设置滚动区域
        self.viewport_manager.set_scroll_area(self.scroll_area)
        
        # 创建一个测试事件
        from PyQt6.QtCore import QEvent
        resize_event = QEvent(QEvent.Resize)
        
        # 调用事件过滤器
        result = self.viewport_manager.eventFilter(self.scroll_area, resize_event)
        
        # 事件过滤器应该返回False，表示不拦截事件
        assert result is False
        
        # 测试启用/禁用监听
        self.viewport_manager.enable_listening(False)
        result = self.viewport_manager.eventFilter(self.scroll_area, resize_event)
        assert result is False
    
    def test_enable_listening(self):
        """测试启用/禁用监听"""
        # 设置滚动区域
        self.viewport_manager.set_scroll_area(self.scroll_area)
        
        # 禁用监听
        self.viewport_manager.enable_listening(False)
        assert not self.viewport_manager.is_listening_enabled()
        
        # 启用监听
        self.viewport_manager.enable_listening(True)
        assert self.viewport_manager.is_listening_enabled()
    
    def test_clear(self):
        """测试清理资源"""
        # 设置滚动区域和观察者
        self.viewport_manager.set_scroll_area(self.scroll_area)
        
        class TestObserver:
            def on_viewport_size_changed(self, width, height):
                pass
        
        observer = TestObserver()
        self.viewport_manager.add_observer(observer)
        
        # 清理资源
        self.viewport_manager.clear()
        
        # 检查状态
        assert self.viewport_manager.get_viewport_width() == 0.0
        assert self.viewport_manager.get_viewport_height() == 0.0
        assert self.viewport_manager.get_scroll_area() is None
        assert not self.viewport_manager.is_listening_enabled()
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试在未设置滚动区域的情况下更新视口尺寸
        result = self.viewport_manager.update_viewport_size()
        assert result is False
        
        # 测试在未设置滚动区域的情况下获取视口尺寸（应该返回默认值）
        assert self.viewport_manager.get_viewport_width() == 0.0
        assert self.viewport_manager.get_viewport_height() == 0.0

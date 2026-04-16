#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF内容显示区域管理类

功能：
- 创建和管理PDF内容显示区域
- 处理页面布局和渲染
- 支持不同浏览模式的内容显示
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt6.QtCore import Qt

# 导入事件总线
from services.event_bus import event_bus

class ContentArea:
    """
    PDF内容显示区域管理类
    
    负责创建和管理PDF内容显示的滚动区域
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.scroll_area = None
        self.center_container = None
        self.center_layout = None
        
        # 创建内容区域
        self._create_content_area()
        
        # 订阅渲染完成事件
        event_bus.render_completed.connect(self._on_render_completed)
    
    def _create_content_area(self):
        """创建右侧内容显示区域"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 创建居中容器
        self.center_container = QWidget()
        self.center_layout = QVBoxLayout(self.center_container)
        self.center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        
        # 页面显示标签将由浏览模式管理
        self.page_label = None
        
        # 设置居中容器为scroll_area的widget
        self.scroll_area.setWidget(self.center_container)
    
    def get_center_layout(self):
        """获取居中布局"""
        return self.center_layout
    
    def get_center_container(self):
        """获取居中容器"""
        return self.center_container
    
    def update_layout(self):
        """更新内容布局,确保页面正确显示"""
        if not self.scroll_area or not self.scroll_area.widget():
            return
            
        # 确保scroll_area不会太小，保持合理的最小尺寸
        if self.scroll_area.width() < 200 or self.scroll_area.height() < 200:
            self.scroll_area.setMinimumSize(200, 200)
        
        # 强制刷新布局
        if self.center_layout:
            self.center_layout.invalidate()
            self.center_layout.activate()
    
    def _on_render_completed(self, page_num, result, is_final):
        """处理渲染完成事件
        
        参数：
        - page_num: int, 页面编号
        - result: QPixmap, 渲染结果
        - is_final: bool, 是否为最终结果
        """
        # 检查是否有父对象且父对象有viewtype_manager
        if hasattr(self.parent, 'viewtype_manager') and self.parent.viewtype_manager:
            current_viewtype = self.parent.viewtype_manager.current_viewtype
            # 检查当前视图类型是否激活
            if current_viewtype and current_viewtype.is_active:
                # 检查当前页面是否需要更新
                if hasattr(self.parent, 'current_page') and self.parent.current_page == page_num:
                    # 强制更新布局，确保渲染结果正确显示
                    self.update_layout()
                    # 注意：不要调用show_page，否则会导致递归渲染
                    # 渲染结果已经通过事件传递，只需要更新布局即可

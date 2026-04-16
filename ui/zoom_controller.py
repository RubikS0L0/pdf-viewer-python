#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缩放控制器类

功能：
- 处理缩放滑块的变化
- 处理放大/缩小按钮
- 处理实际大小/适合页面/适合页宽功能
- 更新缩放控件的状态
- 与ZoomService和事件总线集成
"""

import logging
from services import event_bus
from services.zoom_service import ZoomService

class ZoomController:
    """
    缩放控制器
    
    负责处理所有与缩放相关的功能
    """
    
    def __init__(self, parent, zoom_service):
        self.parent = parent
        self.zoom_service = zoom_service
        # 设置标记避免递归调用
        self.updating_zoom = False
        # 防抖计时器
        self.zoom_timer = None
        
        # 订阅缩放变化事件
        event_bus.zoom_changed.connect(self._on_zoom_changed)
        
        self.logger = logging.getLogger(__name__)
    
    def on_zoom_slider_changed(self, value):
        """处理缩放滑块变化"""
        if self.updating_zoom:
            return
        
        try:
            # 滑块映射规则：20%-200%对应1-100的滑块值
            if value >= 100:
                # 当滑块值≥100时，缩放级别固定为200%
                zoom_level = 2.0
            else:
                # 正常映射：20%-200% → 1-100
                zoom_level = 0.2 + (value - 1) * (1.8 / 99)
            
            # 更新ZoomService的缩放级别
            actual_zoom = self.zoom_service.set_zoom_level(zoom_level)
            
            # 使用防抖机制，避免频繁的缩放操作导致的性能问题
            from PyQt6.QtCore import QTimer
            if self.zoom_timer:
                self.zoom_timer.stop()
            
            self.zoom_timer = QTimer.singleShot(50, lambda: self._update_after_zoom())
        except Exception as e:
            self.logger.error(f"处理缩放滑块变化失败: {str(e)}")
    
    def _update_after_zoom(self):
        """缩放后更新页面显示和控件状态"""
        try:
            # 更新页面显示
            if hasattr(self.parent, 'show_page') and hasattr(self.parent, 'current_page'):
                self.parent.show_page(self.parent.current_page)
            
            # 更新所有缩放控件的状态
            self.update_zoom_controls()
        except Exception as e:
            self.logger.error(f"缩放后更新页面显示和控件状态失败: {str(e)}")
    
    def zoom_actual_size(self):
        """实际大小 - 将页面恢复到100%缩放"""
        try:
            # 重置缩放级别
            self.zoom_service.reset_zoom()
            # 清除所有页面的缓存（因为缩放级别变化影响所有页面）
            if hasattr(self.parent, 'page_cache'):
                self.parent.page_cache.clear()
            # 重新显示页面
            self.parent.show_page(self.parent.current_page)
            self.update_zoom_controls()
            self.parent.status_bar.showMessage("已设置为实际大小 (100%)")
        except Exception as e:
            self.logger.error(f"设置实际大小失败: {str(e)}")
    
    def zoom_fit_page(self):
        """适合页面 - 缩放页面以适应整个页面显示"""
        try:
            # 获取页面尺寸
            page_size = self.parent.page_renderer.get_page_size(
                self.parent.pdf_manager.get_document(),
                self.parent.current_page,
                1.0,
                self.parent.pdf_manager.get_document_mutex()
            )
            
            if page_size == (0, 0):
                # 如果获取页面尺寸失败，使用默认值
                page_size = (800, 1000)
            
            # 清除所有页面的缓存（因为缩放级别变化影响所有页面）
            if hasattr(self.parent, 'page_cache'):
                self.parent.page_cache.clear()
            
            # 先显示页面（使用当前缩放级别），这样视口尺寸才会正确
            self.parent.show_page(self.parent.current_page)
            
            # 更新视口尺寸，获取最新的视口大小
            self.parent.viewport_manager.update_viewport_size()
            
            # 从ViewportManager获取视口尺寸
            viewport_size = self.parent.viewport_manager.get_viewport_size()
            
            # 计算并设置适合页面的缩放级别
            fit_zoom = self.zoom_service.fit_page(page_size, viewport_size)
            
            # 再次显示页面（使用新的缩放级别）
            self.parent.show_page(self.parent.current_page)
            self.update_zoom_controls()
            
            # 延迟居中显示页面，确保布局已完成
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, self._center_page_in_viewport)
            
            # 更新状态栏
            zoom_percentage = int(fit_zoom * 100)
            self.parent.status_bar.showMessage(f"已设置为适合页面 ({zoom_percentage}%)")
        except Exception as e:
            self.logger.error(f"设置适合页面失败: {str(e)}")
    
    def _center_page_in_viewport(self):
        """将页面居中显示在视口中"""
        try:
            scroll_area = self.parent.content_area.scroll_area
            if not scroll_area:
                return
            
            # 获取水平和垂直滚动条
            h_scroll = scroll_area.horizontalScrollBar()
            v_scroll = scroll_area.verticalScrollBar()
            
            # 计算居中位置
            h_center = (h_scroll.maximum() + h_scroll.minimum()) // 2
            v_center = (v_scroll.maximum() + v_scroll.minimum()) // 2
            
            # 设置滚动条位置
            h_scroll.setValue(h_center)
            v_scroll.setValue(v_center)
            
            self.logger.debug(f"页面已居中: h={h_center}, v={v_center}")
        except Exception as e:
            self.logger.error(f"页面居中失败: {str(e)}")
    
    def zoom_fit_width(self):
        """适合页宽 - 缩放页面以适应页面宽度"""
        try:
            # 先更新视口尺寸，确保使用最新的视口尺寸
            self.parent.viewport_manager.update_viewport_size()
            
            # 获取页面尺寸
            page_size = self.parent.page_renderer.get_page_size(
                self.parent.pdf_manager.get_document(),
                self.parent.current_page,
                1.0,
                self.parent.pdf_manager.get_document_mutex()
            )
            
            if page_size == (0, 0):
                # 如果获取页面尺寸失败，使用默认值
                page_size = (800, 1000)
            
            page_width = page_size[0]
            
            # 从ViewportManager获取视口宽度
            viewport_width = self.parent.viewport_manager.get_viewport_width()
            
            # 计算并设置适合页宽的缩放级别
            fit_zoom = self.zoom_service.fit_width(page_width, viewport_width)
            # 清除所有页面的缓存（因为缩放级别变化影响所有页面）
            if hasattr(self.parent, 'page_cache'):
                self.parent.page_cache.clear()
            # 重新显示页面
            self.parent.show_page(self.parent.current_page)
            self.update_zoom_controls()
            
            # 更新状态栏
            zoom_percentage = int(fit_zoom * 100)
            self.parent.status_bar.showMessage(f"已设置为适合页宽 ({zoom_percentage}%)")
        except Exception as e:
            self.logger.error(f"设置适合页宽失败: {str(e)}")
    
    def zoom_in(self):
        """放大页面"""
        try:
            # 放大页面
            new_zoom = self.zoom_service.zoom_in()
            # 清除所有页面的缓存（因为缩放级别变化影响所有页面）
            if hasattr(self.parent, 'page_cache'):
                self.parent.page_cache.clear()
            # 重新显示页面
            self.parent.show_page(self.parent.current_page)
            self.update_zoom_controls()
        except Exception as e:
            self.logger.error(f"放大页面失败: {str(e)}")
    
    def zoom_out(self):
        """缩小页面"""
        try:
            # 缩小页面
            new_zoom = self.zoom_service.zoom_out()
            # 清除所有页面的缓存（因为缩放级别变化影响所有页面）
            if hasattr(self.parent, 'page_cache'):
                self.parent.page_cache.clear()
            # 重新显示页面
            self.parent.show_page(self.parent.current_page)
            self.update_zoom_controls()
        except Exception as e:
            self.logger.error(f"缩小页面失败: {str(e)}")
    
    def update_zoom_controls(self):
        """更新所有缩放控件的状态"""
        # 设置标记避免递归调用
        self.updating_zoom = True
        try:
            # 从ZoomService获取当前缩放级别
            zoom_level = self.zoom_service.get_zoom_level()
            zoom_percentage = int(zoom_level * 100)
            
            # 获取工具栏管理器的控件引用
            toolbar_manager = self.parent.toolbar_manager
            
            # 更新新的缩放控制组件
            if toolbar_manager.zoom_control:
                toolbar_manager.zoom_control.setZoom(zoom_percentage)
            
            # 兼容旧代码：更新滑块位置
            if toolbar_manager.zoom_slider:
                # 滑块映射规则：20%-200%对应1-100的滑块值
                if zoom_level >= 2.0:
                    # 当缩放级别≥200%时，滑块固定在最大值100
                    slider_value = 100
                else:
                    # 正常映射：20%-200% → 1-100
                    slider_value = int(1 + (zoom_level - 0.2) * (99 / 1.8))
                    slider_value = min(max(slider_value, 1), 100)
                toolbar_manager.zoom_slider.setValue(slider_value)
            
            # 兼容旧代码：更新百分比显示
            if toolbar_manager.zoom_percentage_label:
                toolbar_manager.zoom_percentage_label.setText(f"{zoom_percentage}%")
            
            # 更新状态栏
            self.parent._update_status_bar(self.parent.current_page)
        finally:
            # 确保标记被重置
            self.updating_zoom = False
    
    def set_zoom_percentage(self, percentage: float):
        """设置缩放百分比（新版接口）
        
        Args:
            percentage: 缩放百分比 (20-500)
        """
        try:
            zoom_level = percentage / 100.0
            actual_zoom = self.zoom_service.set_zoom_level(zoom_level)
            
            # 清除所有页面的缓存（因为缩放级别变化影响所有页面）
            if hasattr(self.parent, 'page_cache'):
                self.parent.page_cache.clear()
            
            # 重新显示页面
            self.parent.show_page(self.parent.current_page)
            self.update_zoom_controls()
        except Exception as e:
            self.logger.error(f"设置缩放百分比失败: {str(e)}")
    
    def _on_zoom_changed(self, zoom_level: float, zoom_mode: str):
        """处理缩放变化事件
        
        参数：
        - zoom_level: float, 新的缩放级别
        - zoom_mode: str, 新的缩放模式
        """
        try:
            # 更新缩放控件的状态
            self.update_zoom_controls()
        except Exception as e:
            self.logger.error(f"处理缩放变化事件失败: {str(e)}")

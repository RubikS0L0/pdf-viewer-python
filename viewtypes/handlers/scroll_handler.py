"""
滚动处理器

处理所有与滚动相关的逻辑：
- 滚动位置保存和恢复
- 滚动到指定单元
- 滚动条位置计算
"""

import logging


class ScrollHandler:
    """滚动处理器"""
    
    def __init__(self, viewtype):
        """
        初始化滚动处理器
        
        参数:
            viewtype: 所属的浏览视图类型实例
        """
        self.viewtype = viewtype
        self.logger = logging.getLogger(__name__)
        self.scroll_positions = {}  # 保存每个视图类型的滚动位置
    
    def save_scroll_position(self):
        """保存当前滚动位置"""
        scroll_area = self.viewtype.scroll_area
        if not scroll_area:
            return
        
        # 保存滚动条位置
        h_pos = scroll_area.horizontalScrollBar().value() if scroll_area.horizontalScrollBar() else 0
        v_pos = scroll_area.verticalScrollBar().value() if scroll_area.verticalScrollBar() else 0
        
        # 使用类名作为键，保存滚动位置
        viewtype_name = self.viewtype.__class__.__name__
        self.scroll_positions[viewtype_name] = (h_pos, v_pos)
    
    def restore_scroll_position(self):
        """恢复滚动位置"""
        scroll_area = self.viewtype.scroll_area
        if not scroll_area:
            return
        
        # 获取当前视图类型的保存的滚动位置
        viewtype_name = self.viewtype.__class__.__name__
        if viewtype_name in self.scroll_positions:
            h_pos, v_pos = self.scroll_positions[viewtype_name]
            
            # 恢复水平滚动条位置
            if scroll_area.horizontalScrollBar():
                scroll_area.horizontalScrollBar().setValue(h_pos)
            
            # 恢复垂直滚动条位置
            if scroll_area.verticalScrollBar():
                scroll_area.verticalScrollBar().setValue(v_pos)
    
    def save_scroll_info(self):
        """
        保存滚动位置和视口中心
        
        返回:
            tuple: (scroll_pos, viewport_center)
        """
        scroll_area = self.viewtype.scroll_area
        scroll_pos = None
        viewport_center = None
        
        if scroll_area is not None:
            h_scroll = scroll_area.horizontalScrollBar()
            v_scroll = scroll_area.verticalScrollBar()
            
            if h_scroll is not None and v_scroll is not None:
                scroll_pos = (h_scroll.value(), v_scroll.value())
                
                # 从 ViewportManager 获取视口尺寸
                from ui.viewport_manager import viewport_manager
                viewport_width = viewport_manager.get_viewport_width()
                viewport_height = viewport_manager.get_viewport_height()
                
                old_zoom = self.viewtype.zoom_level
                if old_zoom > 0:
                    viewport_center = (
                        (scroll_pos[0] + viewport_width / 2) / old_zoom,
                        (scroll_pos[1] + viewport_height / 2) / old_zoom
                    )
        
        return scroll_pos, viewport_center
    
    def restore_scroll_position_with_center(self, scroll_pos, viewport_center, zoom_level):
        """
        恢复滚动位置，保持视口中心不变
        
        参数:
            scroll_pos: 原始滚动位置
            viewport_center: 视口中心坐标（PDF坐标系）
            zoom_level: 新的缩放级别
        """
        scroll_area = self.viewtype.scroll_area
        if scroll_pos is None or viewport_center is None or scroll_area is None:
            return
        
        h_scroll = scroll_area.horizontalScrollBar()
        v_scroll = scroll_area.verticalScrollBar()
        
        if h_scroll is None or v_scroll is None:
            return
        
        # 强制更新滚动条
        h_scroll.update()
        v_scroll.update()
        
        # 从 ViewportManager 获取更新后的视口尺寸
        from ui.viewport_manager import viewport_manager
        viewport_width = viewport_manager.get_viewport_width()
        viewport_height = viewport_manager.get_viewport_height()
        
        # 计算新的滚动位置（使用新的缩放级别）
        new_h_pos = int(viewport_center[0] * zoom_level - viewport_width / 2)
        new_v_pos = int(viewport_center[1] * zoom_level - viewport_height / 2)
        
        # 确保滚动位置在有效范围内
        max_h = h_scroll.maximum()
        max_v = v_scroll.maximum()
        new_h_pos = max(0, min(new_h_pos, max_h)) if max_h > 0 else 0
        new_v_pos = max(0, min(new_v_pos, max_v)) if max_v > 0 else 0
        
        # 设置新的滚动位置
        h_scroll.setValue(new_h_pos)
        v_scroll.setValue(new_v_pos)
    
    def scroll_to_unit(self, unit_num, get_unit_rect_func):
        """
        滚动到指定单元
        
        参数:
            unit_num: 单元索引
            get_unit_rect_func: 获取单元矩形区域的回调函数
        """
        scroll_area = self.viewtype.scroll_area
        if not scroll_area:
            return
        
        v_scroll = scroll_area.verticalScrollBar()
        if not v_scroll:
            return
        
        # 获取目标单元的矩形区域
        target_rect = get_unit_rect_func(unit_num)
        if not target_rect:
            return
        
        target_y = target_rect.y()
        item_height = target_rect.height()
        
        # 获取视口高度
        from ui.viewport_manager import viewport_manager
        viewport_height = viewport_manager.get_viewport_height()
        
        # 计算滚动位置
        scroll_position = self._calculate_scroll_position(
            target_y, viewport_height, item_height
        )
        
        # 更新滚动条
        self._update_scroll_bar(v_scroll, scroll_position, target_y, item_height, viewport_height)
    
    def _calculate_scroll_position(self, target_y, viewport_height, item_height):
        """
        计算滚动位置
        
        参数:
            target_y: 目标Y坐标
            viewport_height: 视口高度
            item_height: 项目高度
        
        返回:
            int: 滚动位置
        """
        if item_height <= viewport_height:
            scroll_position = target_y - (viewport_height // 2)
        else:
            scroll_position = target_y
        
        # 确保滚动位置在有效范围内
        scroll_position = max(scroll_position, 0)
        return scroll_position
    
    def _update_scroll_bar(self, v_scroll, scroll_position, target_y, item_height, viewport_height):
        """
        更新滚动条位置
        
        参数:
            v_scroll: 垂直滚动条
            scroll_position: 滚动位置
            target_y: 目标Y坐标
            item_height: 项目高度
            viewport_height: 视口高度
        """
        # 强制更新滚动条最大值
        v_scroll.update()
        
        # 再次确保滚动位置在有效范围内
        scroll_position = max(scroll_position, 0)
        max_scroll = v_scroll.maximum()
        
        if item_height > viewport_height:
            bottom_limit = target_y + item_height - viewport_height
            scroll_position = min(scroll_position, bottom_limit)
        
        # 设置滚动位置
        v_scroll.setValue(scroll_position)
    
    def handle_wheel_event(self, event):
        """
        处理鼠标滚轮事件（滚动部分）
        
        参数:
            event: 鼠标滚轮事件
        """
        from PyQt6.QtCore import Qt
        from utils.constants import Constants
        
        try:
            pdf_viewer = self.viewtype.pdf_viewer
            viewtype_service = self.viewtype.viewtype_service
            scroll_area = self.viewtype.scroll_area
            
            if not pdf_viewer.pdf_manager.is_open or viewtype_service.get_total_pages() == 0:
                return
            
            scroll_bar = scroll_area.verticalScrollBar()
            current_value = scroll_bar.value()
            max_value = scroll_bar.maximum()
            delta = event.angleDelta().y()
            
            threshold = Constants.SCROLL_BOUNDARY_THRESHOLD.value
            at_bottom = current_value >= max_value - threshold
            at_top = current_value <= threshold
            
            current_page = self.viewtype.current_page
            total_pages = viewtype_service.get_total_pages()
            
            # 处理翻页逻辑
            if delta < 0 and at_bottom and current_page < total_pages - 1:
                # 向下滚动到底部，翻到下一页
                if hasattr(pdf_viewer, 'navigation_controller'):
                    pdf_viewer.navigation_controller.next_page()
                    event.accept()
            elif delta > 0 and at_top and current_page > 0:
                # 向上滚动到顶部，翻到上一页
                if hasattr(pdf_viewer, 'navigation_controller'):
                    pdf_viewer.navigation_controller.prev_page()
                    event.accept()
            else:
                # 处理页面内滚动
                self._handle_page_scroll(scroll_bar, current_value, max_value, delta, event)
        
        except Exception as e:
            self.logger.error(f"处理滚轮事件失败: {e}")
    
    def _handle_page_scroll(self, scroll_bar, current_value, max_value, delta, event):
        """
        处理页面内滚动
        
        参数:
            scroll_bar: 滚动条
            current_value: 当前值
            max_value: 最大值
            delta: 滚动增量
            event: 鼠标滚轮事件
        """
        # 计算滚动步长
        scroll_step = 20  # 默认滚动步长
        if delta > 0:
            # 向上滚动
            new_value = max(0, current_value - scroll_step)
        else:
            # 向下滚动
            new_value = min(max_value, current_value + scroll_step)
        
        # 设置新的滚动位置
        scroll_bar.setValue(new_value)
        event.accept()

"""
缩放处理器

处理所有与缩放相关的逻辑：
- 缩放变化事件处理
- 页面间距调整
- 缓存清理
- 滚动位置保持
"""

import logging


class ZoomHandler:
    """缩放处理器"""
    
    def __init__(self, viewtype):
        """
        初始化缩放处理器
        
        参数:
            viewtype: 所属的浏览视图类型实例
        """
        self.viewtype = viewtype
        self.logger = logging.getLogger(__name__)
    
    def on_zoom_changed(self, zoom_level):
        """
        处理缩放变化事件
        
        参数:
            zoom_level: 新的缩放级别
        """
        if not self.viewtype.is_active:
            return
        
        try:
            # 保存当前缩放级别和滚动信息
            old_zoom = self.viewtype.zoom_level
            
            # 获取滚动处理器保存的滚动信息
            from .scroll_handler import ScrollHandler
            if hasattr(self.viewtype, 'scroll_handler'):
                scroll_pos, viewport_center = self.viewtype.scroll_handler.save_scroll_info()
            else:
                scroll_pos, viewport_center = None, None
            
            # 调整页面间距
            self._adjust_page_spacing(zoom_level)
            
            # 清除缓存
            self._clear_page_cache(zoom_level)
            
            # 更新滚动区域
            self._update_scroll_area()
            
            # 重新显示页面
            if hasattr(self.viewtype, 'show_page'):
                self.viewtype.show_page(self.viewtype.current_page)
            
            # 恢复滚动位置
            if hasattr(self.viewtype, 'scroll_handler') and scroll_pos is not None:
                self.viewtype.scroll_handler.restore_scroll_position_with_center(
                    scroll_pos, viewport_center, zoom_level
                )
        except Exception as e:
            self.logger.error(f"处理缩放变化事件失败: {str(e)}")
    
    def _adjust_page_spacing(self, zoom_level):
        """
        根据缩放比例调整页面间距
        
        参数:
            zoom_level: 当前缩放级别
        """
        from utils.constants import Constants
        
        base_spacing = Constants.PAGE_SPACING.value
        scaled_spacing = max(5, int(base_spacing * zoom_level))
        if hasattr(self.viewtype, 'pages_layout') and self.viewtype.pages_layout is not None:
            self.viewtype.pages_layout.setSpacing(scaled_spacing)
    
    def _clear_page_cache(self, zoom_level):
        """
        清除当前页面在新缩放级别的缓存
        
        参数:
            zoom_level: 当前缩放级别
        """
        if hasattr(self.viewtype.pdf_viewer, 'page_cache'):
            self.viewtype.pdf_viewer.page_cache.remove_page(
                self.viewtype.current_page, zoom_level
            )
    
    def _update_scroll_area(self):
        """强制更新滚动区域，确保尺寸信息已更新"""
        scroll_area = self.viewtype.scroll_area
        if scroll_area is not None and scroll_area.widget() is not None:
            scroll_area.widget().adjustSize()
            scroll_area.widget().updateGeometry()

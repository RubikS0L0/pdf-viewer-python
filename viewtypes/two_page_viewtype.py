"""
双页浏览视图类型模块

功能：
- 实现PDF双页浏览视图类型
- 同时显示左右两页的内容
- 支持跨页显示和居中布局
- 处理双页视图类型下的用户交互
- 支持页面缩放和导航

开发环境：
- Python 3.14
- Windows系统

核心依赖：
- PyQt5：GUI界面组件
- BrowsingViewtype：浏览视图类型抽象基类

创建时间：2026-01-16
更新时间：2026-01-23
"""

from .base import BrowsingViewtype
from services.event_bus import event_bus

class TwoPageViewtype(BrowsingViewtype):
    """双页浏览视图类型"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
        # 订阅渲染完成事件
        event_bus.render_completed.connect(self._on_render_completed)
    
    def show_page(self, page_num):
        """显示指定页码的页面"""
        if not self.is_active:
            return
            
        # 确保页码有效
        if page_num < 0 or page_num >= self.viewtype_service.get_total_pages():
            return
            
        # 确保显示的是偶数页码开始的双页
        if page_num % 2 == 1 and page_num > 0:
            page1_num = page_num - 1
            page2_num = page_num
        else:
            page1_num = page_num
            page2_num = min(page1_num + 1, self.viewtype_service.get_total_pages() - 1)
        
        # 更新当前页码
        self.current_page = page_num
        
        # 发布页面更新事件
        self._on_page_changed(page_num)
        
        # 直接合并两页并显示
        combined_pixmap = self._merge_two_pages(page1_num, page2_num)
        if combined_pixmap is not None:
            self.set_page_pixmap(combined_pixmap)
            self.update_config()
            self._center_spread_in_viewport()
    
    def _center_spread_in_viewport(self):
        """将合并双页居中显示在视口中"""
        if self.scroll_area is None or self.page_label is None:
            return
        
        scroll_area = self.scroll_area
        v_scroll = scroll_area.verticalScrollBar()
        h_scroll = scroll_area.horizontalScrollBar()
        
        if v_scroll is None or h_scroll is None:
            return
        
        # 使用 pixmap 尺寸计算，避免 label.height() 在布局未完成时返回 0
        pixmap = self.page_label.pixmap()
        page_height = pixmap.height() if pixmap is not None else 0
        page_width = pixmap.width() if pixmap is not None else 0
        viewport_height = scroll_area.viewport().height()
        viewport_width = scroll_area.viewport().width()
        
        v_pos = max(0, (page_height - viewport_height) // 2)
        h_pos = max(0, (page_width - viewport_width) // 2)
        
        v_scroll.setValue(v_pos)
        h_scroll.setValue(h_pos)
    
    def _on_render_completed(self, page_num, result, is_final):
        """处理渲染完成事件"""
        if result is None or not self.is_active:
            return
            
        # 确保页面标签已初始化
        if self.page_label is None:
            self._initialize_page_label()
            
        # 计算当前显示的双页范围
        current_page = self.current_page
        if current_page % 2 == 1 and current_page > 0:
            page1_num = current_page - 1
            page2_num = current_page
        else:
            page1_num = current_page
            page2_num = min(page1_num + 1, self.viewtype_service.get_total_pages() - 1)
        
        # 检查当前渲染的页面是否在双页范围内
        if page_num == page1_num or page_num == page2_num:
            # 重新合并两页并显示
            combined_pixmap = self._merge_two_pages(page1_num, page2_num)
            if combined_pixmap is not None:
                self.set_page_pixmap(combined_pixmap)
                self.update_config()
                self._center_spread_in_viewport()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视图类型服务实现

实现IViewtypeService接口，将调用委托给PDFMainWindow
"""

from services.interfaces import IViewtypeService
from PyQt6.QtGui import QPixmap


class ViewtypeService(IViewtypeService):
    """视图类型服务实现"""
    
    def __init__(self, pdf_viewer):
        """初始化视图类型服务
        
        参数：
        - pdf_viewer: PDFMainWindow实例
        """
        self.pdf_viewer = pdf_viewer
    
    def get_current_page(self) -> int:
        """获取当前页码"""
        return self.pdf_viewer.get_current_page()
    
    def get_total_pages(self) -> int:
        """获取总页数"""
        return self.pdf_viewer.get_total_pages()
    
    def get_zoom_level(self) -> float:
        """获取当前缩放级别"""
        return self.pdf_viewer.zoom_service.get_zoom_level()
    
    def set_zoom_level(self, zoom_level: float) -> None:
        """设置缩放级别"""
        self.pdf_viewer.zoom_service.set_zoom_level(zoom_level)
    
    def get_page_pixmap(self, page_num: int) -> QPixmap:
        """获取指定页码的页面Pixmap（同步方法）"""
        return self.pdf_viewer._get_page_pixmap(page_num)
    
    def get_page_pixmap_async(self, page_num: int, callback=None) -> int:
        """异步获取指定页码的页面Pixmap"""
        return self.pdf_viewer._get_page_pixmap_async(page_num, callback)
    
    def get_two_pages_pixmap_async(self, page1_num: int, page2_num: int, callback=None) -> None:
        """异步获取双页的合并Pixmap"""
        return self.pdf_viewer._get_two_pages_pixmap_async(page1_num, page2_num, callback)
    
    def get_page_size(self, page_num: int, zoom_level: float) -> tuple:
        """获取指定页码的页面尺寸"""
        return self.pdf_viewer.pdf_service.get_page_size(page_num, zoom_level)
    
    def update_content_layout(self) -> None:
        """更新内容布局"""
        self.pdf_viewer._update_content_layout()
    
    def show_page(self, page_num: int) -> None:
        """显示指定页码的页面"""
        self.pdf_viewer.show_page(page_num)
    
    def get_detection_results(self) -> dict:
        """获取检测结果"""
        return getattr(self.pdf_viewer, 'detection_results', {})
    
    def get_results_mutex(self):
        """获取结果互斥锁"""
        return getattr(self.pdf_viewer, 'results_mutex', None)
    
    def get_selecting(self) -> bool:
        """获取选择状态"""
        return getattr(self.pdf_viewer, 'selecting', False)
    
    def set_selecting(self, value: bool) -> None:
        """设置选择状态"""
        if hasattr(self.pdf_viewer, 'selecting'):
            self.pdf_viewer.selecting = value
    
    def get_select_start_pdf(self):
        """获取选择起始PDF坐标"""
        from PyQt6.QtCore import QPoint
        return getattr(self.pdf_viewer, 'select_start_pdf', QPoint(0, 0))
    
    def set_select_start_pdf(self, value) -> None:
        """设置选择起始PDF坐标"""
        if hasattr(self.pdf_viewer, 'select_start_pdf'):
            self.pdf_viewer.select_start_pdf = value
    
    def get_select_end_pdf(self):
        """获取选择结束PDF坐标"""
        from PyQt6.QtCore import QPoint
        return getattr(self.pdf_viewer, 'select_end_pdf', QPoint(0, 0))
    
    def set_select_end_pdf(self, value) -> None:
        """设置选择结束PDF坐标"""
        if hasattr(self.pdf_viewer, 'select_end_pdf'):
            self.pdf_viewer.select_end_pdf = value
    
    def is_two_page_mode(self) -> bool:
        """检查当前是否为双页浏览模式"""
        current_viewtype = self.pdf_viewer.viewtype_manager.get_current_viewtype_name()
        return current_viewtype in ["two_page_spread", "two_page_spread_continuous"]

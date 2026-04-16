"""
选择框渲染器

处理选择框的绘制逻辑：
- PDF坐标到屏幕坐标的转换
- 选择框绘制
- 选择状态管理
"""

import logging
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import QRect
from utils.constants import Constants


class SelectionRenderer:
    """选择框渲染器"""
    
    def __init__(self, viewtype):
        """
        初始化选择框渲染器
        
        参数:
            viewtype: 所属的浏览视图类型实例
        """
        self.viewtype = viewtype
        self.logger = logging.getLogger(__name__)
    
    def pdf_to_screen(self, pdf_x, pdf_y):
        """
        PDF坐标转屏幕坐标
        
        参数:
            pdf_x: PDF X坐标
            pdf_y: PDF Y坐标
            
        返回:
            tuple: (screen_x, screen_y)
        """
        scroll_area = self.viewtype.scroll_area
        if not scroll_area:
            return 0, 0
        
        scroll_x = scroll_area.horizontalScrollBar().value()
        scroll_y = scroll_area.verticalScrollBar().value()
        zoom_level = self.viewtype.zoom_level
        
        screen_x = pdf_x * zoom_level - scroll_x
        screen_y = pdf_y * zoom_level - scroll_y
        return screen_x, screen_y
    
    def screen_to_pdf(self, screen_x, screen_y):
        """
        屏幕坐标转PDF坐标
        
        参数:
            screen_x: 屏幕 X坐标
            screen_y: 屏幕 Y坐标
            
        返回:
            tuple: (pdf_x, pdf_y)
        """
        scroll_area = self.viewtype.scroll_area
        if not scroll_area:
            return 0, 0
        
        scroll_x = scroll_area.horizontalScrollBar().value()
        scroll_y = scroll_area.verticalScrollBar().value()
        zoom_level = self.viewtype.zoom_level
        
        pdf_x = (screen_x + scroll_x) / zoom_level
        pdf_y = (screen_y + scroll_y) / zoom_level
        return pdf_x, pdf_y
    
    def draw_selection_box(self, painter):
        """
        绘制选择框
        
        参数:
            painter: QPainter 实例
        """
        selecting = self.viewtype.selecting
        select_start_pdf = self.viewtype.select_start_pdf
        select_end_pdf = self.viewtype.select_end_pdf
        scroll_area = self.viewtype.scroll_area
        
        if (selecting or select_start_pdf != select_end_pdf) and scroll_area:
            x1, y1 = self.pdf_to_screen(select_start_pdf.x(), select_start_pdf.y())
            x2, y2 = self.pdf_to_screen(select_end_pdf.x(), select_end_pdf.y())
            
            # 绘制选择框
            pen = QPen(
                QColor(*Constants.SELECTION_BOX_COLOR.value), 
                Constants.SELECTION_BOX_WIDTH.value, 
                Constants.SELECTION_BOX_STYLE.value
            )
            painter.setPen(pen)
            painter.drawRect(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
    
    def set_select_state(self, selecting, start_pdf, end_pdf):
        """
        设置选择状态
        
        参数:
            selecting: 是否正在选择
            start_pdf: 选择起始点（PDF坐标）
            end_pdf: 选择结束点（PDF坐标）
        """
        self.viewtype.selecting = selecting
        self.viewtype.select_start_pdf = start_pdf
        self.viewtype.select_end_pdf = end_pdf
        
        # 触发重绘
        if self.viewtype.page_label:
            self.viewtype.page_label.update()

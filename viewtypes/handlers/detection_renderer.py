"""
检测结果渲染器

处理目标检测结果的绘制逻辑：
- 检测框绘制
- 标签绘制（带背景）
- 坐标转换和缩放适应
"""

import logging
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import QRect, Qt
from utils.constants import Constants


class DetectionRenderer:
    """检测结果渲染器"""
    
    def __init__(self, viewtype):
        """
        初始化检测结果渲染器
        
        参数:
            viewtype: 所属的浏览视图类型实例
        """
        self.viewtype = viewtype
        self.logger = logging.getLogger(__name__)
    
    def _pdf_to_screen(self, pdf_x, pdf_y):
        """
        PDF坐标转屏幕坐标（内部辅助方法）
        
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
    
    def draw_detection_results(self, painter):
        """
        绘制检测结果
        
        参数:
            painter: QPainter 实例
        """
        results_mutex = self.viewtype.results_mutex
        detection_results = self.viewtype.detection_results
        current_page = self.viewtype.current_page
        scroll_area = self.viewtype.scroll_area
        zoom_level = self.viewtype.zoom_level
        
        if results_mutex and current_page in detection_results:
            results_mutex.lock()
            try:
                results = detection_results[current_page]
                if results and scroll_area:
                    self._draw_results(painter, results, zoom_level)
            finally:
                results_mutex.unlock()
    
    def _draw_results(self, painter, results, zoom_level):
        """
        绘制检测结果列表
        
        参数:
            painter: QPainter 实例
            results: 检测结果列表
            zoom_level: 当前缩放级别
        """
        # 根据缩放比例调整样式
        scale_factor = zoom_level
        
        # 绘制检测结果矩形和标签
        box_color = Constants.DETECTION_BOX_COLOR.value
        box_width = max(1, int(Constants.DETECTION_BOX_WIDTH.value * scale_factor))
        font_size = max(6, int(Constants.DETECTION_LABEL_FONT_SIZE.value * scale_factor))
        
        pen = QPen(QColor(*box_color), box_width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        
        font = painter.font()
        font.setPointSize(font_size)
        painter.setFont(font)
        
        label_color = Constants.DETECTION_LABEL_COLOR.value
        label_bg = Constants.DETECTION_LABEL_BACKGROUND.value
        
        for result in results:
            self._draw_single_result(painter, result, font_size, label_color, label_bg)
    
    def _draw_single_result(self, painter, result, font_size, label_color, label_bg):
        """
        绘制单个检测结果
        
        参数:
            painter: QPainter 实例
            result: 单个检测结果
            font_size: 字体大小
            label_color: 标签颜色
            label_bg: 标签背景色
        """
        # 处理不同的数据结构
        if isinstance(result, tuple):
            # 旧数据结构：(x1, y1, x2, y2)
            x1, y1, x2, y2 = result
            class_name = "unknown"
            confidence = 0.0
        else:
            # 新数据结构：字典
            bbox = result.get('bbox', (0, 0, 0, 0))
            x1, y1, x2, y2 = bbox
            class_name = result.get('class_name', "unknown")
            confidence = result.get('confidence', 0.0)
        
        # 转换为屏幕坐标
        screen_x1, screen_y1 = self._pdf_to_screen(x1, y1)
        screen_x2, screen_y2 = self._pdf_to_screen(x2, y2)
        
        # 绘制边界框
        painter.drawRect(QRect(
            int(screen_x1), int(screen_y1), 
            int(screen_x2 - screen_x1), int(screen_y2 - screen_y1)
        ))
        
        # 绘制标签，添加背景
        label = f"{class_name}: {confidence:.2f}"
        label_rect = QRect(
            int(screen_x1), 
            int(screen_y1 - font_size - 5), 
            len(label) * font_size // 2, 
            font_size + 5
        )
        
        # 绘制标签背景
        painter.fillRect(label_rect, QColor(*label_bg))
        
        # 绘制标签文本
        painter.setPen(QColor(*label_color))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)
        
        # 恢复画笔颜色（用于下一个框）
        box_color = Constants.DETECTION_BOX_COLOR.value
        box_width = max(1, int(Constants.DETECTION_BOX_WIDTH.value * self.viewtype.zoom_level))
        pen = QPen(QColor(*box_color), box_width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)

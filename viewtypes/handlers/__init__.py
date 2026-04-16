"""
视图类型处理器模块

将 BrowsingViewtype 的职责拆分为多个专门的处理器：
- ScrollHandler: 处理滚动相关逻辑
- ZoomHandler: 处理缩放相关逻辑
- SelectionRenderer: 绘制选择框
- DetectionRenderer: 绘制检测结果
"""

from .scroll_handler import ScrollHandler
from .zoom_handler import ZoomHandler
from .selection_renderer import SelectionRenderer
from .detection_renderer import DetectionRenderer

__all__ = [
    'ScrollHandler',
    'ZoomHandler',
    'SelectionRenderer',
    'DetectionRenderer',
]

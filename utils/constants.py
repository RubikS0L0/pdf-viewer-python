#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF浏览器常量定义

使用枚举类型统一管理所有常量，增强代码可维护性和安全性

分类：
- 界面文本常量：按钮、菜单等文本
- 数值常量：缩放因子、缓存大小等
- 布局常量：预加载范围、最小选择区域等

开发环境：
- Python 3.14
- Windows系统

核心依赖：
- enum：枚举类型支持
"""

from enum import Enum
from PyQt6.QtCore import Qt


class Constants(Enum):
    """
    PDF浏览器常量定义
    """
    # 界面文本常量
    OPEN_BUTTON_TEXT = "打开"
    PREV_BUTTON_TEXT = "上一页"
    NEXT_BUTTON_TEXT = "下一页"
    ZOOM_IN_TEXT = "放大"
    ZOOM_OUT_TEXT = "缩小"
    SELECT_BUTTON_TEXT = "选择"
    STATISTIC_BUTTON_TEXT = "统计"
    FILE_MENU_OPEN = "打开"
    FILE_MENU_EXIT = "退出"
    
    # 数值常量（由配置文件动态加载，此处为默认值）
    DETECTION_RENDER_SCALE = 2.0  # 检测时页面渲染缩放因子
    MIN_SELECT_AREA = 20  # 最小选择区域像素
    THUMBNAIL_CACHE_SIZE = 20  # 缩略图缓存数量
    PAGE_CACHE_SIZE = 10  # 页面缓存大小
    PRELOAD_RANGE = 3  # 预加载页面范围
    
    # 缩放相关常量
    MIN_ZOOM = 0.2  # 最小缩放比例
    MAX_ZOOM = 5.0  # 最大缩放比例
    ZOOM_DELTA = 1.05  # 滚轮缩放因子
    DEFAULT_ZOOM = 1.0  # 默认缩放级别
    
    # 间距相关常量
    PAGE_SPACING = 20  # 双页模式页面间距
    SPREAD_SPACING = 10  # 双页连续模式双页组合间距
    
    # 节流和延迟常量
    THROTTLE_DELAY = 16  # 节流延迟时间（毫秒）
    CACHE_TIMEOUT = 500  # 缓存超时时间（毫秒）
    
    # 检测相关常量
    CONF_THRESHOLD = 0.5  # 置信度阈值
    IOU_THRESHOLD = 0.45  # IOU阈值
    NMS_THRESHOLD = 0.5  # NMS阈值
    
    # 内存管理常量
    MEMORY_WARNING_THRESHOLD = 80.0  # 内存警告阈值（%）
    MEMORY_CRITICAL_THRESHOLD = 85.0  # 内存临界阈值（%）
    CACHE_CLEANUP_RATIO = 0.5  # 缓存清理比例
    CRITICAL_CLEANUP_RATIO = 0.7  # 临界状态缓存清理比例
    
    # UI相关常量
    FONT_SIZE = 8  # 检测结果字体大小
    
    # 检测结果样式常量
    DETECTION_BOX_COLOR = (0, 255, 0)  # 检测框颜色 (RGB)
    DETECTION_BOX_WIDTH = 2  # 检测框宽度
    DETECTION_LABEL_FONT_SIZE = 8  # 检测标签字体大小
    DETECTION_LABEL_COLOR = (255, 255, 255)  # 检测标签颜色 (RGB)
    DETECTION_LABEL_BACKGROUND = (0, 0, 0, 128)  # 检测标签背景 (RGBA)
    
    # 选择框样式常量
    SELECTION_BOX_COLOR = (255, 0, 0)  # 选择框颜色 (RGB)
    SELECTION_BOX_WIDTH = 2  # 选择框宽度
    SELECTION_BOX_STYLE = Qt.PenStyle.DashLine  # 选择框样式
    
    # 渲染相关常量
    RENDER_RETRY_COUNT = 3  # 渲染重试次数
    RENDER_RETRY_DELAY = 0.1  # 渲染重试延迟（秒）
    
    # 滚动相关常量
    SCROLL_BOUNDARY_THRESHOLD = 5  # 滚动边界阈值
    
    # 缩放变化常量
    ZOOM_CHANGE_THRESHOLD = 0.01  # 缩放变化阈值
    
    # 设备配置常量
    DEFAULT_DEVICE = "cpu"  # 默认计算设备
    
    # 页面边距常量（用于适应页面/适应宽度计算）
    PAGE_MARGIN = 20  # 页面边距大小（像素）
    

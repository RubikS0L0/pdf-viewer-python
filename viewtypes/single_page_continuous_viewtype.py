"""
单页连续浏览视图类型模块

功能：
- 实现PDF单页连续浏览视图类型
- 连续显示所有页面内容，可滚动浏览
- 支持页面预加载和动态显示
- 处理连续浏览视图类型下的用户交互
- 支持页面缩放和导航

开发环境：
- Python 3.14
- Windows系统

核心依赖：
- PyQt5：GUI界面组件
- BrowsingViewtype：浏览视图类型抽象基类

创建时间：2026-01-16
更新时间：2026-05-27（重构：事件订阅由基类统一管理）
"""

import logging
from .base import ContinuousViewtype, ViewtypePageLabel
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from services.event_bus import event_bus
from utils.constants import Constants


class SinglePageContinuousViewtype(ContinuousViewtype):
    """单页连续浏览视图类型"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
        # _render_completed_bound 由父类 BaseContinuousViewtype.__init__ 末尾的
        # _connect_render_completed() 设置，无需重复初始化
    
    # ---------- 基类要求的抽象方法 ----------
    def _show_single_unit(self, unit_num):
        """显示单个单元（页面）"""
        if self.pages_layout is None:
            logging.warning(f"单页连续视图类型: pages_layout 为 None，无法显示页面 {unit_num}")
            return
            
        if self.viewtype_service.get_total_pages() == 0:
            logging.warning(f"单页连续视图类型: PDF 文档未打开，无法显示页面 {unit_num}")
            return
            
        if unit_num < 0 or unit_num >= self.viewtype_service.get_total_pages():
            logging.warning(f"单页连续视图类型: 无效的页码 {unit_num}")
            return
            
        page_label = None
        if unit_num not in self.page_labels:
            try:
                page_label = ViewtypePageLabel(self)
                page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
                self.page_labels[unit_num] = page_label
                self.pages_layout.addWidget(page_label)
                logging.debug(f"单页连续视图类型: 创建页面标签，页码：{unit_num}")
            except Exception as e:
                logging.error(f"单页连续视图类型: 创建页面标签失败，页码：{unit_num}，错误：{str(e)}")
                return
        else:
            page_label = self.page_labels[unit_num]
        
        self.viewtype_service.get_page_pixmap_async(unit_num)
    
    def _scroll_to_unit(self, unit_num):
        """滚动到指定单元（页面）"""
        if unit_num not in self.page_labels:
            return
        if self.scroll_area is None:
            return
        v_scroll = self.scroll_area.verticalScrollBar()
        if not v_scroll:
            return
        
        current_page_label = self.page_labels.get(unit_num)
        if current_page_label is None:
            return
        
        # 强制更新所有页面标签的大小
        for p, page_label in list(self.page_labels.items()):
            if page_label:
                try:
                    page_label.adjustSize()
                    page_label.repaint()
                except Exception:
                    continue
        
        if self.pages_layout:
            self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.pages_layout.invalidate()
            self.pages_layout.activate()
        
        QApplication.processEvents()
        
        # 计算累积高度
        target_y = 0
        spacing = Constants.PAGE_SPACING.value
        
        for p in range(unit_num):
            page_label = self.page_labels.get(p)
            if page_label:
                try:
                    h = page_label.height()
                    if h == 0:
                        h = page_label.sizeHint().height()
                    target_y += h + spacing
                except Exception:
                    continue
        
        viewport_height = self.scroll_area.viewport().height()
        
        try:
            current_page_height = current_page_label.height()
            if current_page_height == 0:
                current_page_height = current_page_label.sizeHint().height()
        except Exception:
            return
        
        scroll_position = target_y - (viewport_height - current_page_height) // 2
        scroll_position = max(0, scroll_position)
        v_scroll.setValue(scroll_position)
    
    def _get_current_unit(self, page_num):
        """获取当前页码对应的单元索引（页码即单元索引）"""
        return page_num
    
    def _get_max_unit(self):
        """获取最大单元数（总页数）"""
        return self.viewtype_service.get_total_pages()
    
    # ---------- 渲染完成处理 ----------
    def _on_render_completed(self, page_num, result, is_final):
        """处理渲染完成事件"""
        if result is None or not self.is_active:
            return
            
        if page_num not in self.page_labels:
            return
        
        page_label = self.page_labels[page_num]
        if page_label is None:
            return
        
        def update_gui():
            try:
                page_label.setPixmap(result)
                page_label.show()
                self.viewtype_service.update_content_layout()
                if self.scroll_area is not None and self.scroll_area.widget() is not None:
                    self.scroll_area.widget().adjustSize()
            except Exception as e:
                logging.error(f"单页连续视图类型: 设置 pixmap 失败，页码：{page_num}，错误：{str(e)}")
                if "wrapped C/C++ object has been deleted" in str(e):
                    self._recreate_label(page_num, result)
        
        from PyQt6.QtCore import QTimer
        if QApplication.instance():
            QTimer.singleShot(0, update_gui)
    
    def _recreate_label(self, page_num, pixmap):
        """重新创建页面标签"""
        try:
            new_label = ViewtypePageLabel(self)
            new_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
            self.page_labels[page_num] = new_label
            if self.pages_layout is not None:
                self.pages_layout.addWidget(new_label)
            new_label.setPixmap(pixmap)
            new_label.show()
            self.viewtype_service.update_content_layout()
        except Exception as e2:
            logging.error(f"单页连续视图类型: 重新创建标签失败，页码：{page_num}，错误：{str(e2)}")
    
    # ---------- 基类统一信号管理 ----------
    def _connect_render_completed(self):
        """连接渲染完成事件"""
        self._render_completed_bound = self._on_render_completed
        event_bus.render_completed.connect(self._render_completed_bound)
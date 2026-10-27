"""
双页连续浏览视图类型模块

功能：
- 实现PDF双页连续浏览视图类型
- 连续显示多个双页组合，支持滚动浏览
- 支持跨页显示和垂直布局
- 处理双页连续视图类型下的用户交互
- 支持页面缩放和导航

开发环境：
- Python 3.14
- Windows系统

核心依赖：
- PyQt5：GUI界面组件
- BrowsingViewtype：浏览视图类型抽象基类

创建时间：2026-01-16
更新时间：2026-05-27（重构：事件订阅由基类统一管理 + spread 缓存安全版）
"""

import logging
from .base import ContinuousViewtype, ViewtypePageLabel
from services.event_bus import event_bus
from utils.constants import Constants


class TwoPageContinuousViewtype(ContinuousViewtype):
    """双页连续浏览视图类型"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
        self.spread_labels = {}  # 存储双页标签
        self._spread_cache = {}  # spread 合并结果缓存
        self._spread_cache_max = 20  # 缓存硬上限
        self._pending_remerge_timers = []  # 跟踪所有待执行的 timer
    
    # ---------- 基类要求的抽象方法 ----------
    def _show_single_unit(self, unit_num):
        """显示单个单元（双页）"""
        if self.viewtype_service.get_total_pages() == 0:
            logging.warning(f"双页连续视图类型: PDF 文档未打开，无法显示双页 {unit_num}")
            return
        
        page1_num = unit_num * 2
        page2_num = min(page1_num + 1, self.viewtype_service.get_total_pages() - 1)
        
        if self.pages_layout is None:
            logging.warning(f"双页连续视图类型: pages_layout 为 None，无法显示双页 {unit_num}")
            return
        
        spread_key = f"spread_{unit_num}"
        page_label = None
        if spread_key not in self.spread_labels:
            try:
                page_label = ViewtypePageLabel(self)
                page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
                self.spread_labels[spread_key] = page_label
                self.pages_layout.addWidget(page_label)
                logging.debug(f"双页连续视图类型: 创建双页标签，双页索引：{unit_num}")
            except Exception as e:
                logging.error(f"双页连续视图类型: 创建双页标签失败，双页索引：{unit_num}，错误：{str(e)}")
                return
        else:
            page_label = self.spread_labels[spread_key]
        
        # 同步合并两页并显示
        combined_pixmap = self._merge_two_pages(page1_num, page2_num)
        if combined_pixmap is not None:
            from PyQt6.QtWidgets import QApplication
            def update_gui():
                try:
                    page_label.setPixmap(combined_pixmap)
                    page_label.show()
                    self.viewtype_service.update_content_layout()
                    if self.scroll_area is not None and self.scroll_area.widget() is not None:
                        self.scroll_area.widget().adjustSize()
                except Exception as e:
                    logging.error(f"双页连续视图类型: 设置双页 pixmap 失败，双页索引：{unit_num}，错误：{str(e)}")
                    if "wrapped C/C++ object has been deleted" in str(e):
                        self._recreate_spread_label(spread_key, combined_pixmap)
            
            from PyQt6.QtCore import QTimer
            if QApplication.instance():
                QTimer.singleShot(0, update_gui)
    
    def _scroll_to_unit(self, unit_num):
        """滚动到指定单元（双页）"""
        spread_key = f"spread_{unit_num}"
        if spread_key not in self.spread_labels:
            return
        if self.scroll_area is None:
            return
        v_scroll = self.scroll_area.verticalScrollBar()
        if not v_scroll:
            return
        
        # 强制更新所有双页标签的大小
        for key, page_label in list(self.spread_labels.items()):
            if page_label:
                try:
                    page_label.adjustSize()
                    page_label.repaint()
                except Exception:
                    continue
        
        if self.pages_layout:
            from PyQt6.QtCore import Qt
            self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.pages_layout.invalidate()
            self.pages_layout.activate()
        
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        target_y = 0
        spacing = Constants.PAGE_SPACING.value
        
        for i in range(unit_num):
            key = f"spread_{i}"
            page_label = self.spread_labels.get(key)
            if page_label:
                try:
                    h = page_label.height()
                    if h == 0:
                        h = page_label.sizeHint().height()
                    target_y += h + spacing
                except Exception:
                    continue
        
        viewport_height = self.scroll_area.viewport().height()
        
        current_spread_label = self.spread_labels[spread_key]
        try:
            if current_spread_label is not None:
                current_spread_height = current_spread_label.height()
                if current_spread_height == 0:
                    current_spread_height = current_spread_label.sizeHint().height()
            else:
                return
        except Exception:
            return
        
        scroll_position = target_y - (viewport_height - current_spread_height) // 2
        scroll_position = max(0, scroll_position)
        v_scroll.setValue(scroll_position)
    
    def _get_current_unit(self, page_num):
        """获取当前页码对应的单元索引（双页索引）"""
        return page_num // 2
    
    def _get_max_unit(self):
        """获取最大单元数（双页数量）"""
        return (self.viewtype_service.get_total_pages() + 1) // 2
    
    # ---------- 渲染完成处理 ----------
    def _on_render_completed(self, page_num, result, is_final):
        """处理渲染完成事件"""
        if result is None or not self.is_active:
            return
        
        spread_num = page_num // 2
        spread_key = f"spread_{spread_num}"
        
        if spread_key not in self.spread_labels:
            return
        
        page_label = self.spread_labels[spread_key]
        if page_label is None:
            return
        
        page1_num = spread_num * 2
        page2_num = min(page1_num + 1, self.viewtype_service.get_total_pages() - 1)
        
        combined_pixmap = self._merge_two_pages(page1_num, page2_num)
        if combined_pixmap is not None:
            from PyQt6.QtWidgets import QApplication
            def update_gui():
                try:
                    page_label.setPixmap(combined_pixmap)
                    page_label.show()
                    self.viewtype_service.update_content_layout()
                    if self.scroll_area is not None and self.scroll_area.widget() is not None:
                        self.scroll_area.widget().adjustSize()
                except Exception as e:
                    logging.error(f"双页连续视图类型: 设置双页 pixmap 失败，双页索引：{spread_num}，错误：{str(e)}")
                    if "wrapped C/C++ object has been deleted" in str(e):
                        self._recreate_spread_label(spread_key, combined_pixmap)
            
            from PyQt6.QtCore import QTimer
            if QApplication.instance():
                QTimer.singleShot(0, update_gui)
    
    def _recreate_spread_label(self, spread_key, pixmap):
        """重新创建双页标签"""
        try:
            new_label = ViewtypePageLabel(self)
            new_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
            self.spread_labels[spread_key] = new_label
            if self.pages_layout is not None:
                self.pages_layout.addWidget(new_label)
            new_label.setPixmap(pixmap)
            new_label.show()
            self.viewtype_service.update_content_layout()
        except Exception as e2:
            logging.error(f"双页连续视图类型: 重新创建双页标签失败，spread_key：{spread_key}，错误：{str(e2)}")
    
    # ---------- spread 缓存管理 ----------
    def _add_spread_cache(self, cache_key, pixmap):
        """安全添加缓存，带 LRU 淘汰"""
        if len(self._spread_cache) >= self._spread_cache_max:
            self._spread_cache.pop(next(iter(self._spread_cache)))
        self._spread_cache[cache_key] = pixmap
    
    def _remerge_spread(self, spread_num):
        """增量重新合并单个 spread"""
        if not self.is_active:
            return
        spread_key = f"spread_{spread_num}"
        if spread_key not in self.spread_labels:
            return
        
        zoom_level = self.viewtype_service.get_zoom_level()
        cache_key = (spread_num, round(zoom_level, 2))
        
        if cache_key in self._spread_cache:
            combined_pixmap = self._spread_cache[cache_key]
        else:
            page1_num = spread_num * 2
            page2_num = min(page1_num + 1, self.viewtype_service.get_total_pages() - 1)
            combined_pixmap = self._merge_two_pages(page1_num, page2_num)
            if combined_pixmap:
                self._add_spread_cache(cache_key, combined_pixmap)
        
        if combined_pixmap:
            label = self.spread_labels[spread_key]
            label.setPixmap(combined_pixmap)
    
    def _cancel_all_pending_remerge(self):
        """取消所有待执行的重新合并定时器"""
        for timer in self._pending_remerge_timers:
            timer.stop()
            try:
                timer.timeout.disconnect()
            except TypeError:
                pass
        self._pending_remerge_timers.clear()
    
    def on_state_changed(self, state_name, old_value, new_value):
        """处理状态变化"""
        super().on_state_changed(state_name, old_value, new_value)
        
        if state_name == "zoom_level":
            # 清缓存
            self._spread_cache.clear()
            # 取消所有待执行的 timer
            self._cancel_all_pending_remerge()
            
            # 收集可见的 spread
            visible = [
                (int(k.split('_')[1]), v)
                for k, v in self.spread_labels.items()
                if v.isVisible()
            ]
            
            if not visible:
                return
            
            # 分批处理，每批最多 5 个 spread，间隔 50ms
            batch_size = 5
            interval_ms = 50
            for batch_idx in range(0, len(visible), batch_size):
                batch = visible[batch_idx:batch_idx + batch_size]
                from PyQt6.QtCore import QTimer
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(
                    lambda b=batch: [self._remerge_spread(spread_num) for spread_num, _ in b]
                )
                timer.start(batch_idx // batch_size * interval_ms)
                self._pending_remerge_timers.append(timer)
    
    def reset_display(self):
        """重置显示状态"""
        # 先取消所有 timer，再清理
        self._cancel_all_pending_remerge()
        super().reset_display()
        # 清缓存
        self._spread_cache.clear()
    
    # ---------- 基类统一信号管理 ----------
    def _connect_render_completed(self):
        """连接渲染完成事件"""
        self._render_completed_bound = self._on_render_completed
        event_bus.render_completed.connect(self._render_completed_bound)
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
更新时间：2026-01-23
"""

import logging
from .base import ContinuousViewtype, ViewtypePageLabel
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from services.event_bus import event_bus

class SinglePageContinuousViewtype(ContinuousViewtype):
    """单页连续浏览视图类型"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
        # 订阅渲染完成事件
        event_bus.render_completed.connect(self._on_render_completed)
    
    def _show_single_unit(self, unit_num):
        """显示单个单元（页面）"""
        # 确保pages_layout已经初始化，不再调用_create_layout，直接使用activate方法中创建的pages_layout
        if self.pages_layout is None:
            logging.warning(f"单页连续视图类型: pages_layout为None，无法显示页面{unit_num}")
            return
            
        # 确保PDF文档已打开
        if self.viewtype_service.get_total_pages() == 0:
            logging.warning(f"单页连续视图类型: PDF文档未打开，无法显示页面{unit_num}")
            return
            
        # 确保页码有效
        if unit_num < 0 or unit_num >= self.viewtype_service.get_total_pages():
            logging.warning(f"单页连续视图类型: 无效的页码{unit_num}")
            return
            
        # 创建或获取PageLabel
        page_label = None
        if unit_num not in self.page_labels:
            try:
                page_label = ViewtypePageLabel(self)
                # 连接信号，在页面显示后更新布局
                page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
                self.page_labels[unit_num] = page_label
                self.pages_layout.addWidget(page_label)
                logging.debug(f"单页连续视图类型: 创建并添加了页面标签，页码：{unit_num}，标签ID：{id(page_label)}")
            except Exception as e:
                logging.error(f"单页连续视图类型: 创建页面标签失败，页码：{unit_num}，错误：{str(e)}")
                return
        else:
            page_label = self.page_labels[unit_num]
            logging.debug(f"单页连续视图类型: 获取了现有页面标签，页码：{unit_num}，标签ID：{id(page_label)}")
        
        # 使用异步方法获取页面pixmap，不传递回调函数，通过事件总线处理渲染完成
        self.viewtype_service.get_page_pixmap_async(unit_num)
    
    def _scroll_to_unit(self, unit_num):
        """滚动到指定单元（页面）"""
        # 检查unit_num是否在page_labels中
        if unit_num not in self.page_labels:
            logging.debug(f"_scroll_to_unit: 页面 {unit_num} 不在page_labels中，跳过滚动")
            return
            
        # 确保scroll_area和垂直滚动条有效
        if self.scroll_area is None:
            return
            
        v_scroll = self.scroll_area.verticalScrollBar()
        if not v_scroll:
            return
        
        # 获取当前页面标签（提前获取并验证）
        current_page_label = self.page_labels.get(unit_num)
        if current_page_label is None:
            logging.debug(f"_scroll_to_unit: 页面 {unit_num} 的标签为None，跳过滚动")
            return
            
        # 强制更新所有页面标签的大小，确保高度计算准确
        for p in list(self.page_labels.keys()):
            page_label = self.page_labels.get(p)
            try:
                if page_label is not None:
                    page_label.adjustSize()
                    page_label.repaint()
            except Exception:
                # 如果page_label已被删除或无效，跳过
                continue
        
        # 强制刷新布局
        if self.pages_layout:
            # 确保pages_layout保持水平居中对齐
            self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.pages_layout.invalidate()
            self.pages_layout.activate()
            
        # 等待布局更新完成
        QApplication.processEvents()
        
        # 计算当前页在垂直布局中的位置
        target_y = 0
        from utils.constants import Constants
        spacing = Constants.PAGE_SPACING.value  # 使用统一的页面间距
        
        for p in range(unit_num):
            if p in self.page_labels:
                page_label = self.page_labels.get(p)
                try:
                    # 检查page_label是否仍然有效
                    if page_label is not None:
                        # 使用 sizeHint 获取期望高度，如果实际高度为0
                        height = page_label.height()
                        if height == 0:
                            height = page_label.sizeHint().height()
                        target_y += height + spacing
                except Exception:
                    # 如果page_label已被删除或无效，跳过
                    continue
        
        # 获取视口大小
        viewport_height = self.scroll_area.viewport().height()
        
        # 获取当前页面的高度（重新获取以确保有效性）
        try:
            current_page_height = current_page_label.height()
            # 如果实际高度为0，使用 sizeHint
            if current_page_height == 0:
                current_page_height = current_page_label.sizeHint().height()
        except Exception:
            # 如果current_page_label已被删除或无效，返回
            logging.debug(f"_scroll_to_unit: 无法获取页面 {unit_num} 的高度，跳过滚动")
            return
        
        # 计算滚动位置，使当前页面居中显示
        scroll_position = target_y - (viewport_height - current_page_height) // 2
        scroll_position = max(0, scroll_position)
        
        # 更新滚动条位置
        v_scroll.setValue(scroll_position)
    
    def _get_current_unit(self, page_num):
        """获取当前页码对应的单元索引（页码即单元索引）"""
        return page_num
    
    def _get_max_unit(self):
        """获取最大单元数（总页数）"""
        return self.viewtype_service.get_total_pages()
    
    def reset_display(self):
        """重置显示状态"""
        # 检查模式是否激活，非激活状态不清理布局
        if not self.is_active:
            return
            
        # 清理页面标签
        for page_num, page_label in list(self.page_labels.items()):
            if page_label is not None:
                try:
                    if self.pages_layout is not None:
                        self.pages_layout.removeWidget(page_label)
                    # 断开信号连接（在deleteLater之前）
                    try:
                        page_label.pixmapChanged.disconnect()
                    except (RuntimeError, TypeError):
                        # page_label已被销毁或信号未连接，忽略
                        pass
                    except Exception:
                        # 忽略其他异常
                        pass
                    page_label.deleteLater()
                except (RuntimeError, AttributeError):
                    # 忽略已删除或无效的页面标签
                    pass
        self.page_labels.clear()
        
        # 清理布局
        if self.pages_layout is not None:
            try:
                if self.pages_layout.parent() is not None:
                    self.pages_layout.parent().removeItem(self.pages_layout)
            except (RuntimeError, AttributeError):
                # 忽略已删除或无效的布局
                pass
            self.pages_layout = None
    
    def _on_render_completed(self, page_num, result, is_final):
        """处理渲染完成事件"""
        if result is None or not self.is_active:
            return
            
        # 检查页面标签是否存在
        if page_num not in self.page_labels:
            return
            
        page_label = self.page_labels[page_num]
        if page_label is None:
            return
            
        # 确保在主线程中执行GUI操作
        def update_gui():
            try:
                logging.debug(f"单页连续视图类型: 设置页面标签的pixmap，页码：{page_num}，pixmap大小：{result.size()}")
                page_label.setPixmap(result)
                page_label.show()
                logging.debug(f"单页连续视图类型: 页面标签显示，页码：{page_num}，可见性：{page_label.isVisible()}")
                
                # 确保布局更新
                self.viewtype_service.update_content_layout()
                
                # 强制scroll_area的widget调整大小
                if self.scroll_area is not None and self.scroll_area.widget() is not None:
                    self.scroll_area.widget().adjustSize()
            except Exception as e:
                logging.error(f"单页连续视图类型: 设置页面标签的pixmap失败，页码：{page_num}，错误：{str(e)}")
                # 如果页面标签已被删除，重新创建
                if "wrapped C/C++ object has been deleted" in str(e):
                    try:
                        new_page_label = ViewtypePageLabel(self)
                        new_page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
                        self.page_labels[page_num] = new_page_label
                        self.pages_layout.addWidget(new_page_label)
                        new_page_label.setPixmap(result)
                        new_page_label.show()
                        logging.debug(f"单页连续视图类型: 重新创建并添加了页面标签，页码：{page_num}，标签ID：{id(new_page_label)}")
                        
                        # 确保布局更新
                        self.viewtype_service.update_content_layout()
                    except Exception as e2:
                        logging.error(f"单页连续视图类型: 重新创建页面标签失败，页码：{page_num}，错误：{str(e2)}")
        
        # 使用QTimer.singleShot确保在主线程中执行
        from PyQt6.QtCore import QTimer
        if QApplication.instance():
            QTimer.singleShot(0, update_gui)
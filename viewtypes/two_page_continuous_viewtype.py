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
更新时间：2026-01-23
"""

import logging
from .base import ContinuousViewtype, ViewtypePageLabel
from services.event_bus import event_bus

class TwoPageContinuousViewtype(ContinuousViewtype):
    """双页连续浏览视图类型"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
        self.spread_labels = {}  # 存储双页标签
        # 订阅渲染完成事件
        event_bus.render_completed.connect(self._on_render_completed)
    
    def _show_single_unit(self, unit_num):
        """显示单个单元（双页）"""
        # 确保PDF文档已打开
        if self.viewtype_service.get_total_pages() == 0:
            logging.warning(f"双页连续视图类型: PDF文档未打开，无法显示双页{unit_num}")
            return
            
        # 计算双页的页码
        page1_num = unit_num * 2
        page2_num = min(page1_num + 1, self.viewtype_service.get_total_pages() - 1)
        
        # 确保pages_layout已经初始化，不再调用_create_layout，直接使用activate方法中创建的pages_layout
        if self.pages_layout is None:
            logging.warning(f"双页连续视图类型: pages_layout为None，无法显示双页{unit_num}")
            return
                
        # 创建或获取双页的PageLabel
        spread_key = f"spread_{unit_num}"
        page_label = None
        if spread_key not in self.spread_labels:
            try:
                page_label = ViewtypePageLabel(self)
                # 连接信号，在页面显示后更新布局
                page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
                self.spread_labels[spread_key] = page_label
                self.pages_layout.addWidget(page_label)
                logging.debug(f"双页连续视图类型: 创建并添加了双页标签，双页索引：{unit_num}，标签ID：{id(page_label)}")
            except Exception as e:
                logging.error(f"双页连续视图类型: 创建双页标签失败，双页索引：{unit_num}，错误：{str(e)}")
                return
        else:
            page_label = self.spread_labels[spread_key]
            logging.debug(f"双页连续视图类型: 获取了现有双页标签，双页索引：{unit_num}，标签ID：{id(page_label)}")
        
        # 直接合并两页并显示
        combined_pixmap = self._merge_two_pages(page1_num, page2_num)
        if combined_pixmap is not None:
            # 确保在主线程中执行GUI操作
            from PyQt6.QtWidgets import QApplication
            
            def update_gui():
                try:
                    logging.debug("双页连续视图类型: 设置双页标签的pixmap，双页索引：%d，pixmap大小：%s", unit_num, combined_pixmap.size())
                    page_label.setPixmap(combined_pixmap)
                    page_label.show()
                    logging.debug("双页连续视图类型: 双页标签显示，双页索引：%d，可见性：%s", unit_num, page_label.isVisible())
                    
                    # 直接调用update_content_layout来确保布局被正确更新
                    logging.debug("双页连续视图类型: 调用update_content_layout更新布局")
                    self.viewtype_service.update_content_layout()
                    logging.debug("双页连续视图类型: 布局更新完成")
                    
                    # 强制scroll_area的widget调整大小
                    if self.scroll_area is not None and self.scroll_area.widget() is not None:
                        logging.debug("双页连续视图类型: 调整scroll_area widget大小")
                        self.scroll_area.widget().adjustSize()
                        logging.debug("双页连续视图类型: scroll_area widget大小调整完成")
                except Exception as e:
                    logging.error("双页连续视图类型: 设置双页标签的pixmap失败，双页索引：%d，错误：%s", unit_num, str(e))
                    # 如果页面标签已被删除，重新创建
                    if "wrapped C/C++ object has been deleted" in str(e):
                        try:
                            new_page_label = ViewtypePageLabel(self)
                            new_page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
                            self.spread_labels[spread_key] = new_page_label
                            self.pages_layout.addWidget(new_page_label)
                            new_page_label.setPixmap(combined_pixmap)
                            new_page_label.show()
                            logging.debug("双页连续视图类型: 重新创建并添加了双页标签，双页索引：%d，标签ID：%s", unit_num, id(new_page_label))
                            
                            # 确保布局更新
                            self.viewtype_service.update_content_layout()
                        except Exception as e2:
                            logging.error("双页连续视图类型: 重新创建双页标签失败，双页索引：%d，错误：%s", unit_num, str(e2))
            
            # 使用QTimer.singleShot确保在主线程中执行
            from PyQt6.QtCore import QTimer
            if QApplication.instance():
                QTimer.singleShot(0, update_gui)
    
    def _scroll_to_unit(self, unit_num):
        """滚动到指定单元（双页）"""
        spread_key = f"spread_{unit_num}"
        if spread_key not in self.spread_labels:
            return
            
        # 确保scroll_area和垂直滚动条有效
        if self.scroll_area is None:
            return
            
        v_scroll = self.scroll_area.verticalScrollBar()
        if not v_scroll:
            return
            
        # 强制更新所有双页标签的大小，确保高度计算准确
        for key in self.spread_labels:
            page_label = self.spread_labels[key]
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
            from PyQt6.QtCore import Qt
            self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.pages_layout.invalidate()
            self.pages_layout.activate()
            
        # 等待布局更新完成
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # 计算当前双页在垂直布局中的位置
        target_y = 0
        from utils.constants import Constants
        spacing = Constants.PAGE_SPACING.value  # 使用统一的页面间距
        
        for i in range(unit_num):
            key = f"spread_{i}"
            if key in self.spread_labels:
                page_label = self.spread_labels[key]
                try:
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
        
        # 获取当前双页的高度
        current_spread_label = self.spread_labels[spread_key]
        try:
            if current_spread_label is not None:
                current_spread_height = current_spread_label.height()
                # 如果实际高度为0，使用 sizeHint
                if current_spread_height == 0:
                    current_spread_height = current_spread_label.sizeHint().height()
            else:
                return
        except Exception:
            # 如果current_spread_label已被删除或无效，返回
            return
        
        # 计算滚动位置，使当前双页居中显示
        scroll_position = target_y - (viewport_height - current_spread_height) // 2
        scroll_position = max(0, scroll_position)
        
        # 更新滚动条位置
        v_scroll.setValue(scroll_position)
    
    def _get_current_unit(self, page_num):
        """获取当前页码对应的单元索引（双页索引）"""
        return page_num // 2
    
    def _get_max_unit(self):
        """获取最大单元数（双页数量）"""
        return (self.viewtype_service.get_total_pages() + 1) // 2
    
    def reset_display(self):
        """重置显示状态"""
        # 检查模式是否激活，非激活状态不清理布局
        if not self.is_active:
            return
            
        # 清理双页标签
        for spread_key, page_label in list(self.spread_labels.items()):
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
        self.spread_labels.clear()
        
        # 清理布局
        if self.pages_layout is not None:
            try:
                if self.pages_layout.parent() is not None:
                    self.pages_layout.parent().removeItem(self.pages_layout)
            except (RuntimeError, AttributeError):
                # 忽略已删除或无效的布局
                pass
            self.pages_layout = None
    
    def on_state_changed(self, state_name, old_value, new_value):
        """处理状态变化"""
        # 调用基类的on_state_changed方法处理通用逻辑
        super().on_state_changed(state_name, old_value, new_value)
        
        try:
            # 只处理缩放级别变化时的页面更新
            if state_name == "zoom_level":
                # 更新所有双页的显示
                for spread_key, label in self.spread_labels.items():
                    if label.isVisible():
                        # 从key中提取spread_num
                        spread_num = int(spread_key.split('_')[1])
                        page1_num = spread_num * 2
                        page2_num = min(page1_num + 1, self.viewtype_service.get_total_pages() - 1)
                        
                        # 使用基类的双页合并方法
                        combined_pixmap = self._merge_two_pages(page1_num, page2_num)
                        
                        if combined_pixmap is not None:
                            label.setPixmap(combined_pixmap)
        except Exception as e:
            self._handle_exception(f"处理状态变化失败: {str(e)}")
            # 尝试回滚到之前的状态
            self._rollback_state(state_name, old_value)
    
    def _on_render_completed(self, page_num, result, is_final):
        """处理渲染完成事件"""
        if result is None or not self.is_active:
            return
            
        # 计算当前页面所属的双页单元
        spread_num = page_num // 2
        spread_key = f"spread_{spread_num}"
        
        # 检查双页标签是否存在
        if spread_key not in self.spread_labels:
            return
            
        page_label = self.spread_labels[spread_key]
        if page_label is None:
            return
            
        # 计算双页的页码
        page1_num = spread_num * 2
        page2_num = min(page1_num + 1, self.viewtype_service.get_total_pages() - 1)
        
        # 重新合并两页并显示
        combined_pixmap = self._merge_two_pages(page1_num, page2_num)
        if combined_pixmap is not None:
            # 确保在主线程中执行GUI操作
            from PyQt6.QtWidgets import QApplication
            
            def update_gui():
                try:
                    logging.debug("双页连续视图类型: 设置双页标签的pixmap，双页索引：%d，pixmap大小：%s", spread_num, combined_pixmap.size())
                    page_label.setPixmap(combined_pixmap)
                    page_label.show()
                    logging.debug("双页连续视图类型: 双页标签显示，双页索引：%d，可见性：%s", spread_num, page_label.isVisible())
                    
                    # 直接调用update_content_layout来确保布局被正确更新
                    logging.debug("双页连续视图类型: 调用update_content_layout更新布局")
                    self.viewtype_service.update_content_layout()
                    logging.debug("双页连续视图类型: 布局更新完成")
                    
                    # 强制scroll_area的widget调整大小
                    if self.scroll_area is not None and self.scroll_area.widget() is not None:
                        logging.debug("双页连续视图类型: 调整scroll_area widget大小")
                        self.scroll_area.widget().adjustSize()
                        logging.debug("双页连续视图类型: scroll_area widget大小调整完成")
                except Exception as e:
                    logging.error("双页连续视图类型: 设置双页标签的pixmap失败，双页索引：%d，错误：%s", spread_num, str(e))
                    # 如果页面标签已被删除，重新创建
                    if "wrapped C/C++ object has been deleted" in str(e):
                        try:
                            new_page_label = ViewtypePageLabel(self)
                            new_page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
                            self.spread_labels[spread_key] = new_page_label
                            self.pages_layout.addWidget(new_page_label)
                            new_page_label.setPixmap(combined_pixmap)
                            new_page_label.show()
                            logging.debug("双页连续视图类型: 重新创建并添加了双页标签，双页索引：%d，标签ID：%s", spread_num, id(new_page_label))
                            
                            # 确保布局更新
                            self.viewtype_service.update_content_layout()
                        except Exception as e2:
                            logging.error("双页连续视图类型: 重新创建双页标签失败，双页索引：%d，错误：%s", spread_num, str(e2))
            
            # 使用QTimer.singleShot确保在主线程中执行
            from PyQt6.QtCore import QTimer
            if QApplication.instance():
                QTimer.singleShot(0, update_gui)
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
                # 布局与内容解耦：在 addWidget 前预测双页合并尺寸并设置占位
                try:
                    from utils.constants import Constants
                    spacing = Constants.PAGE_SPACING.value
                    size1 = self.viewtype_service.get_page_size(page1_num, self.zoom_level)
                    size2 = self.viewtype_service.get_page_size(page2_num, self.zoom_level) if page2_num != page1_num else (0, 0)
                    if size1 and size1[0] > 0 and size1[1] > 0:
                        w = size1[0] + (size2[0] if size2 else 0) + (spacing if size2 and size2[0] > 0 else 0)
                        h = max(size1[1], size2[1] if size2 else 0)
                        page_label.setMinimumSize(w, h)
                except Exception as e:
                    logging.debug(f"双页连续视图类型: 获取双页预测尺寸失败，双页索引：{unit_num}，错误：{str(e)}")
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
        
        # 直接合并两页并设置pixmap（同步操作，不使用 QTimer.singleShot）
        # 这避免了异步回调中 adjustSize() 改变滚动区域高度导致的回跳问题
        combined_pixmap = self._merge_two_pages(page1_num, page2_num)
        if combined_pixmap is not None:
            try:
                page_label.setPixmap(combined_pixmap)
                page_label.show()
                logging.debug(f"双页连续视图类型: 设置双页标签的pixmap，双页索引：{unit_num}，pixmap大小：{combined_pixmap.size()}")
            except Exception as e:
                logging.error(f"双页连续视图类型: 设置双页标签的pixmap失败，双页索引：{unit_num}，错误：{str(e)}")
                # 如果页面标签已被删除，重新创建
                if "wrapped C/C++ object has been deleted" in str(e):
                    try:
                        new_page_label = ViewtypePageLabel(self)
                        new_page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
                        self.spread_labels[spread_key] = new_page_label
                        self.pages_layout.addWidget(new_page_label)
                        new_page_label.setPixmap(combined_pixmap)
                        new_page_label.show()
                        logging.debug(f"双页连续视图类型: 重新创建并添加了双页标签，双页索引：{unit_num}，标签ID：{id(new_page_label)}")
                    except Exception as e2:
                        logging.error(f"双页连续视图类型: 重新创建双页标签失败，双页索引：{unit_num}，错误：{str(e2)}")
    
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
            
        # 强制更新所有双页标签的大小，确保高度计算准确（按索引升序处理）
        for key in sorted(self.spread_labels.keys(), key=lambda k: int(k.split('_')[1])):
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
            
        # 延迟执行滚动定位，避免 processEvents 重入
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._scroll_to_unit_deferred(unit_num))
    
    def _scroll_to_unit_deferred(self, unit_num):
        """延迟执行的滚动定位（布局稳定后再计算）"""
        spread_key = f"spread_{unit_num}"
        if spread_key not in self.spread_labels:
            return
        
        if self.scroll_area is None:
            return
        
        v_scroll = self.scroll_area.verticalScrollBar()
        if not v_scroll:
            return
        
        current_spread_label = self.spread_labels.get(spread_key)
        if current_spread_label is None:
            return
        target_y = 0
        from utils.constants import Constants
        spacing = Constants.PAGE_SPACING.value
        
        # 计算已存在 spread 标签的平均高度，用于估算缺失的高度
        estimated_height = 0
        label_count = 0
        for key, sl in sorted(self.spread_labels.items(), key=lambda x: int(x[0].split('_')[1])):
            try:
                if sl is not None:
                    h = sl.height()
                    if h == 0:
                        h = sl.minimumSize().height()
                        if h == 0:
                            h = sl.sizeHint().height()
                    if h > 0:
                        estimated_height += h
                        label_count += 1
            except Exception:
                continue
        if label_count > 0:
            estimated_height = estimated_height // label_count
            # 确保 estimated_height 至少有一个合理的最小值
            if estimated_height < 100:
                estimated_height = 620
        else:
            try:
                estimated_height = current_spread_label.height()
                if estimated_height == 0:
                    estimated_height = current_spread_label.minimumSize().height()
                    if estimated_height == 0:
                        estimated_height = current_spread_label.sizeHint().height()
                if estimated_height < 100:
                    estimated_height = 620
            except Exception:
                estimated_height = 620

        for i in range(unit_num):
            key = f"spread_{i}"
            if key in self.spread_labels:
                page_label = self.spread_labels[key]
                try:
                    if page_label is not None:
                        height = page_label.height()
                        if height == 0:
                            height = page_label.minimumSize().height()
                            if height == 0:
                                height = page_label.sizeHint().height()
                        target_y += height + spacing
                except Exception:
                    target_y += estimated_height + spacing
            else:
                target_y += estimated_height + spacing
        
        # 获取视口大小
        viewport_height = self.scroll_area.viewport().height()

        # 获取当前双页的高度
        # 优先使用 minimumSize（我们在 _show_single_unit 中设置的预测高度），
        # 而不是 sizeHint
        current_spread_label = self.spread_labels[spread_key]
        try:
            if current_spread_label is not None:
                current_spread_height = current_spread_label.height()
                if current_spread_height == 0:
                    current_spread_height = current_spread_label.minimumSize().height()
                    if current_spread_height == 0:
                        current_spread_height = current_spread_label.sizeHint().height()
            else:
                return
        except Exception:
            return
        
        # 计算滚动位置，使当前双页居中显示
        scroll_position = target_y - (viewport_height - current_spread_height) // 2
        scroll_position = max(0, scroll_position)
        
        # 程序主动设置滚动位置时，阻断 valueChanged 信号
        # 防止 ThumbnailSync 把这次滚动解释为用户翻页
        self._programmatic_scroll = True
        # 更新滚动条位置
        v_scroll.setValue(scroll_position)
        # 延迟释放锁
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(300, self._release_programmatic_scroll)
    
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
                        else:
                            # 保底：pixmap 为 None 时预测双页合并尺寸，防止缩小时残留
                            try:
                                from utils.constants import Constants
                                spacing = Constants.PAGE_SPACING.value
                                size1 = self.viewtype_service.get_page_size(page1_num, new_value)
                                size2 = self.viewtype_service.get_page_size(page2_num, new_value) if page2_num != page1_num else (0, 0)
                                if size1 and size1[0] > 0 and size1[1] > 0:
                                    w = size1[0] + (size2[0] if size2 else 0) + (spacing if size2 and size2[0] > 0 else 0)
                                    h = max(size1[1], size2[1] if size2 else 0)
                                    label.setMinimumSize(w, h)
                            except Exception:
                                pass
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
        
        # 重新合并两页并显示（同步操作，避免异步回调中的 adjustSize 问题）
        combined_pixmap = self._merge_two_pages(page1_num, page2_num)
        if combined_pixmap is not None:
            try:
                page_label.setPixmap(combined_pixmap)
                page_label.show()
            except Exception as e:
                logging.error(f"双页连续视图类型: 渲染完成设置pixmap失败，双页索引：{spread_num}，错误：{str(e)}")
                if "wrapped C/C++ object has been deleted" in str(e):
                    try:
                        new_page_label = ViewtypePageLabel(self)
                        new_page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
                        self.spread_labels[spread_key] = new_page_label
                        self.pages_layout.addWidget(new_page_label)
                        new_page_label.setPixmap(combined_pixmap)
                        new_page_label.show()
                    except Exception as e2:
                        logging.error(f"双页连续视图类型: 渲染完成重新创建标签失败，双页索引：{spread_num}，错误：{str(e2)}")
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
                # 布局与内容解耦：在 addWidget 前用 get_page_size 预测尺寸并设置占位，
                # 让布局引擎在异步渲染完成前就知道 widget 的真实高度
                try:
                    predicted_size = self.viewtype_service.get_page_size(
                        unit_num, self.zoom_level)
                    logging.warning(f"[_show_single_unit] unit_num={unit_num}, predicted_size={predicted_size}, zoom={self.zoom_level}")
                    if predicted_size and predicted_size[0] > 0 and predicted_size[1] > 0:
                        page_label.setMinimumSize(predicted_size[0], predicted_size[1])
                        logging.warning(f"[_show_single_unit] setMinimumSize({predicted_size[0]}, {predicted_size[1]})")
                except Exception as e:
                    logging.warning(f"单页连续视图类型: 获取页面预测尺寸失败，页码：{unit_num}，错误：{str(e)}")
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
            
        # 强制更新所有页面标签的大小，确保高度计算准确（按页码升序处理）
        for p in sorted(self.page_labels.keys()):
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
            
        # 让布局引擎处理完排队的更新后再计算滚动位置
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._scroll_to_unit_deferred(unit_num))

    def _scroll_to_unit_deferred(self, unit_num):
        """延迟执行的滚动定位（布局稳定后再计算）"""
        if self.scroll_area is None:
            return
        v_scroll = self.scroll_area.verticalScrollBar()
        if not v_scroll:
            return

        current_page_label = self.page_labels.get(unit_num)
        if current_page_label is None:
            return

        from utils.constants import Constants
        spacing = Constants.PAGE_SPACING.value

        # 关键修复：遍历实际布局中的 widget，而不是按页码累加
        # 布局中的 widget 顺序才是正确的累计顺序
        target_y = 0
        target_widget = None

        logging.warning(f"[_scroll_to_unit_deferred] unit={unit_num}, layout_count={self.pages_layout.count() if self.pages_layout else 0}")
        if self.pages_layout is not None:
            for i in range(self.pages_layout.count()):
                item = self.pages_layout.itemAt(i)
                widget = item.widget()
                if widget is not None:
                    # 找到目标页面时，停止累加（不需要加目标 widget 自己的高度）
                    if widget == current_page_label:
                        target_widget = widget
                        logging.warning(f"[_scroll_to_unit_deferred] found target at i={i}, widget={id(widget)}, accumulated before adding target={target_y}")
                        break
                    # 累加当前 widget 的高度
                    h = widget.height()
                    min_h = widget.minimumSize().height()
                    hint_h = widget.sizeHint().height()
                    used_h = h if h > 0 else (min_h if min_h > 0 else hint_h)
                    logging.warning(f"[_scroll_to_unit_deferred] i={i}, h={h}, min={min_h}, hint={hint_h}, used={used_h}")
                    target_y += used_h + spacing

        logging.warning(f"[_scroll_to_unit_deferred] FINAL target_y={target_y}, target_widget={'found' if target_widget else 'NOT found'}")

        # 如果布局遍历失败，使用旧的备选方案
        if target_widget is None:
            logging.warning(f"[_scroll_to_unit_deferred] layout traversal failed, using fallback")
            target_y = 0
            # 估算平均高度
            estimated_height = 620
            for p, pl in sorted(self.page_labels.items()):
                try:
                    if pl:
                        h = pl.height()
                        if h == 0:
                            h = pl.minimumSize().height()
                            if h == 0:
                                h = pl.sizeHint().height()
                        if h > 0:
                            estimated_height = (estimated_height + h) // 2
                except Exception:
                    pass

            for p in range(unit_num):
                if p in self.page_labels:
                    pl = self.page_labels.get(p)
                    if pl:
                        h = pl.height()
                        if h == 0:
                            h = pl.minimumSize().height()
                            if h == 0:
                                h = pl.sizeHint().height()
                        target_y += h + spacing
                else:
                    target_y += estimated_height + spacing

        # 获取视口大小
        viewport_height = self.scroll_area.viewport().height()

        # 获取当前页面的高度
        # 优先使用 minimumSize（我们在 _show_single_unit 中设置的预测高度），
        # 而不是 sizeHint（sizeHint 在没有 pixmap 时返回很小的默认值）
        try:
            current_page_height = current_page_label.height()
            if current_page_height == 0:
                current_page_height = current_page_label.minimumSize().height()
                if current_page_height == 0:
                    current_page_height = current_page_label.sizeHint().height()
        except Exception:
            return

        # 计算滚动位置，使当前页面居中显示
        scroll_position = target_y - (viewport_height - current_page_height) // 2
        scroll_position = max(0, scroll_position)

        logging.warning(f"[_scroll_to_unit_deferred] scroll_position={scroll_position}, target_y={target_y}, viewport={viewport_height}, current_height={current_page_height}")

        # 程序主动设置滚动位置时，阻断 valueChanged 信号
        # 防止 ThumbnailSync 把这次滚动解释为用户翻页
        self._programmatic_scroll = True
        v_scroll.setValue(scroll_position)
        # 延迟释放锁
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(300, self._release_programmatic_scroll)

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
            
        # 同步设置 pixmap（避免异步回调中的 adjustSize 导致回跳）
        try:
            page_label.setPixmap(result)
            page_label.show()
            logging.debug(f"单页连续视图类型: 设置页面标签的pixmap，页码：{page_num}，pixmap大小：{result.size()}")
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
                except Exception as e2:
                    logging.error(f"单页连续视图类型: 重新创建页面标签失败，页码：{page_num}，错误：{str(e2)}")
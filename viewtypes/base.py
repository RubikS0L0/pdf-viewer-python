"""
浏览模式基础模块

定义浏览模式抽象基类，实现模式通用功能和接口，
提供节流装饰器、坐标转换和事件处理功能。
"""

import sys
import os
# 添加项目根目录到模块搜索路径，解决直接运行时的导入问题
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abc import ABC, abstractmethod
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import Qt, QRect, pyqtSignal
import logging
from functools import wraps
import time

# Import config loader and constants
from utils.config_loader import config_loader
from utils.constants import Constants

# Import handlers
from .handlers import ScrollHandler, ZoomHandler, SelectionRenderer, DetectionRenderer

# Import event bus
from services.event_bus import event_bus

# 节流装饰器：限制函数调用频率
def throttle(delay=None):
    """节流装饰器，限制函数在指定时间内只能被调用一次
    
    参数:
        delay: 延迟时间（毫秒），默认从配置文件加载
    
    返回:
        装饰后的函数
    """
    # 从配置文件获取默认延迟时间
    if delay is None:
        ui_config = config_loader.get_ui_config()
        delay = ui_config.get("throttle_delay", 16)
    def decorator(func):
        last_call_time = 0
        is_throttling = False
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            nonlocal last_call_time, is_throttling
            current_time = time.time() * 1000  # 转换为毫秒
            
            if current_time - last_call_time >= delay:
                # 如果超过延迟时间，立即执行
                func(self, *args, **kwargs)
                last_call_time = current_time
                is_throttling = False
            elif not is_throttling:
                # 如果在延迟时间内，且没有正在延迟的调用，使用QTimer执行延迟调用
                is_throttling = True
                
                from PyQt6.QtCore import QTimer, QCoreApplication
                
                def delayed_call():
                    nonlocal last_call_time, is_throttling
                    current_time = time.time() * 1000
                    if is_throttling and current_time - last_call_time >= delay:
                        func(self, *args, **kwargs)
                        last_call_time = current_time
                        is_throttling = False
                
                # 使用QTimer确保在主线程中执行
                if QCoreApplication.instance():
                    QTimer.singleShot(delay, delayed_call)
        
        return wrapper
    
    return decorator
"""
浏览模式抽象基类
定义所有浏览模式必须实现的核心方法
包含PageLabel的所有核心功能
"""

class ViewtypePageLabel(QLabel):
    """自定义页面显示标签，与浏览视图类型关联"""
    
    # 定义pixmapChanged信号
    pixmapChanged = pyqtSignal()
    
    def __init__(self, browsing_viewtype):
        super().__init__()
        self.browsing_viewtype = browsing_viewtype
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True)
        self.current_pixmap = None
        
    def setPixmap(self, pixmap):
        """设置页面图像"""
        self.current_pixmap = pixmap
        super().setPixmap(pixmap)
        self.updateGeometry()
        
        # 触发信号，通知布局更新
        self.pixmapChanged.emit()
        
    def pixmap(self):
        """获取当前图像"""
        return self.current_pixmap
        
    def sizeHint(self):
        """返回尺寸提示"""
        if self.current_pixmap:
            return self.current_pixmap.size()
        return super().sizeHint()
        
    def wheelEvent(self, event):
        """处理鼠标滚轮事件，委托给浏览视图类型"""
        if self.browsing_viewtype:
            # 调用浏览视图类型的处理方法
            self.browsing_viewtype.handle_wheel_event(event)
            # 如果事件没有被处理（没有调用event.accept()），则调用默认处理
            if not event.isAccepted():
                super().wheelEvent(event)
        else:
            super().wheelEvent(event)
            
    def mouseMoveEvent(self, event):
        """处理鼠标移动事件，实现光标跟随缩略图预览框移动"""
        if self.browsing_viewtype:
            self.browsing_viewtype.handle_mouse_move(event)
        super().mouseMoveEvent(event)
            
    def paintEvent(self, event):
        """重写绘制事件"""
        # 先调用父类绘制pixmap
        super().paintEvent(event)
        
        # 委托给浏览视图类型处理绘制选择框和检测结果
        if self.browsing_viewtype:
            painter = QPainter(self)
            self.browsing_viewtype.draw_selection_box(painter)
            self.browsing_viewtype.draw_detection_results(painter)
            painter.end()

class BrowsingViewtype(ABC):
    """浏览视图类型抽象基类"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        """初始化浏览视图类型"""
        # 初始化日志记录器
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.viewtype_service = viewtype_service
        self.pdf_viewer = pdf_viewer
        # 延迟初始化scroll_area相关组件，直到activate()方法被调用
        self.scroll_area = None
        self.center_container = None
        self.center_layout = None
        self.page_label = None  # 将在子类中初始化
        self.is_active = False
        
        # 简化状态管理
        self._current_pixmap = None
        
        # 初始化处理器（职责分离）
        self.scroll_handler = ScrollHandler(self)
        self.zoom_handler = ZoomHandler(self)
        self.selection_renderer = SelectionRenderer(self)
        self.detection_renderer = DetectionRenderer(self)
    
    # 简化的状态访问属性
    @property
    def current_page(self):
        return self.viewtype_service.get_current_page()
    
    @current_page.setter
    def current_page(self, value):
        # 直接设置pdf_viewer的current_page属性，避免递归调用
        self.pdf_viewer.current_page = value
    
    @property
    def zoom_level(self):
        return self.viewtype_service.get_zoom_level()
    
    @zoom_level.setter
    def zoom_level(self, value):
        self.viewtype_service.set_zoom_level(value)
    
    @property
    def detection_results(self):
        return self.viewtype_service.get_detection_results()
    
    @property
    def results_mutex(self):
        return self.viewtype_service.get_results_mutex()
    
    @property
    def selecting(self):
        return self.viewtype_service.get_selecting()
    
    @selecting.setter
    def selecting(self, value):
        self.viewtype_service.set_selecting(value)
    
    @property
    def select_start_pdf(self):
        return self.viewtype_service.get_select_start_pdf()
    
    @select_start_pdf.setter
    def select_start_pdf(self, value):
        self.viewtype_service.set_select_start_pdf(value)
    
    @property
    def select_end_pdf(self):
        return self.viewtype_service.get_select_end_pdf()
    
    @select_end_pdf.setter
    def select_end_pdf(self, value):
        self.viewtype_service.set_select_end_pdf(value)
    
    @property
    def current_pixmap(self):
        return self._current_pixmap if hasattr(self, '_current_pixmap') else None
    
    @current_pixmap.setter
    def current_pixmap(self, value):
        self._current_pixmap = value
    
    # 新增状态变化处理方法
    def on_state_changed(self, state_name, old_value, new_value):
        """处理状态变化通知"""
        # 调用基础状态变化处理方法
        if not self.on_state_changed_base(state_name, old_value, new_value):
            return
            
        # 子类可以重写此方法以添加模式特定的处理逻辑
        try:
            if state_name == "zoom_level":
                self.update_config()
            elif state_name == "zoom_mode":
                self.update_config()
            elif state_name == "current_page":
                self.show_page(new_value)
        except Exception as e:
            self._handle_exception(f"处理状态变化失败: {str(e)}")
            # 尝试回滚到之前的状态
            self._rollback_state(state_name, old_value)

    def on_state_changed_base(self, state_name, old_value, new_value):
        """基础状态变化处理方法"""
        # 检查模式是否激活
        if not self.is_active:
            return False
            
        # 检查状态是否真正改变
        if old_value == new_value:
            return False
            
        return True

    def _rollback_state(self, state_name, old_value):
        """回滚到之前的状态"""
        try:
            if state_name == "zoom_level":
                self.zoom_level = old_value
            elif state_name == "zoom_mode":
                self.zoom_mode = old_value
            elif state_name == "current_page":
                self.current_page = old_value
        except Exception as e:
            self._handle_exception(f"状态回滚失败: {str(e)}")

    def _handle_exception(self, message):
        """处理异常并记录日志"""
        self.logger.error(f"模式 {self.__class__.__name__} {message}")

    def update_config_base(self):
        """基础配置更新方法"""
        # 检查模式是否激活
        if not self.is_active:
            return
            
        # 基本布局刷新
        if self.center_layout is not None:
            self.center_layout.invalidate()
            self.center_layout.activate()

    def reset_display_base(self):
        """基础显示重置方法"""
        # 清理页面标签（如果存在且有效）
        if hasattr(self, 'page_label') and self.page_label:
            try:
                # 检查 page_label 和 center_layout 是否有效
                if self.center_layout and self.page_label.parent():
                    self.center_layout.removeWidget(self.page_label)
                # 断开信号连接（在deleteLater之前）
                try:
                    self.page_label.pixmapChanged.disconnect()
                except (RuntimeError, TypeError):
                    # page_label已被销毁或信号未连接，忽略
                    pass
                except Exception:
                    # 忽略其他异常
                    pass
                self.page_label.deleteLater()
                self.page_label = None
            except (RuntimeError, AttributeError):
                # 如果 page_label 已经被删除或属性不存在，直接设置为 None
                self.page_label = None

    def _add_layout_to_container(self, layout, container=None):
        """将布局添加到容器中"""
        if not layout:
            return
            
        # 使用默认容器（center_layout）如果未指定
        target_container = container if container else self.center_layout
        
        # 移除布局从当前父容器
        if layout.parent():
            layout.parent().removeItem(layout)
            
        # 添加布局到目标容器
        target_container.addLayout(layout)
    
    def activate_base(self):
        """基础激活方法，初始化scroll_area相关组件"""
        # 初始化scroll_area相关组件
        self.scroll_area = self.pdf_viewer.scroll_area
        
        # 优先从ContentArea实例获取center_layout和center_container，这样更可靠
        if hasattr(self.pdf_viewer, 'content_area') and self.pdf_viewer.content_area:
            self.center_layout = self.pdf_viewer.content_area.get_center_layout()
            self.center_container = self.pdf_viewer.content_area.get_center_container()
        elif self.scroll_area:
            # 回退到原来的方式
            self.center_container = self.scroll_area.widget()
            if self.center_container:
                self.center_layout = self.center_container.layout()
        
    def save_scroll_position(self):
        """保存当前滚动位置"""
        self.scroll_handler.save_scroll_position()
        
    def restore_scroll_position(self):
        """恢复滚动位置"""
        self.scroll_handler.restore_scroll_position()
    
    def activate(self):
        """激活浏览模式"""
        # 调用钩子方法
        self._before_activate()
        
        # 调用父类基础激活方法，初始化scroll_area相关组件
        self.activate_base()
        
        # 重置显示状态（无条件清理）
        self.reset_display()
        
        # 确保center_layout有效
        if not self._ensure_center_layout():
            return
            
        # 激活模式
        self._activate_mode()
        
        # 初始化页面标签
        self._initialize_page_label()
        
        # 显示当前页面
        self.show_page(self.viewtype_service.get_current_page())
        
        # 调用钩子方法
        self._after_activate()
    
    def _ensure_center_layout(self):
        """确保center_layout有效"""
        if self.center_layout is None:
            # 直接从ContentArea获取，不依赖scroll_area和center_container
            if hasattr(self.pdf_viewer, 'content_area') and self.pdf_viewer.content_area is not None:
                self.center_layout = self.pdf_viewer.content_area.get_center_layout()
                self.center_container = self.pdf_viewer.content_area.get_center_container()
            else:
                logging.warning(f"{self.__class__.__name__} 激活失败：center_layout 为 None")
                return False
        return True
    
    def _activate_mode(self):
        """激活模式"""
        # 设置模式为激活状态
        self.is_active = True
        
        # 订阅缩放变化事件
        if hasattr(self.pdf_viewer, 'zoom_service'):
            self.pdf_viewer.zoom_service.add_observer(self)
        
        # 设置布局为完全居中
        self.center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def _initialize_page_label(self):
        """初始化页面标签"""
        # 创建ViewtypePageLabel实例
        self.page_label = ViewtypePageLabel(self)
        # 连接信号，在页面显示后更新布局
        self.page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
        self.center_layout.addWidget(self.page_label)
    
    def deactivate(self):
        """停用浏览模式"""
        # 调用钩子方法
        self._before_deactivate()
        
        # 取消订阅缩放变化事件
        if hasattr(self.pdf_viewer, 'zoom_service'):
            self.pdf_viewer.zoom_service.remove_observer(self)
        
        self.is_active = False
        self.reset_display()
        
        # 调用钩子方法
        self._after_deactivate()
    
    def reset_display(self):
        """重置显示状态"""
        # 调用基类的基础显示重置方法
        self.reset_display_base()
    
    def update_config(self):
        """更新配置（如缩放级别变化时）"""
        # 调用基类的基础配置更新方法
        self.update_config_base()
        
        # 强制布局更新
        if self.center_layout is not None:
            self.center_layout.invalidate()
            self.center_layout.activate()
        
        # 确保page_label的几何信息更新
        if self.page_label is not None:
            self.page_label.updateGeometry()
    
    @abstractmethod
    def show_page(self, page_num):
        """显示指定页码的页面"""
        pass
    
    # 钩子方法，子类可以重写
    def _before_activate(self):
        """激活前的钩子方法"""
        pass
    
    def _after_activate(self):
        """激活后的钩子方法"""
        pass
    
    def _before_deactivate(self):
        """停用时的钩子方法"""
        pass
    
    def _after_deactivate(self):
        """停用后的钩子方法"""
        pass
    
    def handle_mouse_move(self, event):
        """处理鼠标移动事件
        
        子类可以重写此方法来添加模式特定的鼠标移动处理逻辑
        """
        # 默认不做任何处理，子类可以重写
        pass
        
    def handle_wheel_event(self, event):
        """处理鼠标滚轮事件
        
        支持ctrl+鼠标滚轮缩放功能，根据ctrl键状态决定是缩放还是滚动
        """
        from PyQt6.QtCore import Qt
        
        try:
            # 检查是否按下了ctrl键
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                # Ctrl+鼠标滚轮：缩放功能
                self._handle_zoom_wheel(event)
            else:
                # 普通鼠标滚轮：滚动或翻页
                self.scroll_handler.handle_wheel_event(event)
        except Exception as e:
            self.logger.error(f"处理鼠标滚轮事件失败: {str(e)}")
    
    def _handle_zoom_wheel(self, event):
        """处理缩放滚轮事件"""
        from utils.constants import Constants
        
        delta = event.angleDelta().y()
        if delta != 0:
            # 计算缩放比例变化（每滚动一格滚轮，缩放5%）
            zoom_delta = Constants.ZOOM_DELTA.value if delta > 0 else 1.0 / Constants.ZOOM_DELTA.value
            new_zoom = self.zoom_level * zoom_delta
            
            # 限制缩放范围
            new_zoom = max(Constants.MIN_ZOOM.value, min(new_zoom, Constants.MAX_ZOOM.value))
            
            if abs(new_zoom - self.zoom_level) > 0.01:  # 避免微小变化
                # 更新ZoomService中的缩放级别
                self.viewtype_service.set_zoom_level(new_zoom)
                # 清除该页面在当前缩放级别的缓存
                if hasattr(self.pdf_viewer, 'page_cache'):
                    self.pdf_viewer.page_cache.remove_page(self.current_page, new_zoom)
                # 重新显示页面
                self.viewtype_service.show_page(self.current_page)
                # 更新缩放控件
                if hasattr(self.pdf_viewer, 'zoom_controller') and hasattr(self.pdf_viewer.zoom_controller, 'update_zoom_controls'):
                    self.pdf_viewer.zoom_controller.update_zoom_controls()
                event.accept()
    
    def set_page_pixmap(self, pixmap):
        """设置页面图像"""
        self.current_pixmap = pixmap
        if self.page_label:
            self.page_label.setPixmap(pixmap)
            self.page_label.updateGeometry()
    
    def _on_page_changed(self, page_num):
        """页面变化时的处理方法
        
        发布page_updated事件，通知其他组件页面已更新
        
        参数：
        - page_num: int, 页面编号
        """
        try:
            # 发布页面更新事件
            event_bus.publish_page_updated(page_num)
        except Exception as e:
            self._handle_exception(f"发布页面更新事件失败: {str(e)}")
    
    def pdf_to_screen(self, pdf_x, pdf_y):
        """PDF坐标转屏幕坐标"""
        return self.selection_renderer.pdf_to_screen(pdf_x, pdf_y)
    
    def screen_to_pdf(self, screen_x, screen_y):
        """屏幕坐标转PDF坐标"""
        return self.selection_renderer.screen_to_pdf(screen_x, screen_y)
    
    def draw_selection_box(self, painter):
        """绘制选择框"""
        self.selection_renderer.draw_selection_box(painter)
    
    def draw_detection_results(self, painter):
        """绘制检测结果"""
        self.detection_renderer.draw_detection_results(painter)
    
    def set_select_state(self, selecting, start_pdf, end_pdf):
        """设置选择状态"""
        self.selection_renderer.set_select_state(selecting, start_pdf, end_pdf)
    
    def on_zoom_changed(self, zoom_level):
        """处理缩放变化事件"""
        self.zoom_handler.on_zoom_changed(zoom_level)
    
    def _merge_two_pages(self, page1_num, page2_num):
        """合并两页为一个pixmap"""
        page1_pixmap = self.viewtype_service.get_page_pixmap(page1_num)
        page2_pixmap = self.viewtype_service.get_page_pixmap(page2_num) if page2_num != page1_num else None
        
        if page1_pixmap:
            from utils.constants import Constants
            spacing = Constants.PAGE_SPACING.value
            width = page1_pixmap.width() + (page2_pixmap.width() if page2_pixmap else 0) + (spacing if page2_pixmap else 0)
            height = max(page1_pixmap.height(), page2_pixmap.height() if page2_pixmap else 0)
            
            combined_pixmap = QPixmap(width, height)
            bg_color = self.scroll_area.palette().color(self.scroll_area.backgroundRole())
            combined_pixmap.fill(bg_color)
            
            painter = QPainter(combined_pixmap)
            
            # 绘制第一页，垂直居中
            page1_y = (height - page1_pixmap.height()) // 2
            painter.drawPixmap(0, page1_y, page1_pixmap)
            
            # 绘制第二页，垂直居中
            if page2_pixmap:
                page2_y = (height - page2_pixmap.height()) // 2
                painter.drawPixmap(page1_pixmap.width() + spacing, page2_y, page2_pixmap)
            
            painter.end()
            
            return combined_pixmap
        return None
    
    def _calculate_scroll_position(self, target_y, viewport_height, item_height):
        """计算滚动位置"""
        if item_height <= viewport_height:
            scroll_position = target_y - (viewport_height // 2)
        else:
            scroll_position = target_y
        
        # 确保滚动位置在有效范围内
        scroll_position = max(scroll_position, 0)
        return scroll_position
    
    def _update_scroll_bar(self, v_scroll, scroll_position, target_y, item_height, viewport_height):
        """更新滚动条位置"""
        # 强制更新滚动条最大值
        v_scroll.update()
        
        # 再次确保滚动位置在有效范围内
        scroll_position = max(scroll_position, 0)
        max_scroll = v_scroll.maximum()
        if item_height > viewport_height:
            bottom_limit = target_y + item_height - viewport_height
            scroll_position = min(scroll_position, bottom_limit)
        
        # 设置滚动位置
        v_scroll.setValue(scroll_position)


class BaseContinuousViewtype(BrowsingViewtype, ABC):
    """连续浏览视图类型基础基类"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
        self.page_labels = {}  # 单页连续用
        self.spread_labels = {}  # 双页连续用（子类覆盖）
        self.pages_layout = None
        self._layout_owned = False  # 标记 layout 是否由本实例拥有
        self._render_completed_bound = None  # 保存信号连接引用
        self._connect_render_completed()
    
    def _connect_render_completed(self):
        """连接渲染完成事件 — 统一入口，子类覆盖实现具体逻辑"""
        # 子类在此方法中订阅 event_bus.render_completed
        pass
    
    def _disconnect_render_completed(self):
        """断开渲染完成事件 — 幂等操作，可安全重复调用"""
        if self._render_completed_bound is None:
            return
        try:
            event_bus.render_completed.disconnect(self._render_completed_bound)
        except (RuntimeError, TypeError):
            # 未连接或已断开，均视为成功
            pass
        finally:
            self._render_completed_bound = None
    
    def _safe_destroy_label(self, page_label):
        """安全销毁页面标签 — 所有异常路径全覆盖"""
        if page_label is None:
            return
        try:
            # 断开所有可能连接的信号（避免已删除对象的信号回调）
            for signal_name in ['pixmapChanged', 'destroyed']:
                try:
                    signal = getattr(page_label, signal_name, None)
                    if signal:
                        signal.disconnect()
                except (RuntimeError, TypeError, AttributeError):
                    pass
            # 从 pages_layout 移除
            if self.pages_layout is not None:
                try:
                    self.pages_layout.removeWidget(page_label)
                except (RuntimeError, TypeError):
                    pass
            page_label.deleteLater()
        except (RuntimeError, AttributeError):
            # 对象已销毁，无操作
            pass
    
    def _clear_layout_recursive(self, layout):
        """递归清理 layout 内的所有子部件"""
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                self._safe_destroy_label(item.widget())
            elif item.layout():
                self._clear_layout_recursive(item.layout())
    
    def activate(self):
        """激活连续浏览模式 — 单一入口，消除代码重复"""
        self._before_activate()
        self.activate_base()
        # 无条件清理，不依赖 is_active
        self.reset_display()
        
        self.center_layout = self._resolve_center_layout()
        if self.center_layout is None:
            logging.warning(f"{self.__class__.__name__} 激活失败：center_layout 为 None")
            return
        
        self.center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.pages_layout = self._build_pages_layout()
        if self.pages_layout is None:
            logging.warning(f"{self.__class__.__name__} 激活失败：pages_layout 创建失败")
            return
        
        try:
            if self.pages_layout.parent() is None:
                self.center_layout.addLayout(self.pages_layout)
                self._layout_owned = True
        except Exception as e:
            self.logger.error(f"添加 pages_layout 失败：{str(e)}")
            return
        
        self.is_active = True
        self.show_page(self.viewtype_service.get_current_page())
        self._after_activate()
    
    def _resolve_center_layout(self):
        """统一获取 center_layout"""
        if hasattr(self.pdf_viewer, 'content_area') and self.pdf_viewer.content_area:
            layout = self.pdf_viewer.content_area.get_center_layout()
            if layout is not None:
                return layout
        if self.scroll_area and self.scroll_area.widget():
            return self.scroll_area.widget().layout()
        return None
    
    def _build_pages_layout(self):
        """创建 pages_layout — 子类通过覆盖此方法定制间距"""
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Constants.PAGE_SPACING.value)
        return layout
    
    def reset_display(self):
        """无条件清理 — 移除 is_active 依赖，消除模式切换残留"""
        # 清理 page_labels
        for page_label in list(self.page_labels.values()):
            self._safe_destroy_label(page_label)
        self.page_labels.clear()
        
        # 清理 spread_labels
        for page_label in list(self.spread_labels.values()):
            self._safe_destroy_label(page_label)
        self.spread_labels.clear()
        
        # 清理 pages_layout（只清理自己拥有的）
        if self._layout_owned and self.pages_layout is not None:
            try:
                parent = self.pages_layout.parent()
                if parent is not None:
                    parent.removeItem(self.pages_layout)
                self._clear_layout_recursive(self.pages_layout)
            except (RuntimeError, AttributeError):
                pass
            self.pages_layout = None
            self._layout_owned = False
    
    def deactivate(self):
        """停用浏览模式 — 统一断开信号，消除事件泄漏"""
        self._before_deactivate()
        self._disconnect_render_completed()
        if hasattr(self.pdf_viewer, 'zoom_service'):
            self.pdf_viewer.zoom_service.remove_observer(self)
        self.is_active = False
        self.reset_display()
        self._after_deactivate()
    
    def _get_current_unit(self, page_num):
        """获取当前页码对应的单元索引"""
        raise NotImplementedError
    
    def _get_max_unit(self):
        """获取最大单元数"""
        raise NotImplementedError


class ContinuousViewtype(BaseContinuousViewtype, ABC):
    """连续浏览视图类型基类
    
    包含虚拟滚动 show_page 逻辑和子部件清理逻辑。
    注意：不覆盖 activate()，直接使用 BaseContinuousViewtype 的单一入口。
    """
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
    
    def show_page(self, page_num):
        """显示指定页码的页面 — 虚拟滚动"""
        if not self.is_active:
            return
            
        if page_num < 0 or page_num >= self.viewtype_service.get_total_pages():
            return
            
        self.current_page = page_num
        
        # 发布页面更新事件
        self._on_page_changed(page_num)
        
        # 计算当前单元索引和需要显示的单元范围
        current_unit = self._get_current_unit(page_num)
        start_unit, end_unit = self._calculate_display_range(current_unit)
        
        # 收集需要保留的页面标签
        needed_unit_nums = set(range(start_unit, end_unit + 1))
        needed_unit_nums.add(current_unit)
        
        # 移除不需要的页面标签
        if self.pages_layout is not None:
            self._cleanup_unneeded_widgets(needed_unit_nums)
        
        # 显示需要的单元
        self._display_needed_units(needed_unit_nums)
        
        # 滚动到当前单元
        self._scroll_to_unit(current_unit)
        
        # 强制布局更新
        self.update_config()
    
    @abstractmethod
    def _show_single_unit(self, unit_num):
        """显示单个单元（页面或双页）"""
        pass
    
    @abstractmethod
    def _scroll_to_unit(self, unit_num):
        """滚动到指定单元"""
        pass
    
    def _calculate_display_range(self, current_unit):
        """计算需要显示的单元范围"""
        start_unit = max(0, current_unit - 2)
        end_unit = min(self._get_max_unit() - 1, current_unit + 2)
        return start_unit, end_unit
    
    def _cleanup_unneeded_widgets(self, needed_unit_nums):
        """移除不需要的页面标签"""
        current_widgets = []
        widget_to_unit = {}
        
        # 构建 widget 到 unit 的映射
        if hasattr(self, 'page_labels'):
            for unit, widget in list(self.page_labels.items()):
                widget_to_unit[widget] = unit
        if hasattr(self, 'spread_labels'):
            for unit, widget in list(self.spread_labels.items()):
                widget_to_unit[widget] = unit
        
        # 收集所有 widget
        if self.pages_layout is not None:
            while self.pages_layout.count() > 0:
                item = self.pages_layout.takeAt(0)
                if item.widget() is not None:
                    current_widgets.append(item.widget())
        
        # 重新添加需要的 widget，删除不需要的
        for widget in current_widgets:
            unit_num = widget_to_unit.get(widget, -1)
            if unit_num in needed_unit_nums:
                if self.pages_layout is not None:
                    self.pages_layout.addWidget(widget)
            else:
                # 断开信号
                try:
                    if widget is not None:
                        widget.pixmapChanged.disconnect()
                except (RuntimeError, TypeError, Exception):
                    pass
                # 从字典移除
                if hasattr(self, 'page_labels') and unit_num in self.page_labels:
                    del self.page_labels[unit_num]
                if hasattr(self, 'spread_labels') and unit_num in self.spread_labels:
                    del self.spread_labels[unit_num]
                # 销毁
                try:
                    widget.deleteLater()
                except Exception:
                    pass
    
    def _display_needed_units(self, needed_unit_nums):
        """显示需要的单元"""
        for unit_num in needed_unit_nums:
            if not hasattr(self, 'page_labels') or unit_num not in self.page_labels:
                if hasattr(self, 'spread_labels') and f"spread_{unit_num}" in self.spread_labels:
                    continue
                self._show_single_unit(unit_num)
    
    def update_config(self):
        """更新配置"""
        # 调用基类的基础配置更新方法
        self.update_config_base()
        
        # 强制布局更新
        if self.pages_layout is not None:
            self.pages_layout.invalidate()
            self.pages_layout.activate()
        
        # 确保所有页面标签的几何信息更新
        if hasattr(self, 'page_labels'):
            for page_label in self.page_labels.values():
                if page_label is not None:
                    try:
                        page_label.updateGeometry()
                        page_label.adjustSize()
                    except Exception:
                        pass
        
        # 确保 scroll_area 的 widget 正确调整大小
        if self.scroll_area is not None and self.scroll_area.widget() is not None:
            self.scroll_area.widget().adjustSize()
            self.scroll_area.widget().updateGeometry()
            self.scroll_area.update()
        
        # 强制处理所有待处理事件，确保 UI 立即更新
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance():
            QApplication.processEvents()
            QApplication.processEvents()
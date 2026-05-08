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
    
    注意：状态存储在实例的 __dict__ 上（键名为 _throttle_{func_name}），
    保证不同实例之间互相独立，不存在共享状态问题。
    """
    # 从配置文件获取默认延迟时间
    if delay is None:
        ui_config = config_loader.get_ui_config()
        delay = ui_config.get("throttle_delay", 16)
    def decorator(func):
        _attr = f"_throttle_{func.__name__}"  # 每个函数使用独立的实例属性键
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 每个实例独立维护自己的节流状态，存储在实例的 __dict__ 中
            state = self.__dict__.setdefault(_attr, {"last_call_time": 0, "is_throttling": False})
            current_time = time.time() * 1000  # 转换为毫秒
            
            if current_time - state["last_call_time"] >= delay:
                # 超过延迟时间，立即执行
                func(self, *args, **kwargs)
                state["last_call_time"] = current_time
                state["is_throttling"] = False
            elif not state["is_throttling"]:
                # 在延迟时间内，且没有正在排队的延迟调用，使用QTimer延迟执行
                state["is_throttling"] = True
                
                from PyQt6.QtCore import QTimer, QCoreApplication
                
                def delayed_call():
                    new_time = time.time() * 1000
                    if state["is_throttling"] and new_time - state["last_call_time"] >= delay:
                        func(self, *args, **kwargs)
                        state["last_call_time"] = new_time
                        state["is_throttling"] = False
                
                # 使用QTimer确保在主线程中执行
                if QCoreApplication.instance():
                    QTimer.singleShot(delay, delayed_call)
        
        return wrapper
    
    return decorator

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
        # 布局与内容解耦：同步设置 minimumSize，让布局引擎在异步渲染前
        # 就知道 widget 的真实尺寸，消除高度从 0 突变的 TOCTOU 竞态
        if pixmap is not None:
            self.setMinimumSize(pixmap.size())
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
        self.logger = logging.getLogger(__name__)
        
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
        # 检查模式是否激活
        if not self.is_active:
            return
            
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
        
        # 重置显示状态
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
                logging.warning(f"{self.__class__.__name__}激活失败：center_layout为None")
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

from PyQt6.QtCore import QObject as _QObject

class _ViewportWheelFilter(_QObject):
    """
    安装在 scroll_area.viewport() 上的事件过滤器。
    
    拦截 Ctrl+Wheel，路由给连续视图类型的 _handle_zoom_wheel；
    其余事件一律透传，保留 QScrollArea 原始行为。
    """

    def __init__(self, viewtype):
        super().__init__()
        self._viewtype = viewtype

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent, Qt as _Qt
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() == _Qt.KeyboardModifier.ControlModifier:
                try:
                    self._viewtype._handle_zoom_wheel(event)
                except Exception as exc:
                    logging.warning(f"_ViewportWheelFilter: _handle_zoom_wheel 失败: {exc}")
                return True  # 拦截，不再向下传递
        return super().eventFilter(obj, event)


class BaseContinuousViewtype(BrowsingViewtype, ABC):
    """连续浏览视图类型基础基类"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
        self.page_labels = {}  # 存储页面标签
        self.pages_layout = None
        self._viewport_wheel_filter = None  # Ctrl+滚轮缩放的 viewport 事件过滤器
    
    def _install_viewport_wheel_filter(self):
        """在 scroll_area.viewport() 上安装 Ctrl+滚轮事件过滤器"""
        if self.scroll_area is None:
            return
        viewport = self.scroll_area.viewport()
        if viewport is None:
            return
        # 若已安装则先移除旧的
        self._remove_viewport_wheel_filter()
        self._viewport_wheel_filter = _ViewportWheelFilter(self)
        viewport.installEventFilter(self._viewport_wheel_filter)
        logging.debug(f"{self.__class__.__name__}：已安装 viewport Ctrl+滚轮过滤器")

    def _remove_viewport_wheel_filter(self):
        """移除 viewport 事件过滤器"""
        if self._viewport_wheel_filter is None:
            return
        if self.scroll_area is not None:
            viewport = self.scroll_area.viewport()
            if viewport is not None:
                try:
                    viewport.removeEventFilter(self._viewport_wheel_filter)
                except RuntimeError:
                    pass
        self._viewport_wheel_filter = None
        logging.debug(f"{self.__class__.__name__}：已移除 viewport Ctrl+滚轮过滤器")

    def activate(self):
        """激活连续浏览模式"""
        # 调用钩子方法
        self._before_activate()
        
        # 调用父类基础激活方法，初始化scroll_area相关组件
        self.activate_base()
        # 重置显示状态（此时is_active为False，不会删除布局和组件）
        self.reset_display()
        
        # 确保center_layout有效
        if self.center_layout is None:
            # 直接从ContentArea获取，不依赖scroll_area和center_container
            if hasattr(self.pdf_viewer, 'content_area') and self.pdf_viewer.content_area is not None:
                self.center_layout = self.pdf_viewer.content_area.get_center_layout()
                self.center_container = self.pdf_viewer.content_area.get_center_container()
            else:
                logging.warning(f"{self.__class__.__name__}激活失败：center_layout为None")
                return
                
        # 导入所有需要的类和常量，确保在使用前已定义
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QVBoxLayout
        
        self.center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 直接创建pages_layout，不依赖任何外部常量，确保它被正确初始化
        self.pages_layout = None
        try:
            self.pages_layout = QVBoxLayout()
            logging.debug(f"{self.__class__.__name__}：pages_layout创建成功，类型为{type(self.pages_layout)}")
            
            self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.pages_layout.setContentsMargins(0, 0, 0, 0)
            self.pages_layout.setSpacing(10)  # 使用默认间距10
            logging.debug(f"{self.__class__.__name__}：pages_layout属性设置完成")
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__}：pages_layout创建或初始化失败：{str(e)}")
            self.pages_layout = None
        
        # 确保pages_layout已经创建
        
        # 只使用is None检查，不依赖布尔值检查
        if self.pages_layout is None:
            return
        
        
        # 再次检查center_layout是否有效，防止在pages_layout创建过程中center_layout变为None
        
        # 只使用is None检查，不依赖布尔值检查
        if self.center_layout is None:
            return
        
        
        # 将布局添加到中心容器
        try:
            # 检查pages_layout.parent()是否为None，使用is None检查
            if self.pages_layout.parent() is None:
                self.center_layout.addLayout(self.pages_layout)
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__}：添加pages_layout到center_layout失败：{str(e)}")
            return
        
        # 设置模式为激活状态 - 移到最后，确保所有资源都已成功创建
        self.is_active = True
        
        # 安装 viewport Ctrl+滚轮过滤器，确保鼠标在页面间隙时也能缩放
        self._install_viewport_wheel_filter()
        
        # 显示当前页面
        self.show_page(self.pdf_viewer.current_page)
        
        # 调用钩子方法
        self._after_activate()
    
    def deactivate(self):
        """停用连续浏览模式"""
        # 移除 viewport Ctrl+滚轮过滤器
        self._remove_viewport_wheel_filter()
        # 调用父类 deactivate（取消缩放观察者、is_active=False、reset_display）
        super().deactivate()

    def reset_display(self):
        """重置显示状态"""
        # 检查模式是否激活，非激活状态不清理布局
        if not self.is_active:
            return
            
        # 清理页面标签
        for page_label in list(self.page_labels.values()):
            if page_label is not None:
                try:
                    if self.pages_layout is not None:
                        self.pages_layout.removeWidget(page_label)
                    # 断开所有信号连接
                    page_label.disconnect()
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
    
    def on_state_changed(self, state_name, old_value, new_value):
        """处理状态变化"""
        # 调用基类的on_state_changed方法处理通用逻辑
        super().on_state_changed(state_name, old_value, new_value)

        try:
            # 只处理缩放级别变化时的页面更新
            if state_name == "zoom_level":
                # 更新所有页面的显示
                for page_num, page_label in self.page_labels.items():
                    if page_label.isVisible():
                        pixmap = self.pdf_viewer._get_page_pixmap(page_num)
                        if pixmap is not None:
                            page_label.setPixmap(pixmap)
                        else:
                            # 保底：pixmap 为 None 时用 get_page_size 预测新尺寸，
                            # 防止缩小时旧的 minimumSize 残留导致 widget 无法收缩
                            try:
                                predicted = self.viewtype_service.get_page_size(
                                    page_num, new_value)
                                if predicted and predicted[0] > 0 and predicted[1] > 0:
                                    page_label.setMinimumSize(predicted[0], predicted[1])
                            except Exception:
                                pass
        except Exception as e:
            self._handle_exception(f"处理状态变化失败: {str(e)}")
            # 尝试回滚到之前的状态
            self._rollback_state(state_name, old_value)
    
    @abstractmethod
    def _show_single_unit(self, unit_num):
        """显示单个单元（页面或双页）"""
        pass
    
    @abstractmethod
    def _scroll_to_unit(self, unit_num):
        """滚动到指定单元"""
        pass
    
    @abstractmethod
    def _get_current_unit(self, page_num):
        """获取当前页码对应的单元索引"""
        pass
    
    @abstractmethod
    def _get_max_unit(self):
        """获取最大单元数"""
        pass

class ContinuousViewtype(BaseContinuousViewtype, ABC):
    """连续浏览视图类型基类"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
        self._programmatic_scroll = False  # 标记程序主动滚动，阻断 valueChanged 触发的页面计算
        
    def activate(self):
        """激活连续视图类型"""
        # 调用父类基础激活方法，初始化scroll_area相关组件
        self.activate_base()
        # 重置显示状态（此时is_active为False，不会删除布局和组件）
        self.reset_display()
        
        # 确保center_layout有效
        if self.center_layout is None:
            # 直接从ContentArea获取，不依赖scroll_area和center_container
            if hasattr(self.pdf_viewer, 'content_area') and self.pdf_viewer.content_area is not None:
                self.center_layout = self.pdf_viewer.content_area.get_center_layout()
                self.center_container = self.pdf_viewer.content_area.get_center_container()
            else:
                logging.warning(f"{self.__class__.__name__}激活失败：center_layout为None")
                return
                
        # 导入所有需要的类和常量，确保在使用前已定义
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QVBoxLayout
        
        self.center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 直接创建pages_layout，不依赖任何外部常量，确保它被正确初始化
        self.pages_layout = None
        try:
            self.pages_layout = QVBoxLayout()
            logging.debug(f"{self.__class__.__name__}：pages_layout创建成功，类型为{type(self.pages_layout)}")
            
            self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.pages_layout.setContentsMargins(0, 0, 0, 0)
            self.pages_layout.setSpacing(10)  # 使用默认间距10
            logging.debug(f"{self.__class__.__name__}：pages_layout属性设置完成")
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__}：pages_layout创建或初始化失败：{str(e)}")
            self.pages_layout = None
        
        # 确保pages_layout已经创建
        logging.debug(f"{self.__class__.__name__}：检查pages_layout是否为None，值为：{self.pages_layout}")
        
        # 只使用is None检查，不依赖布尔值检查
        if self.pages_layout is None:
            logging.warning(f"{self.__class__.__name__}激活失败：pages_layout创建失败")
            return
        
        logging.debug(f"{self.__class__.__name__}：pages_layout检查通过，继续执行")
        
        # 再次检查center_layout是否有效，防止在pages_layout创建过程中center_layout变为None
        logging.debug(f"{self.__class__.__name__}：检查center_layout是否为None，值为：{self.center_layout}")
        
        # 只使用is None检查，不依赖布尔值检查
        if self.center_layout is None:
            logging.warning(f"{self.__class__.__name__}激活失败：center_layout变为None")
            return
        
        logging.debug(f"{self.__class__.__name__}：center_layout检查通过，继续执行")
        
        # 将布局添加到中心容器
        try:
            # 检查pages_layout.parent()是否为None，使用is None检查
            if self.pages_layout.parent() is None:
                self.center_layout.addLayout(self.pages_layout)
            logging.debug(f"{self.__class__.__name__}：pages_layout添加到center_layout成功")
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__}：添加pages_layout到center_layout失败：{str(e)}")
            return
        
        logging.debug(f"{self.__class__.__name__}：布局添加成功，继续执行")
        
        # 设置模式为激活状态 - 移到最后，确保所有资源都已成功创建
        self.is_active = True
        logging.debug(f"{self.__class__.__name__}：is_active设置为True")
        
        # 安装 viewport Ctrl+滚轮过滤器
        self._install_viewport_wheel_filter()
        
        # 显示当前页面
        self.show_page(self.pdf_viewer.current_page)
        logging.debug(f"{self.__class__.__name__}：激活成功，已显示当前页面")
    
    def _create_layout(self):
        """创建布局，子类可以重写"""
        from utils.constants import Constants
        from PyQt6.QtWidgets import QVBoxLayout
        from PyQt6.QtCore import Qt
        if self.pages_layout is None:
            self.pages_layout = QVBoxLayout()
            self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.pages_layout.setContentsMargins(0, 0, 0, 0)
            self.pages_layout.setSpacing(Constants.PAGE_SPACING.value)
    
    @abstractmethod
    def _show_single_unit(self, unit_num):
        """显示单个单元（页面或双页）"""
        pass
    
    @abstractmethod
    def _scroll_to_unit(self, unit_num):
        """滚动到指定单元"""
        pass
    
    def show_page(self, page_num):
        """显示指定页码的页面"""
        if not self.is_active:
            return

        logging.debug(f"[show_page] page_num={page_num}, current_page_before={self.current_page}")
        if page_num < 0 or page_num >= self.viewtype_service.get_total_pages():
            return
        
        # 设置程序滚动锁，防止 _scroll_to_unit 触发的 valueChanged
        # 被 ThumbnailSync 错误地解释为用户翻页
        self._programmatic_scroll = True
            
        self.current_page = page_num
        
        # 发布页面更新事件
        self._on_page_changed(page_num)
        
        # 计算当前单元索引和需要显示的单元范围
        current_unit = self._get_current_unit(page_num)
        start_unit, end_unit = self._calculate_display_range(current_unit)
        
        # 收集需要保留的页面标签
        needed_unit_nums = set(range(start_unit, end_unit + 1))
        
        # 确保当前单元在需要显示的范围内
        needed_unit_nums.add(current_unit)
        
        # 移除不需要的页面标签
        if self.pages_layout is not None:
            self._cleanup_unneeded_widgets(needed_unit_nums)
        
        # 显示需要的单元（按升序创建新 widget，追加到布局）
        self._display_needed_units(needed_unit_nums)
        
        # 全局重排：确保 pages_layout 中所有 widget 按页码升序排列
        # 这一步处理「向前翻页时新建 widget 追加到末尾导致乱序」的情况
        if self.pages_layout is not None:
            self._reorder_layout_widgets()
        
        # 滚动到当前单元（仅在页面标签存在时）
        # 注意：_display_needed_units 中的异步渲染可能尚未完成
        # 所以 _scroll_to_unit 需要检查页面标签是否存在
        self._scroll_to_unit(current_unit)
        
        # 强制布局更新
        self.update_config()
        
        # 延迟释放程序滚动锁，让布局事件和 QTimer.singleShot(0) 排队的操作完成
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(300, self._release_programmatic_scroll)
    
    def _calculate_display_range(self, current_unit):
        """计算需要显示的单元范围"""
        # 计算需要显示的单元范围，增加显示数量，确保滚动时的连续性
        start_unit = max(0, current_unit - 2)
        end_unit = min(self._get_max_unit() - 1, current_unit + 2)
        return start_unit, end_unit
    
    def _cleanup_unneeded_widgets(self, needed_unit_nums):
        """移除不需要的页面标签"""
        # 收集所有当前的widget及其对应的unit_num
        current_widgets = []
        widget_to_unit = {}
        
        # 先构建widget到unit的映射（unit_num 统一使用整数）
        if hasattr(self, 'page_labels'):
            for unit, widget in list(self.page_labels.items()):
                widget_to_unit[widget] = unit  # page_labels key 是整数
        if hasattr(self, 'spread_labels'):
            for spread_key, widget in list(self.spread_labels.items()):
                # spread_labels key 是字符串 "spread_N"，提取整数 N
                try:
                    unit_num = int(spread_key.split('_')[1])
                except (ValueError, IndexError):
                    unit_num = -1
                widget_to_unit[widget] = unit_num
        
        # 收集所有widget
        if self.pages_layout is not None:
            while self.pages_layout.count() > 0:
                item = self.pages_layout.takeAt(0)
                if item.widget() is not None:
                    current_widgets.append(item.widget())
        
        # 重新添加需要的widget，删除不需要的widget
        # 按页码升序排列，确保布局中 widget 顺序与实际页码一致
        # 避免异步渲染完成时间不同导致的布局乱序 → 滚动位置偏移 → 跳页问题
        for widget in sorted(current_widgets, key=lambda w: widget_to_unit.get(w, -1)):
            unit_num = widget_to_unit.get(widget, -1)
            if unit_num in needed_unit_nums:
                # 保留需要的widget，重新添加到布局
                if self.pages_layout is not None:
                    self.pages_layout.addWidget(widget)
            else:
                # 删除不需要的widget
                # 首先断开信号连接（在widget被销毁前）
                try:
                    # 检查widget是否仍然有效且信号已连接
                    if widget is not None:
                        try:
                            # 尝试断开 pixmapChanged 信号
                            widget.pixmapChanged.disconnect()
                        except (RuntimeError, TypeError):
                            # widget已被销毁或信号未连接，忽略
                            pass
                        except Exception:
                            # 忽略其他异常
                            pass
                except Exception:
                    # 忽略已删除或无效的widget
                    pass
                
                # 从字典中移除（在调用deleteLater之前）
                if hasattr(self, 'page_labels') and unit_num in self.page_labels:
                    del self.page_labels[unit_num]
                if hasattr(self, 'spread_labels'):
                    # spread_labels 用字符串 key，需要转回
                    spread_key = f"spread_{unit_num}"
                    if spread_key in self.spread_labels:
                        del self.spread_labels[spread_key]
                
                # 最后调用deleteLater
                try:
                    widget.deleteLater()
                except Exception:
                    # 忽略已删除或无效的widget
                    pass
    
    def _reorder_layout_widgets(self):
        """重排 pages_layout 中所有 widget，确保按单元编号升序排列

        _cleanup_unneeded_widgets 保证了「已有 widget」的顺序正确，
        但 _display_needed_units 新建的 widget 总是追加到末尾。
        向前翻页时，新建的小页码 widget 会排在已有大页码 widget 之后。
        本方法通过「取出所有 → 按序重新添加」来修正这个问题。
        """
        if self.pages_layout is None:
            return

        # 构建 widget → unit_num 的映射
        widget_to_unit = {}
        if hasattr(self, 'page_labels'):
            for unit, widget in self.page_labels.items():
                widget_to_unit[widget] = unit
        if hasattr(self, 'spread_labels'):
            for unit_key, widget in self.spread_labels.items():
                # spread_labels 的 key 是字符串如 "spread_0"
                try:
                    unit_num = int(unit_key.split('_')[1])
                except (ValueError, IndexError):
                    unit_num = -1
                widget_to_unit[widget] = unit_num

        # 取出布局中的所有 widget
        all_widgets = []
        while self.pages_layout.count() > 0:
            item = self.pages_layout.takeAt(0)
            if item.widget() is not None:
                all_widgets.append(item.widget())

        logging.warning(f"[_reorder_layout_widgets] before reorder: page_labels={list(self.page_labels.keys()) if hasattr(self, 'page_labels') else []}, widget order by page_labels={[(widget_to_unit.get(w, -1), id(w)) for w in all_widgets]}")

        # 按 unit_num 升序重新添加
        sorted_widgets = sorted(all_widgets, key=lambda w: widget_to_unit.get(w, -1))
        for widget in sorted_widgets:
            self.pages_layout.addWidget(widget)

        logging.warning(f"[_reorder_layout_widgets] after reorder: layout_count={self.pages_layout.count()}, order by unit={[widget_to_unit.get(self.pages_layout.itemAt(i).widget(), -1) for i in range(self.pages_layout.count())]}")
    
    def _release_programmatic_scroll(self):
        """释放程序滚动锁"""
        self._programmatic_scroll = False
    
    def _display_needed_units(self, needed_unit_nums):
        """显示需要的单元
        
        按单元编号升序遍历，确保新建 widget 以正确的页码顺序追加到 pages_layout，
        避免乱序追加导致滚动位置计算错误（翻页回跳问题的根因之一）。
        
        注意：_show_single_unit 内部有去重保护，重复调用不会重建已存在的 widget。
        """
        # 判断是双页连续模式还是单页连续模式
        # TwoPageContinuousViewtype 独有 spread_labels，单页连续模式无此属性
        use_spread = hasattr(self, 'spread_labels')
        
        for unit_num in sorted(needed_unit_nums):
            # 检查单元是否已存在，避免重复创建
            if use_spread:
                spread_key = f"spread_{unit_num}"
                already_exists = spread_key in self.spread_labels
            else:
                already_exists = unit_num in self.page_labels
            
            if not already_exists:
                self._show_single_unit(unit_num)
    
    @abstractmethod
    def _get_current_unit(self, page_num):
        """获取当前页码对应的单元索引"""
        pass
    
    @abstractmethod
    def _get_max_unit(self):
        """获取最大单元数"""
        pass
        
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
                        # 忽略已删除或无效的页面标签
                        pass
        
        # 确保scroll_area的widget正确调整大小
        if self.scroll_area is not None and self.scroll_area.widget() is not None:
            self.scroll_area.widget().updateGeometry()
            
            # 强制scroll_area更新
            self.scroll_area.update()
        

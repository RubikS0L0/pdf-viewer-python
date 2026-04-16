"""
事件总线模块

实现发布-订阅模式，用于解耦组件间的直接依赖。
替代原有的直接回调方式，实现更松散的架构。

使用示例:
    # 订阅事件
    event_bus.subscribe(EventType.ZOOM_CHANGED, on_zoom_changed)
    
    # 发布事件
    event_bus.publish(EventType.ZOOM_CHANGED, zoom_level=1.5)
    
    # 取消订阅
    event_bus.unsubscribe(EventType.ZOOM_CHANGED, on_zoom_changed)
"""

import logging
import threading
from enum import Enum, auto
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict


class EventType(Enum):
    """事件类型枚举"""
    # 缩放相关
    ZOOM_CHANGED = auto()
    ZOOM_MODE_CHANGED = auto()
    
    # 页面相关
    PAGE_CHANGED = auto()
    PAGE_RENDERED = auto()
    PAGE_CACHE_CLEARED = auto()
    
    # 文档相关
    DOCUMENT_OPENED = auto()
    DOCUMENT_CLOSED = auto()
    DOCUMENT_LOADING = auto()
    
    # 视图相关
    VIEWTYPE_CHANGED = auto()
    VIEWPORT_RESIZED = auto()
    
    # 选择相关
    SELECTION_STARTED = auto()
    SELECTION_CHANGED = auto()
    SELECTION_ENDED = auto()
    
    # 检测相关
    DETECTION_STARTED = auto()
    DETECTION_COMPLETED = auto()
    DETECTION_RESULTS_UPDATED = auto()
    
    # 配置相关
    CONFIG_CHANGED = auto()
    
    # 应用生命周期
    APP_STARTING = auto()
    APP_READY = auto()
    APP_CLOSING = auto()


class Event:
    """事件对象"""
    
    def __init__(self, event_type: EventType, source: Any = None, **kwargs):
        """
        初始化事件
        
        参数:
            event_type: 事件类型
            source: 事件源对象
            **kwargs: 事件数据
        """
        self.type = event_type
        self.source = source
        self.data = kwargs
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取事件数据"""
        return self.data.get(key, default)
    
    def __repr__(self):
        return f"Event(type={self.type.name}, source={self.source}, data={self.data})"


class EventBus:
    """
    事件总线
    
    实现线程安全的发布-订阅模式。
    支持同步和异步事件处理。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self.logger = logging.getLogger(__name__)
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._subscribers_lock = threading.RLock()
        self._event_history: List[Event] = []
        self._max_history = 100
        self._initialized = True
    
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """
        订阅事件
        
        参数:
            event_type: 事件类型
            handler: 事件处理函数，接收 Event 对象作为参数
        """
        with self._subscribers_lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                self.logger.debug(f"订阅事件: {event_type.name}, 当前订阅数: {len(self._subscribers[event_type])}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """
        取消订阅事件
        
        参数:
            event_type: 事件类型
            handler: 事件处理函数
        """
        with self._subscribers_lock:
            if event_type in self._subscribers:
                if handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)
                    self.logger.debug(f"取消订阅事件: {event_type.name}")
    
    def publish(self, event_type: EventType, source: Any = None, **kwargs) -> None:
        """
        发布事件（同步）
        
        参数:
            event_type: 事件类型
            source: 事件源对象
            **kwargs: 事件数据
        """
        event = Event(event_type, source, **kwargs)
        self._record_history(event)
        
        with self._subscribers_lock:
            handlers = self._subscribers[event_type].copy()
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"事件处理失败 {event_type.name}: {e}", exc_info=True)
    
    def publish_async(self, event_type: EventType, source: Any = None, **kwargs) -> None:
        """
        发布事件（异步）
        
        在后台线程中处理事件
        
        参数:
            event_type: 事件类型
            source: 事件源对象
            **kwargs: 事件数据
        """
        import threading
        
        def _publish():
            self.publish(event_type, source, **kwargs)
        
        thread = threading.Thread(target=_publish, daemon=True)
        thread.start()
    
    def _record_history(self, event: Event) -> None:
        """记录事件历史"""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
    
    def get_history(self, event_type: Optional[EventType] = None, count: int = 10) -> List[Event]:
        """
        获取事件历史
        
        参数:
            event_type: 事件类型过滤，None表示不过滤
            count: 返回的最大数量
            
        返回:
            事件列表
        """
        if event_type is None:
            return self._event_history[-count:]
        
        filtered = [e for e in self._event_history if e.type == event_type]
        return filtered[-count:]
    
    def clear_history(self) -> None:
        """清空事件历史"""
        self._event_history.clear()
    
    def get_subscriber_count(self, event_type: Optional[EventType] = None) -> int:
        """
        获取订阅者数量
        
        参数:
            event_type: 事件类型，None表示获取所有
            
        返回:
            订阅者数量
        """
        with self._subscribers_lock:
            if event_type is not None:
                return len(self._subscribers.get(event_type, []))
            return sum(len(handlers) for handlers in self._subscribers.values())
    
    def clear_subscribers(self, event_type: Optional[EventType] = None) -> None:
        """
        清除订阅者
        
        参数:
            event_type: 事件类型，None表示清除所有
        """
        with self._subscribers_lock:
            if event_type is not None:
                self._subscribers[event_type].clear()
            else:
                self._subscribers.clear()


# 全局事件总线实例
event_bus = EventBus()

# 导出 EventType 作为 EventTypes（保持向后兼容）
EventTypes = EventType


# 装饰器形式的订阅
def on_event(event_type: EventType):
    """
    事件订阅装饰器
    
    使用示例:
        @on_event(EventType.ZOOM_CHANGED)
        def handle_zoom_change(event):
            print(f"Zoom changed to: {event.get('zoom_level')}")
    """
    def decorator(func: Callable[[Event], None]):
        event_bus.subscribe(event_type, func)
        return func
    return decorator

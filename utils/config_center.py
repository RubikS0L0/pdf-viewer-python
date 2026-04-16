"""
统一配置中心

集中管理所有配置，支持：
- 从多个来源加载配置（代码默认值、YAML文件、环境变量）
- 配置项的层级覆盖
- 类型安全的配置访问
- 配置变更通知

替代原有的分散配置：
- utils/constants.py (Constants 枚举)
- utils/config_loader.py (YAML配置)
- 各模块的 _DEFAULT_* 常量
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class CacheConfig:
    """缓存配置"""
    base_max_size_testing: int = 5
    memory_warning_threshold: float = 80.0
    memory_critical_threshold: float = 90.0
    disk_warning_threshold_gb: float = 1.0
    disk_critical_threshold_gb: float = 0.5
    cleanup_interval_ms: int = 60000
    default_cache_dir: str = ".pdf_viewer_cache"


@dataclass
class UIConfig:
    """UI配置"""
    throttle_delay_ms: int = 16
    scroll_step: int = 20
    scroll_boundary_threshold: int = 10
    page_spacing: int = 20
    selection_box_color: tuple = (0, 120, 215)
    selection_box_width: int = 2
    selection_box_style: int = 1  # Qt.SolidLine
    detection_box_color: tuple = (255, 0, 0)
    detection_box_width: int = 2
    detection_label_font_size: int = 10
    detection_label_color: tuple = (255, 255, 255)
    detection_label_background: tuple = (255, 0, 0)


@dataclass
class ZoomConfig:
    """缩放配置"""
    min_zoom: float = 0.1
    max_zoom: float = 5.0
    zoom_delta: float = 1.05
    default_zoom: float = 1.0


@dataclass
class ThreadPoolConfig:
    """线程池配置"""
    render_max_workers: int = 2
    preload_max_workers: int = 2
    detection_max_workers: int = 3
    thumbnail_max_workers: int = 2


@dataclass
class RenderingConfig:
    """渲染配置"""
    default_dpi: int = 72
    progressive_render_delay_ms: int = 100
    progressive_render_interval_ms: int = 50


class ConfigCenter:
    """
    统一配置中心
    
    单例模式，集中管理所有配置项。
    配置优先级：环境变量 > YAML文件 > 代码默认值
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ConfigCenter._initialized:
            return
            
        self.logger = logging.getLogger(__name__)
        self._config_file = Path("config/app_config.yaml")
        self._observers: Dict[str, list] = {}
        
        # 初始化各模块配置
        self._cache = CacheConfig()
        self._ui = UIConfig()
        self._zoom = ZoomConfig()
        self._thread_pool = ThreadPoolConfig()
        self._rendering = RenderingConfig()
        
        # 加载配置
        self._load_from_file()
        self._load_from_env()
        
        ConfigCenter._initialized = True
        self.logger.info("配置中心初始化完成")
    
    def _load_from_file(self):
        """从YAML文件加载配置"""
        if not self._config_file.exists():
            self.logger.debug(f"配置文件不存在: {self._config_file}")
            return
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                return
            
            # 更新缓存配置
            if 'cache' in config_data:
                self._update_dataclass_from_dict(self._cache, config_data['cache'])
            
            # 更新UI配置
            if 'ui' in config_data:
                self._update_dataclass_from_dict(self._ui, config_data['ui'])
            
            # 更新缩放配置
            if 'zoom' in config_data:
                self._update_dataclass_from_dict(self._zoom, config_data['zoom'])
            
            # 更新线程池配置
            if 'thread_pool' in config_data:
                self._update_dataclass_from_dict(self._thread_pool, config_data['thread_pool'])
            
            # 更新渲染配置
            if 'rendering' in config_data:
                self._update_dataclass_from_dict(self._rendering, config_data['rendering'])
            
            self.logger.info(f"已从文件加载配置: {self._config_file}")
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        env_mappings = {
            # 缓存配置
            'PDFVIEW_CACHE_MAX_SIZE': ('cache', 'base_max_size_testing', int),
            'PDFVIEW_CACHE_MEMORY_WARNING': ('cache', 'memory_warning_threshold', float),
            'PDFVIEW_CACHE_DIR': ('cache', 'default_cache_dir', str),
            
            # UI配置
            'PDFVIEW_UI_THROTTLE_DELAY': ('ui', 'throttle_delay_ms', int),
            'PDFVIEW_UI_SCROLL_STEP': ('ui', 'scroll_step', int),
            
            # 缩放配置
            'PDFVIEW_ZOOM_MIN': ('zoom', 'min_zoom', float),
            'PDFVIEW_ZOOM_MAX': ('zoom', 'max_zoom', float),
            'PDFVIEW_ZOOM_DELTA': ('zoom', 'zoom_delta', float),
            
            # 线程池配置
            'PDFVIEW_THREAD_RENDER': ('thread_pool', 'render_max_workers', int),
            'PDFVIEW_THREAD_PRELOAD': ('thread_pool', 'preload_max_workers', int),
        }
        
        for env_var, (section, key, type_func) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    typed_value = type_func(value)
                    config_obj = getattr(self, f'_{section}')
                    old_value = getattr(config_obj, key)
                    setattr(config_obj, key, typed_value)
                    self.logger.debug(f"从环境变量加载: {env_var}={typed_value}")
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"环境变量 {env_var} 值无效: {value}")
    
    def _update_dataclass_from_dict(self, dataclass_obj: Any, updates: Dict):
        """从字典更新 dataclass 对象"""
        for key, value in updates.items():
            if hasattr(dataclass_obj, key):
                setattr(dataclass_obj, key, value)
    
    @property
    def cache(self) -> CacheConfig:
        """获取缓存配置"""
        return self._cache
    
    @property
    def ui(self) -> UIConfig:
        """获取UI配置"""
        return self._ui
    
    @property
    def zoom(self) -> ZoomConfig:
        """获取缩放配置"""
        return self._zoom
    
    @property
    def thread_pool(self) -> ThreadPoolConfig:
        """获取线程池配置"""
        return self._thread_pool
    
    @property
    def rendering(self) -> RenderingConfig:
        """获取渲染配置"""
        return self._rendering
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        通用配置获取方法
        
        参数:
            section: 配置节名称 (cache, ui, zoom, thread_pool, rendering)
            key: 配置项名称
            default: 默认值
            
        返回:
            配置值，如果不存在则返回默认值
        """
        config_obj = getattr(self, f'_{section}', None)
        if config_obj is None:
            return default
        return getattr(config_obj, key, default)
    
    def set(self, section: str, key: str, value: Any, notify: bool = True):
        """
        设置配置值
        
        参数:
            section: 配置节名称
            key: 配置项名称
            value: 新值
            notify: 是否通知观察者
        """
        config_obj = getattr(self, f'_{section}', None)
        if config_obj is None:
            self.logger.warning(f"配置节不存在: {section}")
            return
        
        if not hasattr(config_obj, key):
            self.logger.warning(f"配置项不存在: {section}.{key}")
            return
        
        old_value = getattr(config_obj, key)
        setattr(config_obj, key, value)
        
        if notify and old_value != value:
            self._notify_observers(f"{section}.{key}", old_value, value)
    
    def subscribe(self, config_key: str, callback: Callable):
        """
        订阅配置变更
        
        参数:
            config_key: 配置项键名 (如 "cache.base_max_size_testing")
            callback: 回调函数 (old_value, new_value) -> None
        """
        if config_key not in self._observers:
            self._observers[config_key] = []
        self._observers[config_key].append(callback)
    
    def unsubscribe(self, config_key: str, callback: Callable):
        """取消订阅配置变更"""
        if config_key in self._observers:
            if callback in self._observers[config_key]:
                self._observers[config_key].remove(callback)
    
    def _notify_observers(self, config_key: str, old_value: Any, new_value: Any):
        """通知配置变更观察者"""
        # 通知特定配置项的观察者
        if config_key in self._observers:
            for callback in self._observers[config_key]:
                try:
                    callback(old_value, new_value)
                except Exception as e:
                    self.logger.error(f"配置变更通知失败: {e}")
        
        # 通知通配符观察者
        if '*' in self._observers:
            for callback in self._observers['*']:
                try:
                    callback(config_key, old_value, new_value)
                except Exception as e:
                    self.logger.error(f"配置变更通知失败: {e}")
    
    def save_to_file(self, file_path: Optional[str] = None):
        """
        保存配置到文件
        
        参数:
            file_path: 文件路径，默认使用初始化时的路径
        """
        path = Path(file_path) if file_path else self._config_file
        
        config_data = {
            'cache': self._dataclass_to_dict(self._cache),
            'ui': self._dataclass_to_dict(self._ui),
            'zoom': self._dataclass_to_dict(self._zoom),
            'thread_pool': self._dataclass_to_dict(self._thread_pool),
            'rendering': self._dataclass_to_dict(self._rendering),
        }
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            self.logger.info(f"配置已保存到: {path}")
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
    
    def _dataclass_to_dict(self, dataclass_obj: Any) -> Dict:
        """将 dataclass 转换为字典"""
        result = {}
        for key in dataclass_obj.__dataclass_fields__:
            value = getattr(dataclass_obj, key)
            # 处理 tuple 类型（YAML 不直接支持）
            if isinstance(value, tuple):
                value = list(value)
            result[key] = value
        return result
    
    def reset_to_defaults(self):
        """重置所有配置为默认值"""
        self._cache = CacheConfig()
        self._ui = UIConfig()
        self._zoom = ZoomConfig()
        self._thread_pool = ThreadPoolConfig()
        self._rendering = RenderingConfig()
        self.logger.info("配置已重置为默认值")


# 全局配置中心实例
config_center = ConfigCenter()

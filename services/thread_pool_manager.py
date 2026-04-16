"""全局线程池管理器

负责统一管理所有线程池资源，包括：
- 渲染线程池
- 预加载线程池
- 图形检测线程池
- 缩略图生成线程池

确保线程池的合理使用和生命周期管理。
"""

from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import logging
import time
import threading
from typing import Dict, Optional


class ThreadPoolManager:
    """全局线程池管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ThreadPoolManager, cls).__new__(cls)
                cls._instance._init_thread_pools()
            return cls._instance
    
    def _init_thread_pools(self):
        """初始化线程池"""
        self.logger = logging.getLogger(__name__)
        self._cpu_count = multiprocessing.cpu_count()
        self._lock = threading.Lock()
        
        # 线程池配置
        self._thread_pools = {
            'render': {
                'executor': None,
                'max_workers': min(2, self._cpu_count // 2),
                'name': '渲染线程池'
            },
            'preload': {
                'executor': None,
                'max_workers': min(2, self._cpu_count // 3),
                'name': '预加载线程池'
            },
            'detection': {
                'executor': None,
                'max_workers': min(3, self._cpu_count // 2),
                'name': '图形检测线程池'
            },
            'thumbnail': {
                'executor': None,
                'max_workers': min(2, self._cpu_count // 4),
                'name': '缩略图生成线程池'
            }
        }
        
        # 初始化所有线程池
        for pool_name, pool_config in self._thread_pools.items():
            pool_config['executor'] = ThreadPoolExecutor(
                max_workers=pool_config['max_workers'],
                thread_name_prefix=f'{pool_name}_thread_'
            )
            self.logger.info(f"{pool_config['name']}初始化完成，最大工作线程数：{pool_config['max_workers']}")
        
        # 线程池状态
        self._running = True
        self._shutdown_started = False
        self._shutdown_completed = False
    
    def get_render_executor(self):
        """获取渲染线程池"""
        return self._thread_pools['render']['executor']
    
    def get_preload_executor(self):
        """获取预加载线程池"""
        return self._thread_pools['preload']['executor']
    
    def get_detection_executor(self):
        """获取图形检测线程池"""
        return self._thread_pools['detection']['executor']
    
    def get_thumbnail_executor(self):
        """获取缩略图生成线程池"""
        return self._thread_pools['thumbnail']['executor']
    
    def get_pool_status(self) -> Dict[str, Dict[str, any]]:
        """获取线程池状态"""
        status = {}
        for pool_name, pool_config in self._thread_pools.items():
            status[pool_name] = {
                'name': pool_config['name'],
                'max_workers': pool_config['max_workers'],
                'running': self._running
            }
        return status
    
    def shutdown(self, wait: bool = True, timeout: Optional[float] = 5.0):
        """关闭所有线程池
        
        参数：
        - wait: 是否等待任务完成
        - timeout: 等待超时时间（秒）
        """
        with self._lock:
            if not self._running or self._shutdown_completed:
                self.logger.info("线程池已经关闭")
                return
            
            if self._shutdown_started:
                self.logger.info("线程池正在关闭中")
                return
            
            self._shutdown_started = True
            self.logger.info("开始关闭线程池...")
        
        try:
            # 关闭所有线程池
            for pool_name, pool_config in self._thread_pools.items():
                executor = pool_config['executor']
                if executor:
                    try:
                        self.logger.info(f"关闭{pool_config['name']}，等待任务完成：{wait}")
                        if wait:
                            # 先尝试优雅关闭
                            executor.shutdown(wait=False)
                            # 给任务一些时间完成
                            if timeout > 0:
                                time.sleep(min(timeout, 1.0))
                        else:
                            executor.shutdown(wait=False)
                        self.logger.info(f"{pool_config['name']}已关闭")
                    except Exception as e:
                        self.logger.error(f"关闭{pool_config['name']}时出错：{str(e)}")
            
            # 更新状态
            with self._lock:
                self._running = False
                self._shutdown_completed = True
            
            self.logger.info("所有线程池已成功关闭")
            
        except Exception as e:
            self.logger.error(f"关闭线程池时发生严重错误：{str(e)}")
            # 确保状态更新
            with self._lock:
                self._running = False
                self._shutdown_completed = True
    
    def is_running(self) -> bool:
        """检查线程池是否正在运行"""
        with self._lock:
            return self._running
    
    def __del__(self):
        """析构函数"""
        # 析构函数中只做简单的关闭，避免复杂操作
        if hasattr(self, '_running') and self._running:
            try:
                self.shutdown(wait=False, timeout=0)
            except Exception:
                pass


# 全局线程池管理器实例
thread_pool_manager = ThreadPoolManager()

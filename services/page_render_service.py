#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
页面渲染服务

负责管理页面渲染任务，协调PageRenderer和PageCache组件，
处理异步渲染，优化渲染性能，并与事件总线集成。
"""

import logging
import threading
from queue import PriorityQueue, Empty
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Tuple, Callable, Any
from PyQt6.QtCore import QMutex
from PyQt6.QtGui import QPainter
from services.event_bus import event_bus
from utils.constants import Constants


class RenderTask:
    """渲染任务类"""
    def __init__(self, page_num: int, zoom_level: float, priority: int = 0):
        """初始化渲染任务
        
        参数：
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        - priority: int, 优先级，数字越小优先级越高
        """
        self.page_num = page_num
        self.zoom_level = zoom_level
        self.priority = priority
        self.id = id(self)
    
    def __lt__(self, other):
        """比较优先级"""
        return self.priority < other.priority


class PageRenderService:
    """页面渲染服务类"""
    
    def __init__(self, page_renderer, page_cache, max_workers: int = 4):
        """初始化页面渲染服务
        
        参数：
        - page_renderer: PageRenderer, 页面渲染器实例
        - page_cache: PageCache, 页面缓存实例
        - max_workers: int, 最大工作线程数
        """
        self.logger = logging.getLogger(__name__)
        
        self._page_renderer = page_renderer
        self._page_cache = page_cache
        
        # 渲染任务队列
        self._render_queue = PriorityQueue()
        
        # 动态计算线程池大小，基于系统CPU核心数
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        optimal_workers = min(cpu_count, max_workers)
        self._executor = ThreadPoolExecutor(max_workers=optimal_workers)
        self._max_workers = max_workers
        self._system_cpu_count = cpu_count
        
        # 控制标志
        self._running = True
        
        # 处理中的任务
        self._processing = set()
        self._processing_lock = threading.Lock()
        

        
        # 启动渲染线程
        self._render_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._render_thread.start()
        
        # 订阅缩放事件
        event_bus.zoom_changed.connect(self._on_zoom_changed)
    

    
    def shutdown(self):
        """关闭渲染服务"""
        # 停止运行标志
        self._running = False
        
        # 等待渲染线程结束
        if hasattr(self, '_render_thread'):
            self._render_thread.join(timeout=2.0)
        
        # 关闭线程池
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
        
        # 取消订阅事件
        event_bus.zoom_changed.disconnect(self._on_zoom_changed)
    
    def render_page(self, doc, page_num: int, zoom_level: float, doc_mutex: Optional[QMutex] = None, 
                   priority: int = 0) -> Optional[Any]:
        """渲染页面
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        - doc_mutex: QMutex, 文档访问锁，可选
        - priority: int, 优先级，数字越小优先级越高
        
        返回：
        - Optional[QPixmap]: 渲染后的页面图像，渲染失败返回None
        """
        try:
            # 检查缓存
            cached_pixmap = self._page_cache.get_page(page_num, zoom_level)
            if cached_pixmap:
                event_bus.publish_render_completed(page_num, cached_pixmap, True)
                return cached_pixmap
            
            # 缓存未命中，执行渲染
            pixmap = self._page_renderer.render_page(doc, page_num, zoom_level, doc_mutex)
            
            if pixmap:
                # 将渲染结果存入缓存
                self._page_cache.add_page(page_num, zoom_level, pixmap)
                event_bus.publish_render_completed(page_num, pixmap, True)
            else:
                self.logger.error(f"渲染页面失败：{page_num}，缩放级别：{zoom_level}")
                event_bus.publish_render_completed(page_num, None, True)
            
            return pixmap
        except Exception as e:
            self.logger.error(f"渲染页面失败：{str(e)}")
            event_bus.publish_render_completed(page_num, None, True)
            return None
    
    def queue_render(self, doc, page_num: int, zoom_level: float, doc_mutex: Optional[QMutex] = None, 
                    priority: int = 0) -> int:
        """将渲染请求加入队列
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        - doc_mutex: QMutex, 文档访问锁，可选
        - priority: int, 优先级，数字越小优先级越高
        
        返回：
        - int: 请求ID
        """
        # 检查缓存
        cached_pixmap = self._page_cache.get_page(page_num, zoom_level)
        if cached_pixmap:
            event_bus.publish_render_completed(page_num, cached_pixmap, True)
            return id(cached_pixmap)
        
        # 创建渲染任务
        task = RenderTask(page_num, zoom_level, priority)
        
        # 检查是否已经在处理
        task_key = (page_num, zoom_level)
        with self._processing_lock:
            if task_key in self._processing:
                return task.id
            
            # 添加到处理中集合
            self._processing.add(task_key)
        
        # 将任务加入队列
        self._render_queue.put((priority, task, doc, doc_mutex))
        
        return task.id
    
    def preload_pages(self, doc, current_page: int, zoom_level: float, doc_mutex: Optional[QMutex] = None, 
                     preload_range: int = 2) -> int:
        """预加载页面到缓存（智能预加载）
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - current_page: int, 当前页面编号
        - zoom_level: float, 缩放级别
        - doc_mutex: QMutex, 文档访问锁，可选
        - preload_range: int, 预加载范围，前后各preload_range页
        
        返回：
        - int: 预加载成功的页面数量
        """
        import psutil
        import os
        
        try:
            if not doc:
                self.logger.error("预加载页面失败：文档对象为None")
                return 0
            
            # 检查系统负载，只在空闲时预加载
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.Process(os.getpid()).memory_percent()
            
            # 如果系统负载高，减少预加载范围
            if cpu_usage > 70 or memory_usage > 60:
                preload_range = max(1, preload_range // 2)
            
            total_pages = len(doc)
            preloaded = 0
            preload_tasks = []
            
            # 预加载前后页面
            for i in range(-preload_range, preload_range + 1):
                if i == 0:
                    continue  # 跳过当前页，已经在显示
                
                page_num = current_page + i
                if 0 <= page_num < total_pages:
                    # 检查缓存
                    if not self._page_cache.get_page(page_num, zoom_level):
                        # 检查是否已经在处理
                        task_key = (page_num, round(zoom_level, 2))
                        with self._processing_lock:
                            if task_key not in self._processing:
                                preload_tasks.append(page_num)
            
            # 批量提交预加载任务
            for page_num in preload_tasks:
                # 使用低优先级预加载
                self.queue_render(doc, page_num, zoom_level, doc_mutex, 
                                 priority=20)
            
            return len(preload_tasks)
        except Exception as e:
            self.logger.error(f"预加载页面失败：{str(e)}")
            return 0
    
    def clear_cache(self, page_num: Optional[int] = None):
        """清除页面缓存
        
        参数：
        - page_num: int, 页面编号，None表示清除所有缓存
        """
        try:
            if page_num is None:
                self._page_cache.clear()
            else:
                self._page_cache.remove_page(page_num)
        except Exception as e:
            self.logger.error(f"清除页面缓存失败：{str(e)}")
    
    def get_page_size(self, doc, page_num: int, zoom_level: float, doc_mutex: Optional[QMutex] = None) -> Tuple[float, float]:
        """获取页面尺寸
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        - doc_mutex: QMutex, 文档访问锁，可选
        
        返回：
        - Tuple[float, float]: 页面尺寸 (width, height)
        """
        try:
            return self._page_renderer.get_page_size(doc, page_num, zoom_level, doc_mutex)
        except Exception as e:
            self.logger.error(f"获取页面尺寸失败：{str(e)}")
            return (0, 0)
    
    def _process_queue(self):
        """处理渲染队列"""
        while self._running:
            try:
                # 获取渲染任务
                priority, task, doc, doc_mutex = self._render_queue.get(timeout=0.1)
                
                # 提交到线程池处理
                future = self._executor.submit(self._process_task, task, doc, doc_mutex)
                future.add_done_callback(lambda f, t=task: self._task_completed(t))
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"处理渲染队列失败：{str(e)}")
                continue
    
    def _process_task(self, task: RenderTask, doc, doc_mutex: Optional[QMutex]):
        """处理渲染任务"""
        try:
            # 渲染页面
            pixmap = self._page_renderer.render_page(doc, task.page_num, task.zoom_level, doc_mutex)
            
            if pixmap:
                # 将渲染结果存入缓存
                self._page_cache.add_page(task.page_num, task.zoom_level, pixmap)
            else:
                self.logger.error(f"渲染页面失败：{task.page_num}，缩放级别：{task.zoom_level}")
            
            # 发布渲染完成事件
            event_bus.publish_render_completed(task.page_num, pixmap, True)
            
        except Exception as e:
            self.logger.error(f"处理渲染任务失败：{str(e)}")
            
            # 发布渲染完成事件
            event_bus.publish_render_completed(task.page_num, None, True)
    
    def _task_completed(self, task: RenderTask):
        """任务完成处理"""
        # 从处理中集合移除
        task_key = (task.page_num, task.zoom_level)
        with self._processing_lock:
            if task_key in self._processing:
                self._processing.remove(task_key)
        
        # 标记任务完成
        self._render_queue.task_done()
    
    def _on_zoom_changed(self, zoom_level: float, zoom_mode: str):
        """处理缩放变化事件
        
        参数：
        - zoom_level: float, 新的缩放级别
        - zoom_mode: str, 新的缩放模式
        """
        # 缩放变化时，清理队列中的旧渲染任务
        # 注意：由于PriorityQueue不支持直接删除任务，我们通过标记来处理
        # 这里我们只记录缩放变化，实际的任务管理在处理队列时进行
        
        # 更新最新的缩放级别
        self._last_zoom_level = zoom_level
    
    def get_cache_status(self) -> dict:
        """获取缓存状态
        
        返回：
        - dict: 缓存状态信息
        """
        try:
            cache_info = {
                "cache_size": self._page_cache.get_cache_size(),
                "cached_pages": self._page_cache.get_cached_pages(),
                "memory_usage": self._page_cache.get_memory_usage()
            }
            return cache_info
        except Exception as e:
            self.logger.error(f"获取缓存状态失败：{str(e)}")
            return {}

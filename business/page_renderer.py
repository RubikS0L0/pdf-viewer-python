#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
页面渲染类

负责将PDF页面渲染为QPixmap或QImage，支持不同缩放级别，确保线程安全。
"""

import fitz  # PyMuPDF
import logging
import time
import threading
import multiprocessing
from queue import PriorityQueue, Empty
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QMutex, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QImage

from utils.constants import Constants
from business.interfaces import IPageRenderer

# 导入异常处理模块
from utils.exception_handler import handle_exception, ResourceManager, handle_specific_exceptions


class RenderRequest:
    """渲染请求类"""
    def __init__(self, page_num, zoom_level, priority=0, callback=None):
        """初始化渲染请求
        
        参数：
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        - priority: int, 优先级，数字越小优先级越高
        - callback: callable, 渲染完成后的回调函数
        """
        self.page_num = page_num
        self.zoom_level = zoom_level
        self.priority = priority
        self.callback = callback
        self.id = id(self)
    
    def __lt__(self, other):
        """比较优先级"""
        return self.priority < other.priority


class PageRenderer:
    """负责将PDF页面渲染为QPixmap或QImage，支持不同缩放级别"""
    
    # 实现IPageRenderer接口的所有方法
    
    def __init__(self, max_workers=4):
        """初始化PageRenderer实例
        
        参数：
        - max_workers: int, 最大工作线程数
        """
        self.logger = logging.getLogger(__name__)
        self._render_queue = PriorityQueue()
        
        # 动态计算线程池大小，基于系统CPU核心数
        cpu_count = multiprocessing.cpu_count()
        optimal_workers = min(cpu_count, max_workers)
        self._executor = ThreadPoolExecutor(max_workers=optimal_workers)
        self._max_workers = max_workers
        self._system_cpu_count = cpu_count
        
        self._running = True
        self._processing = set()
        self._lock = threading.Lock()
        self._task_cache = {}  # 任务缓存，用于合并重复任务
        
        # 启动渲染线程
        self._render_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._render_thread.start()
    
    def shutdown(self):
        """关闭渲染器"""
        self._running = False
        if hasattr(self, '_render_thread'):
            self._render_thread.join(timeout=2.0)
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
    
    @handle_specific_exceptions
    def _render_page_common(self, doc, page_num, zoom_level=1.0, doc_mutex=None):
        """渲染页面的公共逻辑，返回像素数据
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        
        返回：
        - tuple: (width, height, stride, samples) 像素数据，渲染失败则返回None
        """
        if not doc:
            self.logger.error("渲染页面失败：文档对象为None")
            return None
        
        if page_num < 0 or page_num >= len(doc):
            self.logger.error(f"渲染页面失败：页码{page_num}超出范围")
            return None
        
        # 锁定文档访问（如果提供了锁）
        if doc_mutex:
            doc_mutex.lock()
        
        try:
            # 加载页面并设置渲染矩阵
            page = doc.load_page(page_num)
            matrix = fitz.Matrix(zoom_level, zoom_level)
            
            # 渲染页面，只使用matrix参数控制缩放
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            # 只返回像素数据，不创建QImage
            return (pix.width, pix.height, pix.stride, pix.samples)
        except fitz.FileDataError as e:
            error_info = handle_exception(e, self.logger, {"action": "render_page", "page_num": page_num, "zoom": zoom_level})
            self.logger.error(f"PDF文件数据错误：{error_info.message}")
            return None
        except fitz.PageError as e:
            error_info = handle_exception(e, self.logger, {"action": "render_page", "page_num": page_num, "zoom": zoom_level})
            self.logger.error(f"页面加载错误：{error_info.message}")
            return None
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "render_page", "page_num": page_num, "zoom": zoom_level})
            self.logger.error(f"渲染页面失败：{error_info.message}")
            return None
        finally:
            # 释放文档访问锁
            if doc_mutex:
                try:
                    doc_mutex.unlock()
                except Exception as e:
                    error_info = handle_exception(e, self.logger, {"action": "unlock_mutex"})
                    self.logger.error(f"释放文档锁失败：{error_info.message}")
    
    @handle_specific_exceptions
    def render_page_progressive(self, doc, page_num, zoom_level=1.0, doc_mutex=None, callback=None):
        """渐进式渲染页面，通过 callback 回传结果。
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        - callback: callable, 渲染完成后的回调函数，签名：callback(page_num, pixmap, is_final)
        
        返回：
        - QPixmap | None：在主线程调用时返回渲染结果；
                          在子线程中调用时结果通过 callback 异步回传，返回 None。
        
        【设计说明】
        之前的实现通过 QTimer.singleShot(0, handle_final) 在事件循环中延迟创建 Qt 对象，
        但 return 语句在 handle_final 执行之前就已经返回，导致返回值永远是 None，
        违反了接口文档描述的契约。
        
        现在的实现：
        1. 先获取像素数据（线程安全，可在任何线程调用）
        2. 若在主线程（有 QApplication 事件循环），直接在当前线程创建 Qt 对象并返回
        3. 若有 callback，同时通过 callback 通知结果，与原有调用方保持兼容
        """
        try:
            pixel_data = self._render_page_common(doc, page_num, zoom_level, doc_mutex)

            if not pixel_data:
                if callback:
                    try:
                        callback(page_num, None, True)
                    except Exception as e:
                        handle_exception(e, self.logger, {"action": "callback_execution", "page_num": page_num})
                return None

            width, height, stride, samples = pixel_data
            img = QImage(samples, width, height, stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)

            if callback:
                try:
                    callback(page_num, pixmap, True)
                except Exception as e:
                    handle_exception(e, self.logger, {"action": "callback_execution", "page_num": page_num})

            return pixmap

        except Exception as e:
            handle_exception(e, self.logger, {"action": "render_page_progressive", "page_num": page_num, "zoom": zoom_level})
            if callback:
                try:
                    callback(page_num, None, True)
                except Exception:
                    pass
            return None
    
    def queue_progressive_render(self, doc, page_num, zoom_level=1.0, doc_mutex=None, priority=0, callback=None):
        """将渐进式渲染请求加入队列（支持任务合并）
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        - priority: int, 优先级，数字越小优先级越高
        - callback: callable, 渲染完成后的回调函数
        
        返回：
        - int: 请求ID
        """
        # 生成任务键
        task_key = (page_num, round(zoom_level, 2))  # 缩放级别保留两位小数
        
        # 检查是否有相同任务正在处理
        with self._lock:
            if task_key in self._task_cache:
                # 任务已存在，添加回调到现有任务
                existing_callbacks = self._task_cache[task_key]
                if callback:
                    existing_callbacks.append(callback)
                return id(existing_callbacks)
            
            # 创建回调列表
            callbacks = [callback] if callback else []
            self._task_cache[task_key] = callbacks
        
        # 创建一个包装的回调函数
        def wrapped_callback(page_num, result, is_final=False):
            # 执行所有回调
            with self._lock:
                if task_key in self._task_cache:
                    callbacks = self._task_cache[task_key]
                    # 移除任务缓存
                    del self._task_cache[task_key]
                else:
                    callbacks = []
            
            for cb in callbacks:
                if cb:
                    try:
                        cb(page_num, result, is_final)
                    except Exception as e:
                        self.logger.error(f"执行渲染队列回调失败：{str(e)}")
        
        # 创建渲染请求
        request = RenderRequest(page_num, zoom_level, priority, wrapped_callback)
        # 将请求加入优先级队列
        self._render_queue.put((priority, request, doc, zoom_level, doc_mutex, True))  # 最后一个参数表示是否为渐进式渲染
        
        # 使用对象ID作为请求ID
        return request.id
    
    def _validate_render_result(self, page_num, zoom_level, pixmap, expected_size):
        """验证渲染结果
        
        参数：
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        - pixmap: QPixmap, 渲染结果
        - expected_size: tuple, 预期尺寸 (width, height)
        
        返回：
        - bool: 验证通过返回True，否则返回False
        """
        if not pixmap:
            self.logger.error(f"渲染结果验证失败：页面{page_num}渲染结果为None")
            return False
        
        actual_size = (pixmap.width(), pixmap.height())
        expected_width, expected_height = expected_size
        
        # 允许5%的误差
        width_error = abs(actual_size[0] - expected_width) / expected_width if expected_width > 0 else 0
        height_error = abs(actual_size[1] - expected_height) / expected_height if expected_height > 0 else 0
        
        if width_error > 0.05 or height_error > 0.05:
            self.logger.warning(f"渲染结果尺寸与预期不符：页面{page_num}，缩放级别：{zoom_level}，实际尺寸：{actual_size}，预期尺寸：{expected_size}")
            return False
        
        return True
    
    def render_page(self, doc, page_num, zoom_level=1.0, doc_mutex=None):
        """渲染指定页码的页面（同步方法）
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        
        返回：
        - QPixmap: 渲染后的QPixmap对象，渲染失败则返回None
        """
        # 格式化缩放级别，确保一致性
        formatted_zoom = round(zoom_level * 100) / 100
        
        max_retries = Constants.RENDER_RETRY_COUNT.value
        for attempt in range(max_retries):
            try:
                # 计算预期尺寸
                expected_size = self.get_page_size(doc, page_num, formatted_zoom, doc_mutex)
                
                # 使用公共渲染逻辑获取像素数据
                pixel_data = self._render_page_common(doc, page_num, formatted_zoom, doc_mutex)
                if pixel_data:
                    # 在当前线程创建Qt对象（假设调用者在主线程）
                    width, height, stride, samples = pixel_data
                    img = QImage(samples, width, height, stride, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(img)
                    
                    # 验证渲染结果
                    self._validate_render_result(page_num, formatted_zoom, pixmap, expected_size)
                    
                    return pixmap
            except Exception as e:
                self.logger.error(f"渲染页面{page_num}失败，缩放级别：{formatted_zoom}，第{attempt + 1}次尝试：{str(e)}")
                if attempt == max_retries - 1:
                    # 最后一次尝试失败，返回None
                    return None
                # 等待一段时间后重试
                time.sleep(Constants.RENDER_RETRY_DELAY.value)

    def render_page_to_image(self, doc, page_num, zoom_level=1.0, doc_mutex=None):
        """渲染页面为QImage对象（同步方法）
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        
        返回：
        - QImage: 渲染后的QImage对象，渲染失败则返回None
        """
        try:
            # 使用公共渲染逻辑获取像素数据
            pixel_data = self._render_page_common(doc, page_num, zoom_level, doc_mutex)
            if pixel_data:
                # 在当前线程创建Qt对象（假设调用者在主线程）
                width, height, stride, samples = pixel_data
                return QImage(samples, width, height, stride, QImage.Format_RGB888)
            return None
        except Exception as e:
            self.logger.error(f"渲染页面到QImage失败：{str(e)}")
            return None
    
    def get_page_size(self, doc, page_num, zoom_level=1.0, doc_mutex=None):
        """获取指定缩放级别下的页面尺寸
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        
        返回：
        - tuple: (width, height)，页面尺寸，获取失败则返回(0, 0)
        """
        try:
            if not doc:
                self.logger.error("获取页面尺寸失败：文档对象为None")
                return (0, 0)
            
            if page_num < 0 or page_num >= len(doc):
                self.logger.error(f"获取页面尺寸失败：页码{page_num}超出范围")
                return (0, 0)
            
            # 锁定文档访问（如果提供了锁）
            if doc_mutex:
                doc_mutex.lock()
            
            try:
                # 加载页面并计算尺寸
                page = doc.load_page(page_num)
                rect = page.rect
                width = rect.width * zoom_level
                height = rect.height * zoom_level
                
                return (width, height)
            finally:
                # 释放文档访问锁
                if doc_mutex:
                    doc_mutex.unlock()
        except Exception as e:
            self.logger.error(f"获取页面尺寸失败：{str(e)}")
            return (0, 0)
    
    def queue_render(self, doc, page_num, zoom_level=1.0, doc_mutex=None, priority=0, callback=None):
        """将渲染请求加入队列
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        - priority: int, 优先级，数字越小优先级越高
        - callback: callable, 渲染完成后的回调函数
        
        返回：
        - int: 请求ID
        """
        request = RenderRequest(page_num, zoom_level, priority, callback)
        self._render_queue.put((priority, request, doc, zoom_level, doc_mutex))
        return request.id
    
    def _process_queue(self):
        """处理渲染队列"""
        while self._running:
            try:
                # 获取渲染请求
                queue_item = self._render_queue.get(timeout=0.1)
                
                # 解析队列项
                if len(queue_item) == 5:
                    # 普通渲染请求
                    priority, request, doc, zoom_level, doc_mutex = queue_item
                    is_progressive = False
                elif len(queue_item) == 6:
                    # 渐进式渲染请求
                    priority, request, doc, zoom_level, doc_mutex, is_progressive = queue_item
                else:
                    # 无效请求
                    self._render_queue.task_done()
                    continue
                
                # 检查是否已经在处理
                with self._lock:
                    if (request.page_num, request.zoom_level) in self._processing:
                        self._render_queue.task_done()
                        continue
                    self._processing.add((request.page_num, request.zoom_level))
                
                # 提交到线程池处理
                if is_progressive:
                    # 处理渐进式渲染请求
                    future = self._executor.submit(self._render_progressive_task, request, doc, zoom_level, doc_mutex)
                else:
                    # 处理普通渲染请求
                    future = self._executor.submit(self._render_task, request, doc, zoom_level, doc_mutex)
                future.add_done_callback(lambda f, req=request: self._task_completed(req))
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"处理渲染队列失败：{str(e)}")
                continue
    
    def _render_task(self, request, doc, zoom_level, doc_mutex):
        """执行渲染任务"""
        try:
            # 渲染页面
            result = self.render_page(doc, request.page_num, zoom_level, doc_mutex)
            
            # 调用回调
            if request.callback:
                try:
                    request.callback(request.page_num, result)
                except Exception as e:
                    self.logger.error(f"执行渲染回调失败：{str(e)}")
        except Exception as e:
            self.logger.error(f"执行渲染任务失败：{str(e)}")
    
    def _render_progressive_task(self, request, doc, zoom_level, doc_mutex):
        """执行渐进式渲染任务"""
        try:
            # 渐进式渲染页面
            result = self.render_page_progressive(doc, request.page_num, zoom_level, doc_mutex, request.callback)
        except Exception as e:
            self.logger.error(f"执行渐进式渲染任务失败：{str(e)}")
    
    def _task_completed(self, request):
        """任务完成处理"""
        with self._lock:
            self._processing.discard((request.page_num, request.zoom_level))
        self._render_queue.task_done()
    
    def batch_render(self, doc, page_nums, zoom_level=1.0, doc_mutex=None, priority=0, callback=None):
        """批量渲染页面
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_nums: list, 页面编号列表
        - zoom_level: float, 缩放级别，默认为1.0
        - doc_mutex: QMutex, 文档访问锁，可选
        - priority: int, 优先级，数字越小优先级越高
        - callback: callable, 每个页面渲染完成后的回调函数
        
        返回：
        - list: 请求ID列表
        """
        request_ids = []
        for page_num in page_nums:
            req_id = self.queue_render(doc, page_num, zoom_level, doc_mutex, priority, callback)
            request_ids.append(req_id)
        return request_ids
    
    def cancel_render(self, page_num, zoom_level):
        """取消渲染请求
        
        注意：由于队列的特性，只能取消尚未开始处理的请求
        """
        # 这里简化处理，实际项目中可能需要更复杂的取消机制

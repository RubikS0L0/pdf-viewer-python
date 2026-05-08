#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF服务类

封装PDF相关的核心业务逻辑，提供统一的接口给UI层使用
"""

import os
import logging
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtGui import QPixmap

from business.interfaces import IPDFManager, IPageRenderer, IPageCache
from business.pdf_processor import PDFProcessor

# 导入异常处理模块
from utils.exception_handler import handle_exception, ResourceManager, handle_specific_exceptions

# 导入事件总线
from services.event_bus import event_bus


class PDFService:
    """PDF服务类"""
    
    # 共享线程池最大工作线程数
    _ASYNC_MAX_WORKERS = 2

    def __init__(self, pdf_manager: IPDFManager, page_renderer: IPageRenderer, page_cache: IPageCache):
        """初始化PDF服务
        
        参数：
        - pdf_manager: IPDFManager, PDF管理器实例
        - page_renderer: IPageRenderer, 页面渲染器实例
        - page_cache: IPageCache, 页面缓存实例
        """
        self.pdf_manager = pdf_manager
        self.page_renderer = page_renderer
        self.page_cache = page_cache
        self.logger = logging.getLogger(__name__)
        
        # 初始化PDF处理器
        self.pdf_processor = PDFProcessor()

        # 共享线程池：整个 PDFService 生命周期内复用，避免每次调用都创建新线程池
        # 使用 max_workers=2 既保留并发能力，又不过度占用系统资源
        self._executor = ThreadPoolExecutor(max_workers=self._ASYNC_MAX_WORKERS)

    def shutdown(self):
        """释放资源，关闭线程池。应在应用退出或不再需要该服务时调用。"""
        self._executor.shutdown(wait=False)
        self.logger.info("PDFService 线程池已关闭")
    
    @staticmethod
    def _validate_pdf_file(file_path: str) -> tuple[bool, str]:
        """验证文件是否为合法的 PDF 文件。
        
        同时检查：
        1. 路径非空且文件存在
        2. 文件扩展名为 .pdf（不区分大小写）
        3. 文件头部魔数为 b'%PDF-'（防止扩展名伪装）
        
        返回：
        - (True, "") 表示验证通过
        - (False, reason) 表示验证失败，reason 为原因描述
        """
        if not file_path:
            return False, "文件路径为空"
        if not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}"
        if not file_path.lower().endswith('.pdf'):
            return False, f"文件扩展名不是 .pdf: {file_path}"
        # 读取文件魔数（前5字节），验证是否真正是PDF格式
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(5)
            if magic != b'%PDF-':
                return False, f"文件头部魔数不符合PDF格式（期望 %PDF-，实际 {magic!r}）: {file_path}"
        except OSError as e:
            return False, f"读取文件头部失败: {e}"
        return True, ""

    @handle_specific_exceptions
    def open_document(self, file_path: str) -> bool:
        """打开PDF文档
        
        参数：
        - file_path: str, PDF文件路径
        
        返回：
        - bool: 打开成功返回True，否则返回False
        """
        resource_manager = ResourceManager()
        
        try:
            # 使用统一的文件验证（扩展名 + 魔数双重校验）
            valid, reason = self._validate_pdf_file(file_path)
            if not valid:
                self.logger.error(f"PDF文件验证失败: {reason}")
                return False
            
            # 获取文件大小
            pdf_file_size = os.path.getsize(file_path)
            
            # 清空页面缓存
            try:
                self.page_cache.clear()
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "clear_cache", "file": file_path})
                self.logger.error(f"清空页面缓存失败: {error_info.message}")
            
            # 打开文档
            success = self.pdf_manager.open(file_path)
            
            if success:
                # 根据PDF文件大小动态调整缓存大小
                if hasattr(self.page_cache, 'update_cache_size'):
                    try:
                        self.page_cache.update_cache_size(pdf_file_size)
                    except Exception as e:
                        error_info = handle_exception(e, self.logger, {"action": "update_cache_size", "file": file_path, "size": pdf_file_size})
                        self.logger.error(f"更新缓存大小失败: {error_info.message}")
            else:
                self.logger.error(f"PDF文档打开失败: {file_path}")
            
            return success
        except FileNotFoundError as e:
            error_info = handle_exception(e, self.logger, {"action": "open_document", "file": file_path})
            return False
        except PermissionError as e:
            error_info = handle_exception(e, self.logger, {"action": "open_document", "file": file_path})
            return False
        except IOError as e:
            error_info = handle_exception(e, self.logger, {"action": "open_document", "file": file_path})
            return False
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "open_document", "file": file_path})
            return False
    
    @handle_specific_exceptions
    def close_document(self) -> bool:
        """关闭PDF文档
        
        返回：
        - bool: 关闭成功返回True，否则返回False
        """
        resource_manager = ResourceManager()
        
        try:
            # 刷新所有缓存，确保数据写入磁盘
            # flush_all方法已移除，直接清空缓存
            
            # 清空页面缓存
            try:
                self.page_cache.clear()
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "clear_cache"})
                self.logger.error(f"清空页面缓存失败: {error_info.message}")
            
            # 清理PDF处理器缓存
            try:
                if hasattr(self, 'pdf_processor'):
                    file_path = self.pdf_manager.get_file_path()
                    self.pdf_processor.clear_cache(file_path)
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "clear_processor_cache"})
                self.logger.error(f"清理PDF处理器缓存失败: {error_info.message}")
            
            # 关闭文档
            success = self.pdf_manager.close()
            
            if not success:
                self.logger.error("PDF文档关闭失败")
            
            return success
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "close_document"})
            return False
    
    def get_page_count(self) -> int:
        """获取文档页数
        
        返回：
        - int: 文档页数
        """
        return self.pdf_manager.page_count
    
    def is_document_open(self) -> bool:
        """检查是否有文档打开
        
        返回：
        - bool: 有文档打开返回True，否则返回False
        """
        return self.pdf_manager.is_open
    
    def get_document_path(self) -> Optional[str]:
        """获取当前打开的文档路径
        
        返回：
        - Optional[str]: 当前打开的文档路径，无文档打开返回None
        """
        return self.pdf_manager.get_file_path()
    
    @handle_specific_exceptions
    def render_page(self, page_num: int, zoom_level: float = 1.0) -> Optional[object]:
        """渲染指定页码的页面（同步方法）
        
        参数：
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        
        返回：
        - Optional[QPixmap]: 渲染后的页面图像，渲染失败返回None
        """
        resource_manager = ResourceManager()
        
        try:
            if not self.pdf_manager.is_open:
                self.logger.error("渲染页面失败：无文档打开")
                return None
            
            # 使用指定的缩放级别
            actual_zoom = zoom_level
            
            # 检查缓存中是否已有该页面的渲染结果
            try:
                cached_pixmap = self.page_cache.get_page(page_num, actual_zoom)
                if cached_pixmap:
                    return cached_pixmap
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "get_cached_page", "page_num": page_num, "zoom": actual_zoom})
                self.logger.error(f"获取缓存页面失败：{error_info.message}")
            
            # 使用PDF处理器渲染页面，根据缩放级别调整dpi
            pdf_path = self.pdf_manager.get_file_path()
            # 将缩放级别转换为dpi
            dpi = int(96 * actual_zoom)
            
            try:
                result = self.pdf_processor.render_page(pdf_path, page_num, dpi=dpi)
                
                if result:
                    temp_path, (width, height) = result
                    # 从临时文件加载为QPixmap
                    pixmap = QPixmap(temp_path)
                    
                    # 将渲染结果存入缓存
                    try:
                        self.page_cache.add_page(page_num, actual_zoom, pixmap)
                    except Exception as e:
                        error_info = handle_exception(e, self.logger, {"action": "add_to_cache", "page_num": page_num, "zoom": actual_zoom})
                        self.logger.error(f"添加到缓存失败：{error_info.message}")
                    
                    return pixmap
                else:
                    self.logger.error(f"渲染页面失败：{page_num}")
                    return None
            except FileNotFoundError as e:
                error_info = handle_exception(e, self.logger, {"action": "render_page", "page_num": page_num, "file": pdf_path})
                self.logger.error(f"渲染页面失败：{error_info.message}")
                return None
            except PermissionError as e:
                error_info = handle_exception(e, self.logger, {"action": "render_page", "page_num": page_num, "file": pdf_path})
                self.logger.error(f"渲染页面失败：{error_info.message}")
                return None
            except IOError as e:
                error_info = handle_exception(e, self.logger, {"action": "render_page", "page_num": page_num, "file": pdf_path})
                self.logger.error(f"渲染页面失败：{error_info.message}")
                return None
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "render_page", "page_num": page_num, "zoom": zoom_level})
            return None
    
    @handle_specific_exceptions
    def render_page_async(self, page_num: int, zoom_level: float = 1.0, priority=0) -> int:
        """异步渲染指定页码的页面
        
        参数：
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        - priority: int, 优先级，数字越小优先级越高（当前实现未使用，预留扩展）
        
        返回：
        - int: Future 对象的 id，可用于追踪任务；-1 表示调用失败
        
        注意：返回值仅是标识符，不保证任务完成时间；
              结果通过事件总线的render_completed事件回传。
        """
        try:
            if not self.pdf_manager.is_open:
                self.logger.error("异步渲染页面失败：无文档打开")
                event_bus.publish_render_completed(page_num, None, True)
                return -1
            
            actual_zoom = zoom_level
            
            # 命中缓存时发布事件，无需入队
            try:
                cached_pixmap = self.page_cache.get_page(page_num, actual_zoom)
                if cached_pixmap:
                    event_bus.publish_render_completed(page_num, cached_pixmap, True)
                    return 0
            except Exception as e:
                handle_exception(e, self.logger, {"action": "get_cached_page", "page_num": page_num, "zoom": actual_zoom})
            
            pdf_path = self.pdf_manager.get_file_path()
            dpi = int(96 * actual_zoom)
            
            def async_render():
                """在线程池中执行渲染，结果通过事件总线发布"""
                try:
                    result = self.pdf_processor.render_page(pdf_path, page_num, dpi=dpi)
                    if result:
                        temp_path, (_w, _h) = result
                        pixmap = QPixmap(temp_path)
                        # 写入内存缓存（is_final=True 时才缓存，避免低质量中间帧污染缓存）
                        try:
                            self.page_cache.add_page(page_num, actual_zoom, pixmap)
                        except Exception as e:
                            handle_exception(e, self.logger, {"action": "add_to_cache", "page_num": page_num})
                        event_bus.publish_render_completed(page_num, pixmap, True)
                    else:
                        self.logger.error(f"异步渲染页面 {page_num} 无结果")
                        event_bus.publish_render_completed(page_num, None, True)
                except Exception as e:
                    handle_exception(e, self.logger, {"action": "async_render", "page_num": page_num, "file": pdf_path})
                    event_bus.publish_render_completed(page_num, None, True)
            
            # 复用共享线程池，避免每次调用都创建新线程池导致资源泄漏
            future = self._executor.submit(async_render)
            return id(future)
        except Exception as e:
            handle_exception(e, self.logger, {"action": "render_page_async", "page_num": page_num, "zoom": zoom_level})
            event_bus.publish_render_completed(page_num, None, True)
            return -1
    
    @handle_specific_exceptions
    def get_page_size(self, page_num: int, zoom_level: float = 1.0) -> Tuple[float, float]:
        """获取指定页码的页面尺寸
        
        参数：
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，默认为1.0
        
        返回：
        - Tuple[float, float]: 页面尺寸 (width, height)
        """
        resource_manager = ResourceManager()
        
        try:
            if not self.pdf_manager.is_open:
                self.logger.error("获取页面尺寸失败：无文档打开")
                return (0, 0)
            
            # 使用PDF处理器获取页面尺寸
            pdf_path = self.pdf_manager.get_file_path()
            # 将缩放级别转换为dpi
            dpi = int(96 * zoom_level)
            
            try:
                size = self.pdf_processor.get_page_size(pdf_path, page_num, dpi=dpi)
                
                if size:
                    return size
                else:
                    self.logger.error(f"获取页面尺寸失败：{page_num}")
                    return (0, 0)
            except FileNotFoundError as e:
                error_info = handle_exception(e, self.logger, {"action": "get_page_size", "page_num": page_num, "file": pdf_path})
                self.logger.error(f"获取页面尺寸失败：{error_info.message}")
                return (0, 0)
            except PermissionError as e:
                error_info = handle_exception(e, self.logger, {"action": "get_page_size", "page_num": page_num, "file": pdf_path})
                self.logger.error(f"获取页面尺寸失败：{error_info.message}")
                return (0, 0)
            except IOError as e:
                error_info = handle_exception(e, self.logger, {"action": "get_page_size", "page_num": page_num, "file": pdf_path})
                self.logger.error(f"获取页面尺寸失败：{error_info.message}")
                return (0, 0)
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "get_page_size", "page_num": page_num, "zoom": zoom_level})
            return (0, 0)
    
    @handle_specific_exceptions
    def preload_pages(self, current_page: int, preload_range: int = 2, zoom_level: float = 1.0) -> int:
        """预加载页面到缓存（异步方式，不阻塞主线程）
        
        参数：
        - current_page: int, 当前页面编号
        - preload_range: int, 预加载范围，前后各preload_range页
        - zoom_level: float, 缩放级别，默认为1.0
        
        返回：
        - int: 提交的预加载任务数量
        """
        try:
            if not self.pdf_manager.is_open:
                self.logger.error("预加载页面失败：无文档打开")
                return 0
            
            pdf_path = self.pdf_manager.get_file_path()
            dpi = int(96 * zoom_level)
            submitted = 0
            
            # 构建需要预加载的页码列表（前后各 preload_range 页 + 当前页）
            pages_to_preload = []
            total_pages = self.get_page_count()
            for offset in range(preload_range + 1):
                for page_num in {current_page + offset, current_page - offset}:
                    if 0 <= page_num < total_pages:
                        # 跳过已在缓存中的页面
                        try:
                            if not self.page_cache.get_page(page_num, zoom_level):
                                pages_to_preload.append(page_num)
                        except Exception:
                            pages_to_preload.append(page_num)
            
            # 去重并保持顺序（优先预加载当前页附近）
            seen = set()
            unique_pages = []
            for p in pages_to_preload:
                if p not in seen:
                    seen.add(p)
                    unique_pages.append(p)
            
            def _preload_one(page_num):
                """在线程池中执行单页预渲染并存入缓存"""
                try:
                    cached = self.page_cache.get_page(page_num, zoom_level)
                    if cached:
                        return  # 已缓存，跳过
                    result = self.pdf_processor.render_page(pdf_path, page_num, dpi=dpi)
                    if result:
                        temp_path, (_w, _h) = result
                        pixmap = QPixmap(temp_path)
                        try:
                            self.page_cache.add_page(page_num, zoom_level, pixmap)
                        except Exception as e:
                            handle_exception(e, self.logger, {"action": "preload_add_cache", "page_num": page_num})
                except Exception as e:
                    handle_exception(e, self.logger, {"action": "preload_render", "page_num": page_num})
            
            # 异步提交预加载任务，不阻塞主线程
            for page_num in unique_pages:
                self._executor.submit(_preload_one, page_num)
                submitted += 1
            
            return submitted
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "preload_pages", "current_page": current_page, "range": preload_range})
            return 0

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF处理器类

负责PDF解析和渲染的核心逻辑，使用多进程处理CPU密集型任务
"""

import fitz  # PyMuPDF
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, Dict, Any
import tempfile
import os


class PDFProcessor:
    """PDF处理器类，负责PDF解析和渲染的核心逻辑"""
    
    def __init__(self):
        """初始化PDF处理器"""
        self.logger = logging.getLogger(__name__)
        
        # 获取CPU核心数
        self.cpu_count = multiprocessing.cpu_count()
        
        # 创建线程池（IO密集型任务）
        self.thread_pool = ThreadPoolExecutor(max_workers=8)
        
        # 创建跨进程管理器
        self.manager = multiprocessing.Manager()
        
        # 创建跨进程缓存
        self.cache = self.manager.dict()
        
        # 创建缓存锁
        self.cache_lock = self.manager.Lock()
        
        # 缓存上限
        self.MAX_CACHE_SIZE = 50
        
        # 缓存访问时间记录
        self.cache_access = self.manager.dict()
        
        # 临时文件目录
        self.temp_dir = tempfile.gettempdir()
        
        # 缓存文件映射
        self.cache_files = self.manager.dict()
    
    def shutdown(self):
        """关闭处理器，清理资源"""
        try:
            # 关闭线程池
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
            
            # 清理缓存文件
            self._cleanup_cache_files()
            
            # 关闭管理器
            if hasattr(self, 'manager'):
                self.manager.shutdown()
        except Exception as e:
            self.logger.error(f"关闭处理器失败: {str(e)}")
    
    def _cleanup_cache_files(self):
        """清理缓存文件"""
        try:
            for file_path in list(self.cache_files.values()):
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        self.logger.error(f"删除缓存文件失败 {file_path}: {str(e)}")
            self.cache_files.clear()
        except Exception as e:
            self.logger.error(f"清理缓存文件失败: {str(e)}")
    
    def _generate_cache_key(self, pdf_path: str, page_num: int, dpi: int, target_size: Tuple[int, int]) -> str:
        """生成缓存键"""
        return f"{pdf_path}_{page_num}_{dpi}_{target_size[0]}_{target_size[1]}"
    
    def _cleanup_old_cache(self):
        """清理最旧的缓存"""
        try:
            if len(self.cache) > self.MAX_CACHE_SIZE:
                # 按访问时间排序，删除最旧的
                sorted_keys = sorted(self.cache_access.items(), key=lambda x: x[1])
                keys_to_remove = sorted_keys[:len(self.cache) - self.MAX_CACHE_SIZE]
                
                for key, _ in keys_to_remove:
                    if key in self.cache:
                        del self.cache[key]
                    if key in self.cache_access:
                        del self.cache_access[key]
                    if key in self.cache_files:
                        file_path = self.cache_files[key]
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                self.logger.error(f"删除旧缓存文件失败 {file_path}: {str(e)}")
                        del self.cache_files[key]
        except Exception as e:
            self.logger.error(f"清理旧缓存失败: {str(e)}")
    
    @staticmethod
    def _render_page_worker(pdf_path: str, page_num: int, dpi: int, target_size: Tuple[int, int], temp_dir: str) -> Optional[Tuple[str, Tuple[int, int, bytes]]]:
        """渲染页面的工作函数（在子进程中执行）"""
        try:
            # 打开PDF文件
            with fitz.open(pdf_path) as doc:
                if page_num < 0 or page_num >= len(doc):
                    return None
                
                # 加载指定页面
                page = doc.load_page(page_num)
                
                # 计算缩放因子
                zoom = dpi / 72.0
                matrix = fitz.Matrix(zoom, zoom)
                
                # 生成位图
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                
                # 生成临时文件
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False, dir=temp_dir)
                temp_path = temp_file.name
                temp_file.close()
                
                # 保存位图
                pix.save(temp_path)
                
                # 返回结果
                return temp_path, (pix.width, pix.height, None)
        except Exception as e:
            logging.error(f"渲染页面失败 {page_num}: {str(e)}")
            return None
    
    def render_page(self, pdf_path: str, page_num: int, dpi: int = 96, target_size: Tuple[int, int] = (800, 1000)) -> Optional[Tuple[str, Tuple[int, int]]]:
        """渲染页面"""
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(pdf_path, page_num, dpi, target_size)
            
            # 尝试获取缓存
            with self.cache_lock:
                if cache_key in self.cache:
                    # 更新访问时间
                    self.cache_access[cache_key] = multiprocessing.current_process().pid
                    return self.cache[cache_key]
            
            # 直接执行渲染，不使用进程池，避免Pool对象传递问题
            rendered_result = self._render_page_worker(pdf_path, page_num, dpi, target_size, self.temp_dir)
            
            if rendered_result:
                temp_path, (width, height, _) = rendered_result
                
                # 更新缓存
                with self.cache_lock:
                    self.cache[cache_key] = (temp_path, (width, height))
                    self.cache_access[cache_key] = multiprocessing.current_process().pid
                    self.cache_files[cache_key] = temp_path
                    
                    # 清理旧缓存
                    self._cleanup_old_cache()
                
                return temp_path, (width, height)
            
            return None
        except Exception as e:
            self.logger.error(f"渲染页面失败: {str(e)}")
            return None
    
    def get_pdf_metadata(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """获取PDF元数据（IO密集型任务）"""
        try:
            # 提交到线程池
            future = self.thread_pool.submit(self._get_pdf_metadata_worker, pdf_path)
            return future.result(timeout=10.0)
        except Exception as e:
            self.logger.error(f"获取PDF元数据失败: {str(e)}")
            return None
    
    def _get_pdf_metadata_worker(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """获取PDF元数据的工作函数"""
        try:
            with fitz.open(pdf_path) as doc:
                metadata = {
                    'page_count': len(doc),
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'creator': doc.metadata.get('creator', ''),
                    'producer': doc.metadata.get('producer', ''),
                    'creation_date': doc.metadata.get('creationDate', ''),
                    'mod_date': doc.metadata.get('modDate', '')
                }
                return metadata
        except Exception as e:
            self.logger.error(f"获取PDF元数据失败: {str(e)}")
            return None
    
    def get_page_size(self, pdf_path: str, page_num: int, dpi: int = 96) -> Optional[Tuple[int, int]]:
        """获取页面尺寸"""
        try:
            # 提交到线程池
            future = self.thread_pool.submit(self._get_page_size_worker, pdf_path, page_num, dpi)
            return future.result(timeout=5.0)
        except Exception as e:
            self.logger.error(f"获取页面尺寸失败: {str(e)}")
            return None
    
    def _get_page_size_worker(self, pdf_path: str, page_num: int, dpi: int) -> Optional[Tuple[int, int]]:
        """获取页面尺寸的工作函数"""
        try:
            with fitz.open(pdf_path) as doc:
                if page_num < 0 or page_num >= len(doc):
                    return None
                
                page = doc.load_page(page_num)
                rect = page.rect
                
                # 计算实际尺寸
                zoom = dpi / 72.0
                width = rect.width * zoom
                height = rect.height * zoom
                
                return (int(width), int(height))
        except Exception as e:
            self.logger.error(f"获取页面尺寸失败: {str(e)}")
            return None
    
    def clear_cache(self, pdf_path: str = None):
        """清空缓存"""
        try:
            with self.cache_lock:
                if pdf_path:
                    # 清空指定PDF的缓存
                    keys_to_remove = []
                    for key in list(self.cache.keys()):
                        if key.startswith(pdf_path):
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        if key in self.cache:
                            del self.cache[key]
                        if key in self.cache_access:
                            del self.cache_access[key]
                        if key in self.cache_files:
                            file_path = self.cache_files[key]
                            if os.path.exists(file_path):
                                try:
                                    os.remove(file_path)
                                except Exception as e:
                                    self.logger.error(f"删除缓存文件失败 {file_path}: {str(e)}")
                            del self.cache_files[key]
                else:
                    # 清空所有缓存
                    self._cleanup_cache_files()
                    self.cache.clear()
                    self.cache_access.clear()
        except Exception as e:
            self.logger.error(f"清空缓存失败: {str(e)}")
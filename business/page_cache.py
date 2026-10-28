#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
页面缓存管理类

实现LRU（最近最少使用）缓存算法，管理已渲染的PDF页面，
support线程安全和自动内存监控清理。
"""

from collections import OrderedDict, defaultdict
import logging
import psutil
import os
import pickle
import hashlib
import time
from typing import Dict, Optional, Tuple

from PyQt6.QtCore import QMutex, QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QPixmap, QImage

from utils.constants import Constants
from utils.config_loader import config_loader
from business.interfaces import IPageCache


class PageCache(IPageCache):
    """实现LRU（最近最少使用）缓存算法，管理已渲染的PDF页面"""

    # ------------------------------------------------------------------ #
    # 默认值常量：统一定义在这里，所有初始化路径都引用同一套值，
    # 避免三处重复粘贴导致的不一致。
    # ------------------------------------------------------------------ #
    _DEFAULT_BASE_MAX_SIZE_TESTING = 5        # 测试环境默认缓存大小
    _DEFAULT_BASE_MAX_SIZE_CONFIG_FAIL = 10   # 配置加载失败时的回退大小
    _DEFAULT_BASE_MAX_SIZE_INIT_FAIL = 3      # 初始化异常时的最小安全大小
    _DEFAULT_MEMORY_WARNING_THRESHOLD = 80.0
    _DEFAULT_MEMORY_CRITICAL_THRESHOLD = 85.0
    _DEFAULT_CACHE_CLEANUP_RATIO = 0.5
    _DEFAULT_CRITICAL_CLEANUP_RATIO = 0.7
    _DEFAULT_DISK_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".pdf_viewer_cache")
    _DEFAULT_DISK_CACHE_SIZE = 1000

    def _apply_default_memory_thresholds(self):
        """将内存相关阈值设置为默认值（供初始化回退路径使用）"""
        self.MEMORY_WARNING_THRESHOLD = self._DEFAULT_MEMORY_WARNING_THRESHOLD
        self.MEMORY_CRITICAL_THRESHOLD = self._DEFAULT_MEMORY_CRITICAL_THRESHOLD
        self.CACHE_CLEANUP_RATIO = self._DEFAULT_CACHE_CLEANUP_RATIO
        self.CRITICAL_CLEANUP_RATIO = self._DEFAULT_CRITICAL_CLEANUP_RATIO

    def _apply_default_disk_cache(self, enabled: bool = False):
        """将磁盘缓存配置设置为默认值（供初始化回退路径使用）"""
        self.disk_cache_enabled = enabled
        self.disk_cache_dir = self._DEFAULT_DISK_CACHE_DIR
        self.disk_cache_size = self._DEFAULT_DISK_CACHE_SIZE

    def _init_common_attributes(self):
        """初始化通用属性（缓存容器、锁、指标等），供正常初始化路径使用"""
        self.cache = OrderedDict()
        self.cache_mutex = QMutex()
        self.logger = logging.getLogger(__name__)
        self.pdf_file_size = 0
        self.system_memory = self._get_system_memory()
        self.performance_metrics = {
            'hits': 0,
            'misses': 0,
            'hit_rate': 0.0,
            'total_operations': 0,
            'cache_size': 0,
            'memory_usage': 0.0,
            'last_cleanup_time': time.time(),
            'cleanup_count': 0,
            'disk_cache_hits': 0,
            'disk_cache_misses': 0
        }
        self.access_frequency = defaultdict(int)
        self.page_sizes = {}

    def __init__(self, max_size=None, use_config=False, renderer=None):
        """初始化页面缓存
        
        参数：
        - max_size: int, 缓存最大大小，默认为配置文件中的page_cache_size
        - use_config: bool, 是否使用配置文件，默认为False（测试环境使用）
        - renderer: 可选，页面渲染器（IPageRenderer）；供 preload_pages 复用，避免每次新建
        """
        # 预加载渲染器（可注入复用，避免 preload_pages 每次 new）
        self._renderer = renderer
        try:
            self._init_common_attributes()

            if use_config:
                # 从配置文件获取缓存大小
                try:
                    cache_config = config_loader.get_cache_config()
                    memory_config = config_loader.get_memory_config()
                    
                    self.base_max_size = max_size or cache_config.get("page_cache_size", Constants.PAGE_CACHE_SIZE.value * 2)
                    self.max_size = self.base_max_size
                    
                    # 内存监控配置（从配置文件加载，找不到时回退到默认常量）
                    self.MEMORY_WARNING_THRESHOLD = memory_config.get("warning_threshold", self._DEFAULT_MEMORY_WARNING_THRESHOLD)
                    self.MEMORY_CRITICAL_THRESHOLD = memory_config.get("critical_threshold", self._DEFAULT_MEMORY_CRITICAL_THRESHOLD)
                    self.CACHE_CLEANUP_RATIO = memory_config.get("cache_cleanup_ratio", self._DEFAULT_CACHE_CLEANUP_RATIO)
                    self.CRITICAL_CLEANUP_RATIO = memory_config.get("critical_cleanup_ratio", self._DEFAULT_CRITICAL_CLEANUP_RATIO)
                    
                    # 磁盘缓存配置
                    self.disk_cache_enabled = cache_config.get("disk_cache_enabled", True)
                    self.disk_cache_dir = cache_config.get("disk_cache_dir", self._DEFAULT_DISK_CACHE_DIR)
                    self.disk_cache_size = cache_config.get("disk_cache_size", self._DEFAULT_DISK_CACHE_SIZE)
                    
                    if self.disk_cache_enabled:
                        try:
                            os.makedirs(self.disk_cache_dir, exist_ok=True)
                        except Exception as e:
                            self.logger.error(f"创建磁盘缓存目录失败：{str(e)}")
                            self.disk_cache_enabled = False
                except Exception as e:
                    # 配置加载失败时，回退到默认值
                    self.logger.error(f"配置加载失败，使用默认值：{str(e)}")
                    self.base_max_size = max_size or self._DEFAULT_BASE_MAX_SIZE_CONFIG_FAIL
                    self.max_size = self.base_max_size
                    self._apply_default_memory_thresholds()
                    self._apply_default_disk_cache(enabled=False)
            else:
                # 测试环境使用默认值
                self.base_max_size = max_size or self._DEFAULT_BASE_MAX_SIZE_TESTING
                self.max_size = self.base_max_size
                self._apply_default_memory_thresholds()
                self._apply_default_disk_cache(enabled=False)

        except Exception as e:
            # 初始化失败时，使用最小安全默认值，确保对象仍可使用
            # 注意：此处重新获取 logger，因为 _init_common_attributes 可能未执行
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"PageCache初始化失败，降级到最小安全模式：{str(e)}")
            # 重新初始化所有核心属性
            self.cache = OrderedDict()
            self.cache_mutex = QMutex()
            self.pdf_file_size = 0
            self.system_memory = self._get_system_memory()
            self.performance_metrics = {
                'hits': 0, 'misses': 0, 'hit_rate': 0.0,
                'total_operations': 0, 'cache_size': 0, 'memory_usage': 0.0,
                'last_cleanup_time': time.time(), 'cleanup_count': 0,
                'disk_cache_hits': 0, 'disk_cache_misses': 0
            }
            self.access_frequency = defaultdict(int)
            self.page_sizes = {}
            self.base_max_size = max_size or self._DEFAULT_BASE_MAX_SIZE_INIT_FAIL
            self.max_size = self.base_max_size
            self._apply_default_memory_thresholds()
            self._apply_default_disk_cache(enabled=False)
    
    def get_page(self, page_num, zoom_level):
        """从缓存中获取页面
        
        参数：
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别
        
        返回：
        - QPixmap: 缓存的QPixmap对象，不存在则返回None
        """
        try:
            # 格式化缩放级别，确保一致性
            formatted_zoom = round(zoom_level * 100) / 100
            
            self.cache_mutex.lock()
            try:
                cache_key = self._generate_cache_key(page_num, formatted_zoom)
                
                if cache_key in self.cache:
                    # 更新访问频率
                    self.access_frequency[cache_key] += 1
                    # 标记为最近使用
                    self.cache.move_to_end(cache_key)
                    # 更新性能指标
                    self.performance_metrics['hits'] += 1
                    self.performance_metrics['total_operations'] += 1
                    self.performance_metrics['hit_rate'] = self.performance_metrics['hits'] / self.performance_metrics['total_operations']
                    return self.cache[cache_key]
                
                # 内存缓存中没有，尝试从磁盘缓存获取
                if self.disk_cache_enabled:
                    disk_pixmap = self._get_from_disk_cache(page_num, formatted_zoom)
                    if disk_pixmap:
                        # 更新磁盘缓存命中
                        self.performance_metrics['disk_cache_hits'] += 1
                        # 将磁盘缓存中的内容加载到内存缓存
                        self.cache[cache_key] = disk_pixmap
                        self.access_frequency[cache_key] = 1
                        self.cache.move_to_end(cache_key)
                        # 更新性能指标
                        self.performance_metrics['hits'] += 1
                        self.performance_metrics['total_operations'] += 1
                        self.performance_metrics['hit_rate'] = self.performance_metrics['hits'] / self.performance_metrics['total_operations']
                        return disk_pixmap
                    else:
                        self.performance_metrics['disk_cache_misses'] += 1
                
                # 更新性能指标
                self.performance_metrics['misses'] += 1
                self.performance_metrics['total_operations'] += 1
                self.performance_metrics['hit_rate'] = self.performance_metrics['hits'] / self.performance_metrics['total_operations']
                return None
            finally:
                self.cache_mutex.unlock()
        except Exception as e:
            self.logger.error(f"从缓存获取页面失败：{str(e)}")
            return None
    
    def _check_memory_usage(self):
        """检查当前内存使用百分比"""
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.performance_metrics['memory_usage'] = memory_percent
            return memory_percent
        except Exception as e:
            self.logger.error(f"检查内存使用失败：{str(e)}")
            return 0.0
    
    def _get_system_memory(self):
        """获取系统内存大小（MB）"""
        try:
            memory = psutil.virtual_memory()
            return memory.total / (1024 * 1024)  # 转换为MB
        except Exception as e:
            self.logger.error(f"获取系统内存失败：{str(e)}")
            return 4096  # 默认4GB
    
    def update_cache_size(self, pdf_file_size=None):
        """根据系统内存和PDF文件大小动态调整缓存大小
        
        参数：
        - pdf_file_size: int, PDF文件大小（字节），可选
        """
        try:
            # 更新PDF文件大小
            if pdf_file_size is not None:
                self.pdf_file_size = pdf_file_size
            
            # 获取当前内存使用情况
            memory_usage = self._check_memory_usage()
            
            # 计算可用内存比例
            available_memory_ratio = (100 - memory_usage) / 100
            
            # 根据PDF文件大小调整基础缓存大小
            # 小文件（< 10MB）：使用基础缓存大小
            # 中等文件（10MB-50MB）：使用基础缓存大小的1.5倍
            # 大文件（> 50MB）：使用基础缓存大小的2倍
            if self.pdf_file_size < 10 * 1024 * 1024:  # 10MB
                file_factor = 1.0
            elif self.pdf_file_size < 50 * 1024 * 1024:  # 50MB
                file_factor = 1.5
            else:
                file_factor = 2.0
            
            # 根据可用内存调整缓存大小
            # 可用内存 > 50%：使用计算出的缓存大小
            # 可用内存 30%-50%：使用计算出的缓存大小的0.8倍
            # 可用内存 < 30%：使用计算出的缓存大小的0.5倍
            if available_memory_ratio > 0.5:
                memory_factor = 1.0
            elif available_memory_ratio > 0.3:
                memory_factor = 0.8
            else:
                memory_factor = 0.5
            
            # 计算新的缓存大小
            new_max_size = int(self.base_max_size * file_factor * memory_factor)
            
            # 确保缓存大小在合理范围内
            min_size = 3  # 最小缓存大小
            max_size = 50  # 最大缓存大小
            new_max_size = max(min_size, min(new_max_size, max_size))
            
            # 如果缓存大小发生变化，记录日志
            if new_max_size != self.max_size:
                self.logger.info(f"动态调整缓存大小：{self.max_size} → {new_max_size}（PDF文件大小：{self.pdf_file_size / (1024 * 1024):.2f}MB，可用内存：{available_memory_ratio:.2f}）")
                self.max_size = new_max_size
                
                # 如果新的缓存大小小于当前缓存大小，清理超出部分
                if len(self.cache) > self.max_size:
                    excess = len(self.cache) - self.max_size
                    self.logger.info(f"清理超出缓存大小的{excess}个页面")
                    self._cleanup_cache_by_priority(excess)
        except Exception as e:
            self.logger.error(f"动态调整缓存大小失败：{str(e)}")
    
    def _cleanup_cache(self, cleanup_ratio=None):
        """清理缓存中最旧的项
        
        参数：
        - cleanup_ratio: float, 清理比例（0.0-1.0），默认为self.CACHE_CLEANUP_RATIO
        
        返回：
        - int: 清理的缓存项数量
        """
        try:
            self.cache_mutex.lock()
            try:
                ratio = cleanup_ratio or self.CACHE_CLEANUP_RATIO
                cache_size = len(self.cache)
                if cache_size == 0:
                    return 0
                
                # 计算清理数量，至少清理1项
                cleanup_count = max(1, int(cache_size * ratio))
                
                # 移除最旧的项
                removed = self._cleanup_cache_by_priority(cleanup_count)
                
                # 更新性能指标
                self.performance_metrics['cleanup_count'] += 1
                self.performance_metrics['last_cleanup_time'] = time.time()
                
                return removed
            finally:
                self.cache_mutex.unlock()
        except Exception as e:
            self.logger.error(f"清理缓存失败：{str(e)}")
            return 0
    
    def _cleanup_cache_by_priority(self, count):
        """根据优先级清理缓存项
        
        优先级规则：
        1. 访问频率低的优先清理
        2. 最近使用时间早的优先清理
        3. 页面大小大的优先清理
        
        参数：
        - count: int, 要清理的数量
        
        返回：
        - int: 实际清理的数量
        """
        if not self.cache or count <= 0:
            return 0
        
        # 构建缓存项优先级列表
        items_to_consider = []
        for key, value in self.cache.items():
            # 计算优先级分数（越低越优先清理）
            frequency = self.access_frequency.get(key, 0)
            # 页面大小（估算）
            page_size = self.page_sizes.get(key, 0)
            # 构建优先级元组 (frequency, -size, key)
            # 频率越低、大小越大越优先清理
            items_to_consider.append((frequency, -page_size, key))
        
        # 按优先级排序
        items_to_consider.sort()
        
        # 清理优先级最高的项
        removed = 0
        for _, _, key in items_to_consider[:count]:
            if key in self.cache:
                del self.cache[key]
                self.access_frequency.pop(key, None)
                self.page_sizes.pop(key, None)
                removed += 1
        
        return removed
    
    def add_page(self, page_num, zoom_level, pixmap):
        """添加页面到缓存
        
        参数：
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别
        - pixmap: QPixmap, 要缓存的QPixmap对象
        
        返回：
        - bool: 添加成功返回True，否则返回False
        """
        try:
            # 格式化缩放级别，确保一致性
            formatted_zoom = round(zoom_level * 100) / 100
            
            # 内存监控清理：根据内存使用情况自动清理缓存
            memory_usage = self._check_memory_usage()
            if memory_usage > self.MEMORY_WARNING_THRESHOLD:
                if memory_usage > self.MEMORY_CRITICAL_THRESHOLD:
                    self.logger.warning(f"内存使用达到临界值：{memory_usage}%，开始清理缓存")
                    self._cleanup_cache(self.CRITICAL_CLEANUP_RATIO)  # 临界状态清理
                else:
                    self.logger.warning(f"内存使用达到警告值：{memory_usage}%，开始清理缓存")
                    self._cleanup_cache()  # 警告状态清理默认比例
            
            self.cache_mutex.lock()
            try:
                cache_key = self._generate_cache_key(page_num, formatted_zoom)
                
                # 估算页面大小（基于像素数）
                if pixmap:
                    page_size = pixmap.width() * pixmap.height() * 3  # 假设RGB格式，每个像素3字节
                    self.page_sizes[cache_key] = page_size
                
                # 添加或更新缓存项
                self.cache[cache_key] = pixmap
                self.access_frequency[cache_key] = self.access_frequency.get(cache_key, 0) + 1
                self.cache.move_to_end(cache_key)
                
                # 超过最大大小则移除最旧项
                if len(self.cache) > self.max_size:
                    self._cleanup_cache_by_priority(len(self.cache) - self.max_size)
                
                # 更新性能指标
                self.performance_metrics['cache_size'] = len(self.cache)
                
                # 同时保存到磁盘缓存
                if self.disk_cache_enabled:
                    self._save_to_disk_cache(page_num, formatted_zoom, pixmap)
                
                return True
            finally:
                self.cache_mutex.unlock()
        except Exception as e:
            self.logger.error(f"添加页面到缓存失败：{str(e)}")
            return False
    
    def remove_page(self, page_num, zoom_level=None):
        """从缓存中移除页面
        
        参数：
        - page_num: int, 页面编号（从0开始）
        - zoom_level: float, 缩放级别，None表示移除该页面的所有缩放级别
        
        返回：
        - int: 移除的缓存项数量
        """
        try:
            # 格式化缩放级别，确保一致性
            formatted_zoom = None
            if zoom_level is not None:
                formatted_zoom = round(zoom_level * 100) / 100
            
            self.cache_mutex.lock()
            try:
                removed_count = 0
                
                if formatted_zoom is not None:
                    # 移除指定页面和缩放级别的缓存项
                    cache_key = self._generate_cache_key(page_num, formatted_zoom)
                    if cache_key in self.cache:
                        del self.cache[cache_key]
                        self.access_frequency.pop(cache_key, None)
                        self.page_sizes.pop(cache_key, None)
                        removed_count = 1
                    
                    # 同时从磁盘缓存移除
                    if self.disk_cache_enabled:
                        try:
                            disk_cache_key = self._generate_disk_cache_key(page_num, formatted_zoom)
                            disk_cache_path = os.path.join(self.disk_cache_dir, disk_cache_key)
                            if os.path.exists(disk_cache_path):
                                os.remove(disk_cache_path)
                        except:
                            pass
                else:
                    # 移除指定页面的所有缩放级别缓存。
                    # 使用 _generate_cache_key 的格式规则而非硬编码前缀，
                    # 避免键格式变更后前缀匹配失效。
                    # 键格式为 "{page_num}_{zoom:.2f}"，例如 "3_1.50"
                    # 通过检查前缀 "{page_num}_" 并验证后续部分符合浮点格式来精确匹配。
                    page_prefix = f"{page_num}_"
                    keys_to_remove = [
                        key for key in self.cache
                        if key.startswith(page_prefix)
                        and len(key) > len(page_prefix)
                        and key[len(page_prefix):].replace('.', '', 1).isdigit()
                    ]
                    for key in keys_to_remove:
                        del self.cache[key]
                        self.access_frequency.pop(key, None)
                        self.page_sizes.pop(key, None)
                    removed_count = len(keys_to_remove)
                
                # 更新性能指标
                self.performance_metrics['cache_size'] = len(self.cache)
                
                return removed_count
            finally:
                self.cache_mutex.unlock()
        except Exception as e:
            self.logger.error(f"从缓存移除页面失败：{str(e)}")
            return 0
    
    def clear(self):
        """
        清空缓存
        
        返回：
        - int: 清空的缓存项数量
        """
        try:
            self.cache_mutex.lock()
            try:
                cache_size = len(self.cache)
                self.cache.clear()
                self.access_frequency.clear()
                self.page_sizes.clear()
                
                # 同时清空磁盘缓存
                if self.disk_cache_enabled:
                    try:
                        disk_cache_size = 0
                        for filename in os.listdir(self.disk_cache_dir):
                            if filename.endswith('.cache'):
                                file_path = os.path.join(self.disk_cache_dir, filename)
                                try:
                                    os.remove(file_path)
                                    disk_cache_size += 1
                                except:
                                    pass
                    except Exception as e:
                        self.logger.error(f"清空磁盘缓存失败：{str(e)}")
                
                # 重置性能指标
                self.performance_metrics = {
                    'hits': 0,
                    'misses': 0,
                    'hit_rate': 0.0,
                    'total_operations': 0,
                    'cache_size': 0,
                    'memory_usage': self._check_memory_usage(),
                    'last_cleanup_time': time.time(),
                    'cleanup_count': 0,
                    'disk_cache_hits': 0,
                    'disk_cache_misses': 0
                }
                
                return cache_size
            finally:
                self.cache_mutex.unlock()
        except Exception as e:
            self.logger.error(f"清空缓存失败：{str(e)}")
            return 0
    
    def get_cache_size(self):
        """
        获取当前缓存大小
        
        返回：
        - int: 当前缓存项数量
        """
        try:
            self.cache_mutex.lock()
            try:
                return len(self.cache)
            finally:
                self.cache_mutex.unlock()
        except Exception as e:
            self.logger.error(f"获取缓存大小失败：{str(e)}")
            return 0
    
    def get_performance_metrics(self):
        """
        获取缓存性能指标
        
        返回：
        - dict: 性能指标字典
        """
        try:
            self.cache_mutex.lock()
            try:
                # 更新当前缓存大小
                self.performance_metrics['cache_size'] = len(self.cache)
                # 更新当前内存使用
                self.performance_metrics['memory_usage'] = self._check_memory_usage()
                return self.performance_metrics.copy()
            finally:
                self.cache_mutex.unlock()
        except Exception as e:
            self.logger.error(f"获取性能指标失败：{str(e)}")
            return {}
    
    def _generate_cache_key(self, page_num, zoom_level):
        """
        生成缓存键
        
        参数：
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        
        返回：
        - str: 缓存键
        """
        # 缩放级别格式化，与ZoomService保持一致
        formatted_zoom = round(zoom_level * 100) / 100
        zoom_level_str = f"{formatted_zoom:.2f}"
        return f"{page_num}_{zoom_level_str}"
    
    def _generate_disk_cache_key(self, page_num, zoom_level):
        """
        生成磁盘缓存键
        
        参数：
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        
        返回：
        - str: 磁盘缓存键（文件名）
        """
        # 使用哈希函数生成更紧凑的缓存键
        cache_key = self._generate_cache_key(page_num, zoom_level)
        hash_obj = hashlib.md5(cache_key.encode())
        return hash_obj.hexdigest() + ".cache"
    
    def _get_from_disk_cache(self, page_num, zoom_level):
        """
        从磁盘缓存获取页面
        
        参数：
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        
        返回：
        - QPixmap: 缓存的QPixmap对象，不存在则返回None
        """
        if not self.disk_cache_enabled:
            return None
        
        try:
            # 格式化缩放级别，确保一致性
            formatted_zoom = round(zoom_level * 100) / 100
            
            cache_key = self._generate_disk_cache_key(page_num, formatted_zoom)
            cache_path = os.path.join(self.disk_cache_dir, cache_key)
            
            if os.path.exists(cache_path):
                with open(cache_path, 'rb') as f:
                    # 读取图像数据
                    img_data = pickle.load(f)
                    # 从数据创建QImage
                    img = QImage.fromData(img_data)
                    if not img.isNull():
                        # 转换为QPixmap
                        pixmap = QPixmap.fromImage(img)
                        return pixmap
        except Exception as e:
            self.logger.error(f"从磁盘缓存获取页面失败：{str(e)}")
        
        return None
    
    def _save_to_disk_cache(self, page_num, zoom_level, pixmap):
        """
        将页面保存到磁盘缓存
        
        参数：
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        - pixmap: QPixmap, 要缓存的QPixmap对象
        
        返回：
        - bool: 保存成功返回True，否则返回False
        """
        if not self.disk_cache_enabled or pixmap is None:
            return False
        
        try:
            # 格式化缩放级别，确保一致性
            formatted_zoom = round(zoom_level * 100) / 100
            
            cache_key = self._generate_disk_cache_key(page_num, formatted_zoom)
            cache_path = os.path.join(self.disk_cache_dir, cache_key)
            
            # 检查磁盘缓存大小
            self._cleanup_disk_cache()
            
            # 将QPixmap转换为字节数据
            img = pixmap.toImage()
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.WriteOnly)
            success = img.save(buffer, 'PNG')
            if success:
                img_data = byte_array.data()
                # 保存到磁盘
                with open(cache_path, 'wb') as f:
                    pickle.dump(img_data, f)
                return True
        except Exception as e:
            self.logger.error(f"将页面保存到磁盘缓存失败：{str(e)}")
        
        return False
    
    def _cleanup_disk_cache(self):
        """清理磁盘缓存，保持在配置的大小范围内"""
        if not self.disk_cache_enabled:
            return
        
        try:
            # 获取所有缓存文件
            cache_files = []
            for filename in os.listdir(self.disk_cache_dir):
                if filename.endswith('.cache'):
                    file_path = os.path.join(self.disk_cache_dir, filename)
                    if os.path.exists(file_path):
                        try:
                            mtime = os.path.getmtime(file_path)
                            cache_files.append((mtime, file_path))
                        except:
                            pass
            
            # 按修改时间排序（ oldest first）
            cache_files.sort()
            
            # 清理超出大小的文件
            while len(cache_files) > self.disk_cache_size:
                _, file_path = cache_files.pop(0)
                try:
                    os.remove(file_path)
                except:
                    pass
        except Exception as e:
            self.logger.error(f"清理磁盘缓存失败：{str(e)}")
    
    def contains(self, page_num, zoom_level):
        """
        检查缓存中是否包含指定页面
        
        参数：
        - page_num: int, 页面编号
        - zoom_level: float, 缩放级别
        
        返回：
        - bool: 包含返回True，否则返回False
        """
        try:
            # 格式化缩放级别，确保一致性
            formatted_zoom = round(zoom_level * 100) / 100
            
            self.cache_mutex.lock()
            try:
                cache_key = self._generate_cache_key(page_num, formatted_zoom)
                return cache_key in self.cache
            finally:
                self.cache_mutex.unlock()
        except Exception as e:
            self.logger.error(f"检查缓存包含失败：{str(e)}")
            return False
    
    def preload_pages(self, doc, page_num, zoom_level, doc_mutex, preload_range=2):
        """
        预加载页面到缓存
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - page_num: int, 当前页面编号
        - zoom_level: float, 缩放级别
        - doc_mutex: QMutex, 文档访问锁
        - preload_range: int, 预加载范围，前后各preload_range页
        
        返回：
        - int: 预加载成功的页面数量
        """
        # 复用注入的渲染器；未注入时懒加载一次共享实例，避免每次调用都 new PageRenderer（泄漏线程池）
        if self._renderer is None:
            from business.page_renderer import PageRenderer
            self._renderer = PageRenderer()
        renderer = self._renderer
        
        try:
            # 格式化缩放级别，确保一致性
            formatted_zoom = round(zoom_level * 100) / 100
            
            preloaded = 0
            
            # 预加载当前页
            if not self.contains(page_num, formatted_zoom):
                pixmap = renderer.render_page(doc, page_num, formatted_zoom, doc_mutex)
                if pixmap:
                    self.add_page(page_num, formatted_zoom, pixmap)
                    preloaded += 1
            
            # 预加载前几页
            for i in range(1, preload_range + 1):
                prev_page = page_num - i
                if prev_page >= 0 and not self.contains(prev_page, formatted_zoom):
                    pixmap = renderer.render_page(doc, prev_page, formatted_zoom, doc_mutex)
                    if pixmap:
                        self.add_page(prev_page, formatted_zoom, pixmap)
                        preloaded += 1
            
            # 预加载后几页
            for i in range(1, preload_range + 1):
                next_page = page_num + i
                if next_page < len(doc) and not self.contains(next_page, formatted_zoom):
                    pixmap = renderer.render_page(doc, next_page, formatted_zoom, doc_mutex)
                    if pixmap:
                        self.add_page(next_page, formatted_zoom, pixmap)
                        preloaded += 1
            
            return preloaded
        except Exception as e:
            self.logger.error(f"预加载页面失败：{str(e)}")
            return 0
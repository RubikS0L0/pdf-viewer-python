#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PageCache优化测试

测试PageCache的优化功能，特别是智能缓存清理和性能监控
"""

import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 导入必要的模块
from business.page_cache import PageCache
from PyQt6.QtGui import QPixmap


class TestPageCacheOptimization:
    """PageCache优化测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        # 使用较小的缓存大小，避免内存问题
        self.page_cache = PageCache(max_size=5)
        # 创建一个模拟QPixmap对象
        self.test_pixmap = QPixmap(100, 100)
    
    def test_performance_metrics(self):
        """测试性能指标"""
        # 确保性能指标字典存在
        assert hasattr(self.page_cache, 'performance_metrics')
        assert self.page_cache.performance_metrics is not None
        
        # 初始状态检查
        assert self.page_cache.performance_metrics['hits'] == 0
        assert self.page_cache.performance_metrics['misses'] == 0
        assert self.page_cache.performance_metrics['cleanup_count'] == 0
    
    def test_cache_hit_miss(self):
        """测试缓存命中和未命中"""
        # 添加页面到缓存
        self.page_cache.add_page(0, 1.0, self.test_pixmap)
        
        # 第一次获取，应该命中
        pixmap1 = self.page_cache.get_page(0, 1.0)
        assert pixmap1 is not None
        assert self.page_cache.performance_metrics['hits'] == 1
        assert self.page_cache.performance_metrics['misses'] == 0
        
        # 获取不存在的页面，应该未命中
        pixmap2 = self.page_cache.get_page(1, 1.0)
        assert pixmap2 is None
        assert self.page_cache.performance_metrics['misses'] == 1
    
    def test_access_frequency_tracking(self):
        """测试访问频率跟踪"""
        # 添加页面到缓存
        self.page_cache.add_page(0, 1.0, self.test_pixmap)
        
        # 多次访问页面
        for i in range(5):
            self.page_cache.get_page(0, 1.0)
        
        # 检查访问频率（缓存键格式为"page_num_zoom_level"）
        cache_key = f"0_1.00"
        assert cache_key in self.page_cache.access_frequency
        assert self.page_cache.access_frequency[cache_key] >= 5
    
    def test_page_size_tracking(self):
        """测试页面大小跟踪"""
        # 添加页面到缓存
        self.page_cache.add_page(0, 1.0, self.test_pixmap)
        
        # 检查页面大小跟踪（缓存键格式为"page_num_zoom_level"）
        cache_key = f"0_1.00"
        assert cache_key in self.page_cache.page_sizes
        assert self.page_cache.page_sizes[cache_key] > 0
    
    def test_intelligent_cache_cleanup(self):
        """测试智能缓存清理"""
        # 添加多个页面到缓存
        for i in range(5):
            self.page_cache.add_page(i, 1.0, self.test_pixmap)
        
        # 访问其中一些页面，增加它们的访问频率
        for i in range(3):
            self.page_cache.get_page(2, 1.0)  # 访问页面2多次
            self.page_cache.get_page(3, 1.0)  # 访问页面3多次
        
        # 添加第6个页面，触发缓存清理
        self.page_cache.add_page(5, 1.0, self.test_pixmap)
        
        # 检查缓存大小
        assert self.page_cache.get_cache_size() == 5
        
        # 检查访问频率高的页面是否被保留
        assert self.page_cache.get_page(2, 1.0) is not None
        assert self.page_cache.get_page(3, 1.0) is not None
    
    def test_get_performance_metrics(self):
        """测试获取性能指标"""
        # 添加页面并访问
        self.page_cache.add_page(0, 1.0, self.test_pixmap)
        self.page_cache.get_page(0, 1.0)
        self.page_cache.get_page(1, 1.0)  # 未命中
        
        # 获取性能指标
        metrics = self.page_cache.get_performance_metrics()
        assert metrics is not None
        assert 'hits' in metrics
        assert 'misses' in metrics
        assert 'cleanup_count' in metrics
        assert 'hit_rate' in metrics
    
    def test_update_cache_size(self):
        """测试动态调整缓存大小"""
        # 初始缓存大小
        initial_size = self.page_cache.max_size
        
        # 模拟PDF文件大小
        pdf_file_size = 20 * 1024 * 1024  # 20MB
        
        # 动态调整缓存大小
        self.page_cache.update_cache_size(pdf_file_size)
        
        # 缓存大小应该有所调整
        assert self.page_cache.max_size >= initial_size

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PageCache单元测试

测试PageCache的核心功能
"""

import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 导入必要的模块
from business.page_cache import PageCache
from PyQt6.QtGui import QPixmap


class TestPageCache:
    """PageCache单元测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        # 使用较小的缓存大小，避免内存问题
        self.page_cache = PageCache(max_size=5)
        # 创建一个模拟QPixmap对象
        self.test_pixmap = QPixmap(100, 100)
    
    def test_initialization(self):
        """测试初始化"""
        assert self.page_cache is not None
        assert self.page_cache.get_cache_size() == 0
    
    def test_add_page_and_get_page(self):
        """测试添加页面和获取页面"""
        # 添加页面到缓存
        success = self.page_cache.add_page(0, 1.0, self.test_pixmap)
        assert success
        assert self.page_cache.get_cache_size() == 1
        
        # 从缓存获取页面
        cached_pixmap = self.page_cache.get_page(0, 1.0)
        assert cached_pixmap is not None
    
    def test_add_page_exceeds_max_size(self):
        """测试添加页面超过最大大小"""
        # 添加6个页面到缓存（最大大小为5）
        for i in range(6):
            success = self.page_cache.add_page(i, 1.0, self.test_pixmap)
            assert success
        
        # 缓存大小应该为5
        assert self.page_cache.get_cache_size() == 5
        
        # 第一个页面应该被移除
        assert self.page_cache.get_page(0, 1.0) is None
        # 最后一个页面应该存在
        assert self.page_cache.get_page(5, 1.0) is not None
    
    def test_remove_page(self):
        """测试移除页面"""
        # 添加页面到缓存
        self.page_cache.add_page(0, 1.0, self.test_pixmap)
        self.page_cache.add_page(0, 2.0, self.test_pixmap)
        assert self.page_cache.get_cache_size() == 2
        
        # 移除指定页面和缩放级别的缓存项
        removed = self.page_cache.remove_page(0, 1.0)
        assert removed == 1
        assert self.page_cache.get_cache_size() == 1
        assert self.page_cache.get_page(0, 1.0) is None
        assert self.page_cache.get_page(0, 2.0) is not None
        
        # 移除指定页面的所有缩放级别的缓存项
        removed = self.page_cache.remove_page(0)
        assert removed == 1
        assert self.page_cache.get_cache_size() == 0
        assert self.page_cache.get_page(0, 2.0) is None
    
    def test_clear(self):
        """测试清空缓存"""
        # 添加页面到缓存
        for i in range(3):
            self.page_cache.add_page(i, 1.0, self.test_pixmap)
        assert self.page_cache.get_cache_size() == 3
        
        # 清空缓存
        cleared = self.page_cache.clear()
        assert cleared == 3
        assert self.page_cache.get_cache_size() == 0
    
    def test_contains(self):
        """测试缓存包含"""
        # 添加页面到缓存
        self.page_cache.add_page(0, 1.0, self.test_pixmap)
        
        # 测试包含
        assert self.page_cache.contains(0, 1.0)
        assert not self.page_cache.contains(0, 2.0)
        assert not self.page_cache.contains(1, 1.0)

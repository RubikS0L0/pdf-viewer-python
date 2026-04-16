#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PageRenderer单元测试

测试PageRenderer的核心功能
"""

import pytest
from business.page_renderer import PageRenderer


class TestPageRenderer:
    """PageRenderer单元测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.page_renderer = PageRenderer(max_workers=2)
    
    def teardown_method(self):
        """清理测试环境"""
        self.page_renderer.shutdown()
    
    def test_initialization(self):
        """测试初始化"""
        assert self.page_renderer is not None
    
    def test_render_page_with_none_doc(self):
        """测试渲染None文档"""
        result = self.page_renderer.render_page(None, 0, 1.0, None)
        assert result is None
    
    def test_render_page_with_invalid_page_num(self):
        """测试渲染无效页码"""
        # 创建一个模拟文档对象
        class MockDoc:
            def __len__(self):
                return 5
        
        mock_doc = MockDoc()
        result = self.page_renderer.render_page(mock_doc, 10, 1.0, None)
        assert result is None
    
    def test_render_page_to_image_with_none_doc(self):
        """测试渲染None文档为图像"""
        result = self.page_renderer.render_page_to_image(None, 0, 1.0, None)
        assert result is None
    
    def test_get_page_size_with_none_doc(self):
        """测试获取None文档的页面尺寸"""
        result = self.page_renderer.get_page_size(None, 0, 1.0, None)
        assert result == (0, 0)
    
    def test_get_page_size_with_invalid_page_num(self):
        """测试获取无效页码的页面尺寸"""
        # 创建一个模拟文档对象
        class MockDoc:
            def __len__(self):
                return 5
        
        mock_doc = MockDoc()
        result = self.page_renderer.get_page_size(mock_doc, 10, 1.0, None)
        assert result == (0, 0)
    
    def test_queue_progressive_render(self):
        """测试队列渐进式渲染"""
        # 创建一个模拟文档对象
        class MockDoc:
            def __len__(self):
                return 5
        
        mock_doc = MockDoc()
        
        def callback(page_num, result, is_final=False):
            pass
        
        # 测试方法是否能正常调用
        request_id = self.page_renderer.queue_progressive_render(mock_doc, 0, 1.0, None, 0, callback)
        assert request_id is not None
    
    def test_batch_render(self):
        """测试批量渲染"""
        # 创建一个模拟文档对象
        class MockDoc:
            def __len__(self):
                return 5
        
        mock_doc = MockDoc()
        
        def callback(page_num, result):
            pass
        
        # 测试方法是否能正常调用
        request_ids = self.page_renderer.batch_render(mock_doc, [0, 1, 2], 1.0, None, 0, callback)
        assert isinstance(request_ids, list)
        assert len(request_ids) == 3
    
    def test_cancel_render(self):
        """测试取消渲染"""
        # 测试方法是否能正常调用
        try:
            self.page_renderer.cancel_render(0, 1.0)
        except Exception:
            pytest.fail("cancel_render方法抛出异常")

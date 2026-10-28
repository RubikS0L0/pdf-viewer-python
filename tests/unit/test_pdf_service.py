#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDFService单元测试

测试PDFService的核心功能
"""

import os
import tempfile

import pytest
import fitz
from services.pdf_service import PDFService
from PyQt6.QtGui import QPixmap


class TestPDFService:
    """PDFService单元测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        # 创建模拟对象
        class MockPDFManager:
            def __init__(self):
                self.is_open = False
                self.page_count = 0
                self.file_path = None
                self.doc = None
                self.doc_mutex = None
            
            def open(self, file_path):
                self.is_open = True
                self.page_count = 5
                self.file_path = file_path
                return True
            
            def close(self):
                self.is_open = False
                self.page_count = 0
                self.file_path = None
                return True
            
            def get_document(self):
                return self.doc
            
            def get_document_mutex(self):
                return self.doc_mutex
            
            def get_file_path(self):
                return self.file_path
        
        class MockPageCache:
            def __init__(self):
                self.cache = {}
            
            def get_page(self, page_num, zoom_level):
                return self.cache.get((page_num, zoom_level))
            
            def add_page(self, page_num, zoom_level, pixmap):
                self.cache[(page_num, zoom_level)] = pixmap
                return True
            
            def clear(self):
                self.cache.clear()
                return len(self.cache)
            
            def preload_pages(self, doc, page_num, zoom_level, doc_mutex, preload_range=2):
                return preload_range * 2
        
        # 创建模拟实例
        self.mock_pdf_manager = MockPDFManager()
        self.mock_page_cache = MockPageCache()
        
        # 创建PDFService实例，注入 mock 的 pdf_processor：
        # PDFProcessor 使用 multiprocessing，Windows 单元测试环境（非主脚本）会递归 spawn；单元测试不应真实渲染
        class _MockPDFProcessor:
            def render_page(self, pdf_path, page_num, dpi=96):
                return ("C:/nonexistent.png", (612, 792))
            def get_page_size(self, pdf_path, page_num, dpi=96):
                return (612, 792)
            def clear_cache(self, file_path):
                return None
            def shutdown(self):
                return None
        self.pdf_service = PDFService(
            self.mock_pdf_manager,
            self.mock_page_cache,
            pdf_processor=_MockPDFProcessor()
        )

        # 创建临时有效PDF文件，满足PDFService.open_document的文件验证（扩展名+魔数）
        fd, self.tmp_pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        doc = fitz.open()
        doc.new_page(width=612, height=792)
        doc.save(self.tmp_pdf_path)
        doc.close()
        self.test_pdf = self.tmp_pdf_path

    def teardown_method(self):
        """清理测试环境"""
        if hasattr(self, 'tmp_pdf_path') and os.path.exists(self.tmp_pdf_path):
            os.remove(self.tmp_pdf_path)
    
    def test_initialization(self):
        """测试初始化"""
        assert self.pdf_service is not None
    
    def test_open_document(self):
        """测试打开文档"""
        # 打开文档
        success = self.pdf_service.open_document(self.test_pdf)
        assert success
        assert self.mock_pdf_manager.is_open
        assert self.pdf_service.get_page_count() == 5
        assert self.pdf_service.get_document_path() == self.test_pdf
    
    def test_close_document(self):
        """测试关闭文档"""
        # 先打开文档
        self.pdf_service.open_document(self.test_pdf)
        assert self.mock_pdf_manager.is_open
        
        # 关闭文档
        success = self.pdf_service.close_document()
        assert success
        assert not self.mock_pdf_manager.is_open
    
    def test_is_document_open(self):
        """测试文档是否打开"""
        # 文档未打开
        assert not self.pdf_service.is_document_open()
        
        # 打开文档
        self.pdf_service.open_document(self.test_pdf)
        assert self.pdf_service.is_document_open()
    
    def test_get_page_count(self):
        """测试获取文档页数"""
        # 文档未打开
        assert self.pdf_service.get_page_count() == 0
        
        # 打开文档
        self.pdf_service.open_document(self.test_pdf)
        assert self.pdf_service.get_page_count() == 5
    
    def test_render_page(self):
        """测试渲染页面"""
        # 打开文档
        self.pdf_service.open_document(self.test_pdf)
        
        # 渲染页面
        pixmap = self.pdf_service.render_page(0)
        assert pixmap is not None
    
    def test_get_page_size(self):
        """测试获取页面尺寸"""
        # 打开文档
        self.pdf_service.open_document(self.test_pdf)
        
        # 获取页面尺寸
        page_size = self.pdf_service.get_page_size(0)
        assert page_size == (612, 792)
    
    def test_preload_pages(self):
        """测试预加载页面"""
        # 打开文档
        self.pdf_service.open_document(self.test_pdf)
        
        # 预加载页面
        preloaded = self.pdf_service.preload_pages(2, preload_range=2)
        assert preloaded == 5  # 含当前页共5页（0~4）
    
    def test_render_page_without_open(self):
        """测试渲染未打开的文档"""
        # 文档未打开，渲染应该返回None
        pixmap = self.pdf_service.render_page(0)
        assert pixmap is None
    
    def test_get_page_size_without_open(self):
        """测试获取未打开文档的页面尺寸"""
        # 文档未打开，应该返回(0, 0)
        page_size = self.pdf_service.get_page_size(0)
        assert page_size == (0, 0)
    
    def test_preload_pages_without_open(self):
        """测试预加载未打开文档的页面"""
        # 文档未打开，应该返回0
        preloaded = self.pdf_service.preload_pages(2)
        assert preloaded == 0

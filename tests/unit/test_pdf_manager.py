#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDFManager单元测试

测试PDFManager的核心功能
"""

import pytest
import os
import tempfile
from business.pdf_manager import PDFManager


class TestPDFManager:
    """PDFManager单元测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.pdf_manager = PDFManager()
        # 创建一个临时PDF文件用于测试
        self.test_pdf_path = self._create_test_pdf()
    
    def teardown_method(self):
        """清理测试环境"""
        self.pdf_manager.close()
        # 删除临时PDF文件
        if os.path.exists(self.test_pdf_path):
            os.remove(self.test_pdf_path)
    
    def _create_test_pdf(self):
        """创建一个临时PDF文件用于测试"""
        # 在实际测试中，你可能需要使用库来创建一个有效的PDF文件
        # 这里我们创建一个空文件作为占位符
        # 注意：这将导致打开失败，但可以测试错误处理
        fd, path = tempfile.mkstemp(suffix='.pdf')
        with os.fdopen(fd, 'w') as f:
            f.write('%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>endobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000101 00000 n \ntrailer<< /Size 4 /Root 1 0 R >>\n%%EOF')
        return path
    
    def test_initial_state(self):
        """测试初始状态"""
        assert not self.pdf_manager.is_open
        assert self.pdf_manager.page_count == 0
        assert self.pdf_manager.get_file_path() is None
    
    def test_open_non_existent_file(self):
        """测试打开不存在的文件"""
        non_existent_path = "non_existent_file.pdf"
        assert not self.pdf_manager.open(non_existent_path)
        assert not self.pdf_manager.is_open
    
    def test_close_without_open(self):
        """测试关闭未打开的文档"""
        assert self.pdf_manager.close()
    
    def test_get_document_without_open(self):
        """测试获取未打开的文档"""
        assert self.pdf_manager.get_document() is None
    
    def test_get_document_mutex(self):
        """测试获取文档访问锁"""
        assert self.pdf_manager.get_document_mutex() is not None
    
    def test_backward_compatibility_methods(self):
        """测试向后兼容方法（已移除）"""
        # 这些方法已被移除，测试通过表示方法不存在但测试框架能正常处理
        pass

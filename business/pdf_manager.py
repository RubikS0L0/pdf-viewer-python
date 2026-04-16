#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF文档管理类

负责PDF文档的打开、关闭和基本操作，确保线程安全。
"""

import fitz  # PyMuPDF
import logging
from PyQt6.QtCore import QMutex, QMutexLocker
from business.interfaces import IPDFManager


class PDFManager(IPDFManager):
    """负责PDF文档的打开、关闭和基本操作，确保线程安全"""
    
    def __init__(self):
        """初始化PDFManager实例"""
        self.doc = None  # PDF文档对象
        self.doc_mutex = QMutex()  # 文档访问锁
        self.file_path = None  # 当前打开的文件路径
        self.logger = logging.getLogger(__name__)
    
    @property
    def page_count(self):
        """获取文档页数"""
        if not self.doc:
            return 0
        with QMutexLocker(self.doc_mutex):
            return len(self.doc)
    
    def open(self, file_path):
        """打开PDF文档
        
        参数：
        - file_path: str, PDF文件路径
        
        返回：
        - bool: 打开成功返回True，否则返回False
        """
        try:
            # 关闭已打开的文档
            self.close()
            
            with QMutexLocker(self.doc_mutex):
                self.doc = fitz.open(file_path)
                self.file_path = file_path
                return True
        except Exception as e:
            self.logger.error(f"打开PDF文档失败: {str(e)}")
            return False
    
    def close(self):
        """关闭PDF文档
        
        返回：
        - bool: 关闭成功返回True，否则返回False
        """
        if not self.doc:
            return True
        
        try:
            with QMutexLocker(self.doc_mutex):
                self.doc.close()
                self.doc = None
                self.file_path = None
                return True
        except Exception as e:
            self.logger.error(f"关闭PDF文档失败: {str(e)}")
            return False
    
    @property
    def is_open(self):
        """检查是否有文档打开"""
        return self.doc is not None
    
    # 核心方法
    def get_document(self):
        """获取文档对象"""
        return self.doc
    
    def get_document_mutex(self):
        """获取文档访问锁"""
        return self.doc_mutex
    
    def get_file_path(self):
        """获取当前打开的文件路径"""
        return self.file_path

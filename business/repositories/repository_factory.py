"""
Repository 工厂

用于创建和管理 Repository 实例。
"""

import logging
from typing import Optional, Type

from .pdf_repository import IPDFRepository
from .pymupdf_repository import PyMuPDFRepository


class PDFRepositoryFactory:
    """
    PDF Repository 工厂
    
    管理 Repository 实例的创建和生命周期。
    """
    
    _instance = None
    _repository_class: Type[IPDFRepository] = PyMuPDFRepository
    _repository: Optional[IPDFRepository] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
    
    @classmethod
    def set_repository_class(cls, repository_class: Type[IPDFRepository]):
        """
        设置使用的 Repository 类
        
        用于切换不同的 PDF 引擎实现。
        
        参数:
            repository_class: Repository 类
        """
        cls._repository_class = repository_class
        cls._repository = None  # 重置实例
    
    @classmethod
    def get_repository(cls) -> IPDFRepository:
        """
        获取 Repository 实例
        
        使用单例模式，确保只有一个 Repository 实例。
        
        返回:
            IPDFRepository 实例
        """
        if cls._repository is None:
            cls._repository = cls._repository_class()
        return cls._repository
    
    @classmethod
    def reset(cls):
        """重置工厂状态"""
        cls._repository = None
        cls._repository_class = PyMuPDFRepository

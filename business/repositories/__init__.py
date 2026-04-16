"""
Repository 层

抽象 PDF 文档操作，解耦业务逻辑与具体的 PDF 库实现。
便于未来更换 PDF 引擎（如从 PyMuPDF 切换到 pdfium）。

使用 Repository 模式：
- IPDFRepository: 抽象接口
- PyMuPDFRepository: PyMuPDF 实现
- PDFRepositoryFactory: 工厂类
"""

from .pdf_repository import (
    IPDFRepository, PDFDocument, PDFPage, PDFMetadata,
    RenderOptions, RenderResult
)
from .pymupdf_repository import PyMuPDFRepository
from .repository_factory import PDFRepositoryFactory

__all__ = [
    'IPDFRepository',
    'PDFDocument',
    'PDFPage',
    'PDFMetadata',
    'RenderOptions',
    'RenderResult',
    'PyMuPDFRepository',
    'PDFRepositoryFactory',
]

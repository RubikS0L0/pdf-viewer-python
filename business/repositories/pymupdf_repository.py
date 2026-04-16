"""
PyMuPDF Repository 实现

使用 PyMuPDF (fitz) 库实现 PDFRepository 接口。
"""

import fitz  # PyMuPDF
import os
import logging
from typing import List, Tuple, Optional, BinaryIO
import io

from .pdf_repository import (
    IPDFRepository, PDFDocument, PDFPage, PDFMetadata,
    RenderOptions, RenderResult
)


class PyMuPDFDocument(PDFDocument):
    """PyMuPDF 文档实现"""
    
    def __init__(self, file_path: str, doc: fitz.Document):
        super().__init__(file_path)
        self._doc = doc
        self._logger = logging.getLogger(__name__)
    
    @property
    def is_open(self) -> bool:
        """文档是否已打开"""
        return self._doc is not None and not self._doc.is_closed
    
    @property
    def page_count(self) -> int:
        """页面数量"""
        if not self.is_open:
            return 0
        return len(self._doc)
    
    def get_metadata(self) -> PDFMetadata:
        """获取文档元数据"""
        if not self.is_open:
            return PDFMetadata()
        
        meta = self._doc.metadata
        return PDFMetadata(
            title=meta.get('title', ''),
            author=meta.get('author', ''),
            subject=meta.get('subject', ''),
            creator=meta.get('creator', ''),
            producer=meta.get('producer', ''),
            creation_date=meta.get('creationDate', ''),
            modification_date=meta.get('modDate', ''),
            page_count=self.page_count,
            file_size=os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0,
        )
    
    def get_page(self, page_number: int) -> PDFPage:
        """获取页面信息"""
        if not self.is_open:
            raise RuntimeError("文档未打开")
        
        if page_number < 0 or page_number >= self.page_count:
            raise ValueError(f"页码超出范围: {page_number}")
        
        page = self._doc.load_page(page_number)
        rect = page.rect
        
        return PDFPage(
            page_number=page_number,
            width=rect.width,
            height=rect.height,
            rotation=page.rotation,
        )
    
    def render_page(self, page_number: int, options: RenderOptions) -> RenderResult:
        """渲染页面"""
        if not self.is_open:
            raise RuntimeError("文档未打开")
        
        if page_number < 0 or page_number >= self.page_count:
            raise ValueError(f"页码超出范围: {page_number}")
        
        page = self._doc.load_page(page_number)
        
        # 计算变换矩阵
        mat = fitz.Matrix(*options.get_matrix())
        
        # 渲染
        if options.clip_rect:
            clip = fitz.Rect(*options.clip_rect)
            pix = page.get_pixmap(matrix=mat, clip=clip)
        else:
            pix = page.get_pixmap(matrix=mat)
        
        # 转换为 RGB 格式
        if options.grayscale:
            pix = fitz.Pixmap(fitz.csGRAY, pix)
        else:
            if pix.n > 3:  # CMYK: convert to RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
        
        return RenderResult(
            width=pix.width,
            height=pix.height,
            stride=pix.stride,
            samples=pix.samples,
            format="RGB" if not options.grayscale else "GRAY",
        )
    
    def extract_text(self, page_number: int) -> str:
        """提取页面文本"""
        if not self.is_open:
            raise RuntimeError("文档未打开")
        
        if page_number < 0 or page_number >= self.page_count:
            raise ValueError(f"页码超出范围: {page_number}")
        
        page = self._doc.load_page(page_number)
        return page.get_text()
    
    def search_text(self, query: str, page_number: Optional[int] = None) -> List[Tuple[int, Tuple[float, float, float, float]]]:
        """搜索文本"""
        if not self.is_open:
            raise RuntimeError("文档未打开")
        
        results = []
        
        if page_number is not None:
            # 搜索指定页面
            if 0 <= page_number < self.page_count:
                page = self._doc.load_page(page_number)
                rects = page.search_for(query)
                for rect in rects:
                    results.append((page_number, (rect.x0, rect.y0, rect.x1, rect.y1)))
        else:
            # 搜索所有页面
            for i in range(self.page_count):
                page = self._doc.load_page(i)
                rects = page.search_for(query)
                for rect in rects:
                    results.append((i, (rect.x0, rect.y0, rect.x1, rect.y1)))
        
        return results
    
    def close(self) -> None:
        """关闭文档"""
        if self._doc and not self._doc.is_closed:
            self._doc.close()
            self._doc = None


class PyMuPDFRepository(IPDFRepository):
    """PyMuPDF Repository 实现"""
    
    # PDF 文件魔数
    PDF_MAGIC = b'%PDF-'
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
    
    def open(self, file_path: str) -> PDFDocument:
        """打开 PDF 文档"""
        # 验证文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 验证文件格式
        if not self.validate(file_path):
            raise ValueError(f"不是有效的 PDF 文件: {file_path}")
        
        try:
            doc = fitz.open(file_path)
            return PyMuPDFDocument(file_path, doc)
        except Exception as e:
            self._logger.error(f"打开 PDF 失败: {e}")
            raise RuntimeError(f"打开 PDF 失败: {e}")
    
    def open_from_bytes(self, data: bytes) -> PDFDocument:
        """从字节数据打开 PDF 文档"""
        try:
            stream = io.BytesIO(data)
            doc = fitz.open(stream=stream, filetype="pdf")
            return PyMuPDFDocument("<memory>", doc)
        except Exception as e:
            self._logger.error(f"从字节数据打开 PDF 失败: {e}")
            raise RuntimeError(f"从字节数据打开 PDF 失败: {e}")
    
    def validate(self, file_path: str) -> bool:
        """验证文件是否为有效的 PDF"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(5)
                return header.startswith(self.PDF_MAGIC)
        except Exception as e:
            self._logger.warning(f"验证文件失败: {e}")
            return False
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式"""
        return ['.pdf', '.xps', '.epub', '.fb2', '.cbz']

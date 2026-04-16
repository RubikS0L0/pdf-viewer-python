"""
PDF Repository 抽象接口

定义 PDF 文档操作的标准接口，与具体实现解耦。
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict, Any, BinaryIO
from dataclasses import dataclass
from enum import Enum
import io


@dataclass
class PDFMetadata:
    """PDF 元数据"""
    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""
    producer: str = ""
    creation_date: str = ""
    modification_date: str = ""
    page_count: int = 0
    file_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'title': self.title,
            'author': self.author,
            'subject': self.subject,
            'creator': self.creator,
            'producer': self.producer,
            'creation_date': self.creation_date,
            'modification_date': self.modification_date,
            'page_count': self.page_count,
            'file_size': self.file_size,
        }


@dataclass
class PDFPage:
    """PDF 页面信息"""
    page_number: int
    width: float
    height: float
    rotation: int = 0
    
    def get_size_at_dpi(self, dpi: float = 72.0) -> Tuple[int, int]:
        """
        获取指定 DPI 下的页面尺寸（像素）
        
        参数:
            dpi: 目标 DPI
            
        返回:
            (width, height) 像素尺寸
        """
        scale = dpi / 72.0
        return int(self.width * scale), int(self.height * scale)


@dataclass
class RenderOptions:
    """渲染选项"""
    dpi: float = 72.0
    zoom: float = 1.0
    rotation: int = 0
    clip_rect: Optional[Tuple[float, float, float, float]] = None  # (x0, y0, x1, y1)
    grayscale: bool = False
    
    def get_matrix(self) -> Tuple[float, float, float, float, float, float]:
        """
        获取变换矩阵
        
        返回:
            (a, b, c, d, e, f) 变换矩阵
        """
        scale = self.dpi / 72.0 * self.zoom
        return (scale, 0, 0, scale, 0, 0)


@dataclass
class RenderResult:
    """渲染结果"""
    width: int
    height: int
    stride: int
    samples: bytes
    format: str = "RGB"  # RGB, RGBA, GRAY, etc.
    
    def to_image_data(self) -> bytes:
        """获取图像数据"""
        return self.samples


class PDFDocument(ABC):
    """PDF 文档抽象基类"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._metadata: Optional[PDFMetadata] = None
    
    @property
    @abstractmethod
    def is_open(self) -> bool:
        """文档是否已打开"""
        pass
    
    @property
    @abstractmethod
    def page_count(self) -> int:
        """页面数量"""
        pass
    
    @abstractmethod
    def get_metadata(self) -> PDFMetadata:
        """获取文档元数据"""
        pass
    
    @abstractmethod
    def get_page(self, page_number: int) -> PDFPage:
        """
        获取页面信息
        
        参数:
            page_number: 页码（从0开始）
            
        返回:
            PDFPage 对象
        """
        pass
    
    @abstractmethod
    def render_page(self, page_number: int, options: RenderOptions) -> RenderResult:
        """
        渲染页面
        
        参数:
            page_number: 页码（从0开始）
            options: 渲染选项
            
        返回:
            RenderResult 对象
        """
        pass
    
    @abstractmethod
    def extract_text(self, page_number: int) -> str:
        """
        提取页面文本
        
        参数:
            page_number: 页码（从0开始）
            
        返回:
            页面文本内容
        """
        pass
    
    @abstractmethod
    def search_text(self, query: str, page_number: Optional[int] = None) -> List[Tuple[int, Tuple[float, float, float, float]]]:
        """
        搜索文本
        
        参数:
            query: 搜索关键词
            page_number: 指定页码，None表示搜索全部
            
        返回:
            [(page_number, (x0, y0, x1, y1)), ...]
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭文档"""
        pass
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


class IPDFRepository(ABC):
    """
    PDF Repository 抽象接口
    
    定义 PDF 文档的存储和访问接口。
    """
    
    @abstractmethod
    def open(self, file_path: str) -> PDFDocument:
        """
        打开 PDF 文档
        
        参数:
            file_path: 文件路径
            
        返回:
            PDFDocument 对象
            
        抛出:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式无效
            RuntimeError: 打开失败
        """
        pass
    
    @abstractmethod
    def open_from_bytes(self, data: bytes) -> PDFDocument:
        """
        从字节数据打开 PDF 文档
        
        参数:
            data: PDF 文件字节数据
            
        返回:
            PDFDocument 对象
        """
        pass
    
    @abstractmethod
    def validate(self, file_path: str) -> bool:
        """
        验证文件是否为有效的 PDF
        
        参数:
            file_path: 文件路径
            
        返回:
            是否有效
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        返回:
            文件扩展名列表，如 ['.pdf', '.xps']
        """
        pass

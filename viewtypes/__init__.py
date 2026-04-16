"""
浏览视图类型模块包

功能：
- 定义PDF浏览器的各种浏览视图类型接口
- 实现单页浏览、单页连续浏览、双页浏览、双页连续浏览等视图类型
- 提供视图类型管理和切换功能
- 处理不同视图类型下的页面显示和交互逻辑

开发环境：
- Python 3.14
- Windows系统

核心依赖：
- PyQt5：GUI界面组件
- abc：抽象基类支持

创建时间：2026-01-16
更新时间：2026-01-23
"""

# viewtypes包初始化文件

from .base import BrowsingViewtype
from .single_page_viewtype import SinglePageViewtype
from .single_page_continuous_viewtype import SinglePageContinuousViewtype
from .two_page_viewtype import TwoPageViewtype
from .two_page_continuous_viewtype import TwoPageContinuousViewtype
from .manager import ViewtypeManager

__all__ = [
    'BrowsingViewtype',
    'SinglePageViewtype',
    'SinglePageContinuousViewtype',
    'TwoPageViewtype',
    'TwoPageContinuousViewtype',
    'ViewtypeManager'
]
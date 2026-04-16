#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
业务逻辑接口包

定义所有核心业务逻辑的接口
"""

from .ipdf_manager import IPDFManager
from .ipage_renderer import IPageRenderer
from .ipage_cache import IPageCache
from .izoom_manager import IZoomManager

__all__ = [
    "IPDFManager",
    "IPageRenderer",
    "IPageCache",
    "IZoomManager"
]

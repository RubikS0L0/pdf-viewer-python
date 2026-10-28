#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
依赖注入容器配置

使用成熟的Dependency Injector库实现依赖注入
"""

import logging
from dependency_injector import containers, providers

from business.pdf_manager import PDFManager
from business.page_renderer import PageRenderer
from business.page_cache import PageCache
from services.zoom_service import ZoomService
from services.pdf_service import PDFService
from services.viewtype_service import ViewtypeService


class Container(containers.DeclarativeContainer):
    """依赖注入容器"""
    
    # 配置
    config = providers.Configuration()
    
    # 核心业务逻辑类
    pdf_manager = providers.Singleton(PDFManager)
    page_renderer = providers.Singleton(PageRenderer)
    page_cache = providers.Singleton(PageCache, renderer=page_renderer)
    
    # 服务类
    zoom_service = providers.Singleton(ZoomService)
    
    # PDF服务
    pdf_service = providers.Singleton(
        PDFService,
        pdf_manager=pdf_manager,
        page_cache=page_cache
    )
    
    # 视图类型服务
    viewtype_service = providers.Factory(
        ViewtypeService,
        pdf_viewer=providers.Dependency()
    )


# 创建全局容器实例
container = Container()



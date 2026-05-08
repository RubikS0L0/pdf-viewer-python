#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF浏览器主程序入口

功能：
- 启动PDF浏览器应用
- 初始化主窗口
- 处理应用程序事件循环

开发环境：
- Python 3.14
- Windows系统

核心依赖：
- PyQt6：GUI界面实现
- logging：日志记录
"""

import sys
import os
import logging

from PyQt6.QtWidgets import QApplication

# 配置日志
_log_level = os.environ.get('PDF_LOG_LEVEL', 'ERROR').upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.ERROR),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('pdf_viewer.log'), logging.StreamHandler()]
)

# 获取模块级别的logger
logger = logging.getLogger(__name__)

# 导入异常处理模块
from utils.exception_handler import handle_exception, ResourceManager

# 导入主窗口类
from ui.pdf_main_window import PDFMainWindow

if __name__ == '__main__':
    """应用程序入口点"""
    resource_manager = ResourceManager()
    
    try:
        # 初始化依赖注入容器
        # 创建应用程序实例
        app = resource_manager.register(QApplication(sys.argv))
        
        # 创建主窗口实例
        window = PDFMainWindow()
        
        # 显示主窗口
        window.show()
        
        # 启动应用程序事件循环
        try:
            sys.exit(app.exec())
        finally:
            # 应用程序退出时关闭所有线程池
            try:
                from services.thread_pool_manager import thread_pool_manager
                thread_pool_manager.shutdown()
                
                # 关闭PDF处理器
                from utils.di_container import container
                pdf_service = container.pdf_service()
                if hasattr(pdf_service, 'pdf_processor'):
                    pdf_service.pdf_processor.shutdown()
                    
                logging.info("所有线程池和PDF处理器已关闭")
            except Exception as e:
                handle_exception(e, logger, {"action": "shutdown_resources"})
    except FileNotFoundError as e:
        error_info = handle_exception(e, logger, {"action": "start_application"})
        print(f"应用程序启动失败: {error_info.message}")
        sys.exit(1)
    except PermissionError as e:
        error_info = handle_exception(e, logger, {"action": "start_application"})
        print(f"应用程序启动失败: {error_info.message}")
        sys.exit(1)
    except ImportError as e:
        error_info = handle_exception(e, logger, {"action": "start_application"})
        print(f"应用程序启动失败: {error_info.message}")
        sys.exit(1)
    except Exception as e:
        error_info = handle_exception(e, logger, {"action": "start_application"})
        print(f"应用程序启动失败: {error_info.message}")
        sys.exit(1)

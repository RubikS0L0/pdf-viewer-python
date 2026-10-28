#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试配置文件

用于配置测试环境，提供测试夹具
"""

import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session", autouse=True)
def qapplication():
    """为整个测试会话提供 QApplication 实例。

    PyQt6 中创建 QPixmap/QImage 等对象必须先有 QApplication 实例，
    否则会触发 native crash。统一在此创建，供所有测试复用。
    """
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    print("设置测试环境...")
    # 在这里可以添加测试环境的设置代码
    yield
    print("清理测试环境...")
    # 在这里可以添加测试环境的清理代码

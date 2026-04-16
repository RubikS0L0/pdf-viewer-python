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

from utils.dependency_injector import injector


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    print("设置测试环境...")
    # 在这里可以添加测试环境的设置代码
    yield
    print("清理测试环境...")
    # 在这里可以添加测试环境的清理代码
    injector.clear()


@pytest.fixture(scope="function")
def reset_injector():
    """重置依赖注入容器"""
    injector.clear()
    yield
    injector.clear()

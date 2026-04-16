#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ThreadPoolManager单元测试

测试ThreadPoolManager的核心功能，特别是关闭机制和资源释放
"""

import pytest
import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 导入必要的模块
from services.thread_pool_manager import thread_pool_manager


class TestThreadPoolManager:
    """ThreadPoolManager单元测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        assert thread_pool_manager is not None
    
    def test_get_preload_executor(self):
        """测试获取预加载执行器"""
        executor = thread_pool_manager.get_preload_executor()
        assert executor is not None
    
    def test_get_render_executor(self):
        """测试获取渲染执行器"""
        executor = thread_pool_manager.get_render_executor()
        assert executor is not None
    
    def test_shutdown(self):
        """测试关闭所有线程池"""
        # 确保执行器存在
        preload_executor = thread_pool_manager.get_preload_executor()
        render_executor = thread_pool_manager.get_render_executor()
        
        assert preload_executor is not None
        assert render_executor is not None
        
        # 提交一个任务
        def test_task():
            time.sleep(0.1)
            return "test"
        
        future = preload_executor.submit(test_task)
        assert future is not None
        
        # 等待任务完成
        result = future.result()
        assert result == "test"
        
        # 关闭所有线程池
        thread_pool_manager.shutdown(wait=True, timeout=2.0)
        
        # 检查线程池是否已关闭
        assert not thread_pool_manager.is_running()
    
    def test_get_pool_status(self):
        """测试获取线程池状态"""
        status = thread_pool_manager.get_pool_status()
        assert status is not None
        assert isinstance(status, dict)
        assert 'preload' in status
        assert 'render' in status
        assert 'detection' in status
        assert 'thumbnail' in status
    
    def test_is_running(self):
        """测试检查线程池是否正在运行"""
        # 检查线程池状态
        initial_status = thread_pool_manager.is_running()
        
        # 如果线程池已关闭，重新初始化
        if not initial_status:
            # 由于线程池是单例模式，我们无法直接重新初始化
            # 这里我们只测试方法是否存在并能正常调用
            pass
        else:
            # 关闭线程池
            thread_pool_manager.shutdown(wait=False, timeout=1.0)
            
            # 检查线程池是否已关闭
            assert not thread_pool_manager.is_running()

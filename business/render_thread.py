#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
渲染线程类

负责PDF页面的异步渲染，支持任务覆盖机制
"""

import logging
import threading
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional, Callable, Any


class RenderThread(QThread):
    """渲染线程类，支持任务覆盖机制"""
    
    # 渲染完成信号
    render_finished = pyqtSignal(int, object, bool)
    
    def __init__(self):
        """初始化渲染线程"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._running = True
        self._target = None
        self._args = ()
        self._kwargs = {}
        self._callback = None
        self._lock = threading.Lock()
        self._current_task_id = 0
        self._task_cancelled = False
    
    def set_target(self, target: Callable, *args, **kwargs):
        """设置渲染目标，覆盖旧任务
        
        参数：
        - target: 渲染函数
        - *args: 位置参数
        - **kwargs: 关键字参数
        """
        with self._lock:
            # 取消当前任务
            self._task_cancelled = True
            
            # 设置新任务
            self._target = target
            self._args = args
            self._kwargs = kwargs
            self._current_task_id += 1
            self._task_cancelled = False
            
            # 如果线程未运行，启动线程
            if not self.isRunning():
                self.start()
    
    def run(self):
        """线程运行函数"""
        while self._running:
            try:
                with self._lock:
                    if not self._target:
                        break
                    
                    target = self._target
                    args = self._args
                    kwargs = self._kwargs
                    task_id = self._current_task_id
                    task_cancelled = self._task_cancelled
                    
                    # 清除目标
                    self._target = None
                
                if task_cancelled:
                    continue
                
                # 执行渲染
                result = target(*args, **kwargs)
                
                # 检查任务是否被取消
                with self._lock:
                    if self._current_task_id != task_id or self._task_cancelled:
                        continue
                
                # 发送信号
                if result:
                    page_num = args[1] if len(args) > 1 else 0
                    self.render_finished.emit(page_num, result, True)
                
            except Exception as e:
                self.logger.error(f"渲染线程执行失败: {str(e)}")
                
                # 发送错误信号
                page_num = args[1] if len(args) > 1 else 0
                self.render_finished.emit(page_num, None, True)
            
            # 检查是否有新任务
            with self._lock:
                if not self._target:
                    break
    
    def stop(self):
        """停止渲染线程"""
        self._running = False
        with self._lock:
            self._task_cancelled = True
        self.wait(timeout=2.0)
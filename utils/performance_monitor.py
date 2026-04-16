#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能监控模块

功能：
- 监控渲染时间
- 监控缓存命中率
- 监控内存使用情况
- 生成性能报告
"""

import time
import memory_profiler
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        """初始化性能监控器"""
        self.logger = logging.getLogger(__name__)
        self.render_times: Dict[str, float] = {}
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.start_time: Optional[float] = None
        self.memory_usage: Dict[str, float] = {}
    
    def start_timer(self):
        """开始计时"""
        self.start_time = time.time()
    
    def stop_timer(self, operation: str) -> float:
        """停止计时并记录操作时间
        
        参数：
        - operation: str, 操作名称
        
        返回：
        - float: 操作耗时（秒）
        """
        if self.start_time is None:
            return 0.0
        
        elapsed = time.time() - self.start_time
        self.render_times[operation] = elapsed
        self.start_time = None
        return elapsed
    
    def record_cache_hit(self):
        """记录缓存命中"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        self.cache_misses += 1
    
    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率
        
        返回：
        - float: 缓存命中率（0-1）
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
    
    def record_memory_usage(self, operation: str):
        """记录内存使用情况
        
        参数：
        - operation: str, 操作名称
        """
        try:
            usage = memory_profiler.memory_usage()[0]
            self.memory_usage[operation] = usage
        except Exception as e:
            self.logger.error(f"记录内存使用失败: {str(e)}")
    
    def generate_report(self) -> Dict[str, Any]:
        """生成性能报告
        
        返回：
        - Dict[str, Any]: 性能报告
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "render_times": self.render_times,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.get_cache_hit_rate(),
            "memory_usage": self.memory_usage
        }
        
        return report
    
    def reset(self):
        """重置性能监控数据"""
        self.render_times.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.memory_usage.clear()


# 创建全局性能监控器实例
performance_monitor = PerformanceMonitor()

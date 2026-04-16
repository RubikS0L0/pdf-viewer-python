#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
依赖注入容器

功能：
- 管理所有组件的生命周期和依赖关系
- 支持单例管理和依赖解析
- 提供延迟加载能力，提高应用启动速度
"""

import logging
from typing import Dict, Type, Any, Optional, Callable


class DependencyInjector:
    """轻量级依赖注入容器"""
    
    def __init__(self):
        """初始化依赖注入容器"""
        self._registry: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._instances: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    def register(self, name: str, dependency: Any, is_singleton: bool = True) -> None:
        """注册依赖
        
        参数：
        - name: str, 依赖名称
        - dependency: Any, 依赖对象或工厂函数
        - is_singleton: bool, 是否为单例
        """
        if callable(dependency) and not isinstance(dependency, type):
            # 注册为工厂函数
            self._factories[name] = dependency
        else:
            # 注册为类型或实例
            self._registry[name] = {
                "dependency": dependency,
                "is_singleton": is_singleton
            }
    
    def register_interface(self, interface: Type, implementation: Type, is_singleton: bool = True) -> None:
        """注册接口与实现的映射
        
        参数：
        - interface: Type, 接口类型
        - implementation: Type, 实现类型
        - is_singleton: bool, 是否为单例
        """
        interface_name = interface.__name__
        self._registry[interface_name] = {
            "dependency": implementation,
            "is_singleton": is_singleton
        }
    
    def resolve(self, name: str, *args, **kwargs) -> Any:
        """解析依赖
        
        参数：
        - name: str, 依赖名称
        - *args: 位置参数
        - **kwargs: 关键字参数
        
        返回：
        - Any: 解析后的依赖实例
        """
        # 首先检查是否有工厂函数
        if name in self._factories:
            factory = self._factories[name]
            instance = factory(*args, **kwargs)
            return instance
        
        # 检查是否已注册
        if name not in self._registry:
            raise ValueError(f"依赖未注册: {name}")
        
        # 检查是否为单例且已存在实例
        if self._registry[name]["is_singleton"] and name in self._instances:
            return self._instances[name]
        
        # 创建实例
        dependency = self._registry[name]["dependency"]
        if isinstance(dependency, type):
            # 是类型，创建实例
            instance = dependency(*args, **kwargs)
        else:
            # 是实例，直接返回
            instance = dependency
        
        # 如果是单例，缓存实例
        if self._registry[name]["is_singleton"]:
            self._instances[name] = instance
        
        return instance
    
    def get_instance(self, name: str, *args, **kwargs) -> Any:
        """获取依赖实例（别名方法）
        
        参数：
        - name: str, 依赖名称
        - *args: 位置参数
        - **kwargs: 关键字参数
        
        返回：
        - Any: 依赖实例
        """
        return self.resolve(name, *args, **kwargs)
    
    def reset(self) -> None:
        """重置依赖注入容器，清除所有缓存的实例"""
        self._instances.clear()
    
    def clear(self) -> None:
        """清空依赖注入容器，移除所有注册的依赖"""
        self._registry.clear()
        self._factories.clear()
        self._instances.clear()


# 创建全局依赖注入容器实例
injector = DependencyInjector()

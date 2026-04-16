#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置加载模块

功能：
- 读取YAML配置文件
- 支持环境变量覆盖配置
- 提供配置访问接口
- 支持配置验证

开发环境：
- Python 3.14
- Windows系统

核心依赖：
- yaml：YAML文件解析
- os：环境变量访问
- typing：类型提示
"""

import yaml
import os
from typing import Dict, Any, Optional

class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_file: str = "config/development.yaml"):
        """初始化配置加载器
        
        参数：
        - config_file: str，配置文件路径
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            # 读取YAML配置文件
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            # 从环境变量覆盖配置
            self._override_from_env()
            
            # 验证配置完整性
            self._validate_config()
            
        except FileNotFoundError:
            raise Exception(f"配置文件未找到: {self.config_file}")
        except yaml.YAMLError as e:
            raise Exception(f"配置文件解析错误: {str(e)}")
        except Exception as e:
            raise Exception(f"配置加载失败: {str(e)}")
    
    def _override_from_env(self):
        """从环境变量覆盖配置"""
        # 模型配置
        if os.environ.get("PDFVIEW_MODEL_PATH"):
            self.config["model"]["path"] = os.environ.get("PDFVIEW_MODEL_PATH")
        if os.environ.get("PDFVIEW_MODEL_DEVICE"):
            self.config["model"]["device"] = os.environ.get("PDFVIEW_MODEL_DEVICE")
        
        # 检测配置
        if os.environ.get("PDFVIEW_DETECTION_CONF_THRESHOLD"):
            self.config["detection"]["conf_threshold"] = float(os.environ.get("PDFVIEW_DETECTION_CONF_THRESHOLD"))
        if os.environ.get("PDFVIEW_DETECTION_IOU_THRESHOLD"):
            self.config["detection"]["iou_threshold"] = float(os.environ.get("PDFVIEW_DETECTION_IOU_THRESHOLD"))
        
        # 内存配置
        if os.environ.get("PDFVIEW_MEMORY_WARNING_THRESHOLD"):
            self.config["memory"]["warning_threshold"] = float(os.environ.get("PDFVIEW_MEMORY_WARNING_THRESHOLD"))
        if os.environ.get("PDFVIEW_MEMORY_CRITICAL_THRESHOLD"):
            self.config["memory"]["critical_threshold"] = float(os.environ.get("PDFVIEW_MEMORY_CRITICAL_THRESHOLD"))
    
    def _validate_config(self):
        """验证配置完整性"""
        # 检查必填配置项
        required_keys = ["model", "detection", "memory", "cache", "ui", "zoom", "spacing", "preload"]
        for key in required_keys:
            if key not in self.config:
                raise Exception(f"配置缺失必填项: {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        参数：
        - key: str，配置键，支持点分隔（如"model.path"）
        - default: Any，默认值
        
        返回：
        - Any，配置值或默认值
        """
        keys = key.split(".")
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_model_path(self) -> str:
        """获取模型文件路径"""
        return self.get("model.path")
    
    def get_model_device(self) -> str:
        """获取模型设备"""
        return self.get("model.device")
    
    def get_detection_config(self) -> Dict[str, Any]:
        """获取检测配置"""
        return self.get("detection", {})
    
    def get_memory_config(self) -> Dict[str, Any]:
        """获取内存配置"""
        return self.get("memory", {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return self.get("cache", {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取界面配置"""
        return self.get("ui", {})
    
    def get_zoom_config(self) -> Dict[str, Any]:
        """获取缩放配置"""
        return self.get("zoom", {})
    
    def get_spacing_config(self) -> Dict[str, Any]:
        """获取间距配置"""
        return self.get("spacing", {})
    
    def get_preload_config(self) -> Dict[str, Any]:
        """获取预加载配置"""
        return self.get("preload", {})
    
    def get_labels(self) -> Dict[int, str]:
        """获取标签映射"""
        return self.get("labels", {})

# 创建全局配置实例
config_loader = ConfigLoader()

# -*- coding: utf-8 -*-
"""
图形检测配置类

功能：
- 集中管理YOLOv8检测的所有配置参数
- 支持动态更新配置
- 提供默认配置值
- 管理模型参数和后处理参数
- 自动读取models目录下的onnx模型和yaml文件
"""

import os
import yaml

# Import config loader
from utils.config_loader import config_loader

class DetectionConfig:
    """检测配置类"""
    def __init__(self):
        # 从配置文件加载默认值
        detection_config = config_loader.get_detection_config()
        memory_config = config_loader.get_memory_config()
        cache_config = config_loader.get_cache_config()
        zoom_config = config_loader.get_zoom_config()
        labels = config_loader.get_labels()
        
        # 模型参数
        self.model_path = config_loader.get_model_path()
        self.input_size = config_loader.get("model.input_size", 640)
        self.conf_threshold = detection_config.get("conf_threshold", 0.5)
        self.iou_threshold = detection_config.get("iou_threshold", 0.45)
        self.model_params = {
            "conf": self.conf_threshold,
            "iou": self.iou_threshold,
            "device": config_loader.get_model_device(),
            "verbose": detection_config.get("verbose", False)
        }
        
        # 后处理参数
        self.nms_threshold = detection_config.get("nms_threshold", 0.5)
        
        # 自动读取models目录下的onnx模型和yaml文件
        self.available_models = self._discover_models()
        
        # 标签映射
        self.class_names = self._load_class_names() or labels or {
            0: "valve",
            1: "pump",
            2: "heat_exchanger",
            3: "reactor",
            4: "tank",
            5: "pipe",
            6: "instrument",
            7: "other"
        }
    
    def _discover_models(self):
        """发现models目录下的所有onnx模型"""
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        available_models = []
        
        if os.path.exists(models_dir):
            for file in os.listdir(models_dir):
                if file.endswith(".onnx"):
                    model_path = os.path.join(models_dir, file)
                    yaml_path = os.path.join(models_dir, file.replace(".onnx", ".yaml"))
                    available_models.append({
                        "model_path": model_path,
                        "yaml_path": yaml_path if os.path.exists(yaml_path) else None
                    })
        
        return available_models
    
    def _load_class_names(self, yaml_path=None):
        """从yaml文件加载class_names
        
        参数：
        - yaml_path: str，可选，指定的yaml文件路径
        """
        # 首先尝试从指定的yaml_path加载
        if yaml_path and os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and "names" in config:
                        names = config["names"]
                        if isinstance(names, list):
                            return {i: name for i, name in enumerate(names)}
            except Exception as e:
                import logging
                logging.warning(f"Failed to load class names from {yaml_path}: {str(e)}")
        
        # 尝试从当前model_path对应的yaml文件加载
        if self.model_path:
            yaml_path = os.path.splitext(self.model_path)[0] + ".yaml"
            if os.path.exists(yaml_path):
                try:
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        if config and "names" in config:
                            names = config["names"]
                            if isinstance(names, list):
                                return {i: name for i, name in enumerate(names)}
                except Exception as e:
                    pass
        
        # 如果当前model_path没有对应的yaml文件，尝试从models目录下的任何yaml文件加载
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        if os.path.exists(models_dir):
            for file in os.listdir(models_dir):
                if file.endswith(".yaml"):
                    yaml_path = os.path.join(models_dir, file)
                    try:
                        with open(yaml_path, 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f)
                            if config and "names" in config:
                                names = config["names"]
                                if isinstance(names, list):
                                    return {i: name for i, name in enumerate(names)}
                    except Exception as e:
                        pass
        
        # 如果没有找到yaml文件，尝试从第一个可用模型的yaml文件加载
        for model_info in self.available_models:
            if model_info["yaml_path"]:
                try:
                    with open(model_info["yaml_path"], 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        if config and "names" in config:
                            names = config["names"]
                            if isinstance(names, list):
                                return {i: name for i, name in enumerate(names)}
                except Exception as e:
                    pass
        
        return None
    
    def update(self, **kwargs):
        """更新配置
        
        参数：
        - **kwargs: 配置参数
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                # 如果更新了阈值，同时更新model_params
                if key == "conf_threshold":
                    self.model_params["conf"] = value
                elif key == "iou_threshold":
                    self.model_params["iou"] = value
            elif key in self.model_params:
                self.model_params[key] = value
        
        # 如果更新了model_path，重新加载class_names
        if "model_path" in kwargs:
            self.class_names = self._load_class_names() or {
                0: "valve",
                1: "pump",
                2: "heat_exchanger",
                3: "reactor",
                4: "tank",
                5: "pipe",
                6: "instrument",
                7: "other"
            }
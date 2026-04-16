# -*- coding: utf-8 -*-
"""
图形识别系统检测模块

功能：
- 基于YOLOv8的图形元素检测
- 图像预处理与后处理
- 模块化设计，支持模型迭代与调整

核心组件：
- GraphicDetector：图形检测核心类
- ImagePreprocessor：图像预处理
- ResultProcessor：结果后处理
- DetectionConfig：检测配置管理
"""

# Try to import the actual implementation, but fall back to mocks if there are import errors
try:
    from .pid_detector import GraphicDetector as ActualGraphicDetector
    from .config import DetectionConfig as ActualDetectionConfig
    YOLO_AVAILABLE = True
except ImportError as e:
    YOLO_AVAILABLE = False
    
    # Create mock classes to prevent errors
    class MockGraphicDetector:
        def __init__(self, model_path, config=None):
            self.model_path = model_path
            self.config = config
            # 尝试从yaml文件加载class_names
            self.class_names = {}
            if model_path:
                import os
                import yaml
                yaml_path = os.path.splitext(model_path)[0] + ".yaml"
                if os.path.exists(yaml_path):
                    try:
                        with open(yaml_path, 'r', encoding='utf-8') as f:
                            yaml_config = yaml.safe_load(f)
                            if yaml_config and "names" in yaml_config:
                                names = yaml_config["names"]
                                if isinstance(names, list):
                                    self.class_names = {i: name for i, name in enumerate(names)}
                    except Exception as e:
                        pass
        def detect(self, image):
            return []
        def update_model(self, new_model_path):
            self.model_path = new_model_path
        def get_model_info(self):
            return {'model_type': 'Mock', 'model_path': self.model_path, 'class_names': self.class_names}
    
    class MockDetectionConfig:
        def __init__(self):
            self.model_path = ""
            self.input_size = 640
            self.conf_threshold = 0.5
            self.iou_threshold = 0.45
            self.model_params = {
                "conf": 0.5,
                "iou": 0.45,
                "device": "cpu",
                "verbose": False
            }
            self.nms_threshold = 0.5
            # 尝试从models目录下的yaml文件加载class_names
            self.class_names = {}
            import os
            import yaml
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
            if os.path.exists(models_dir):
                for file in os.listdir(models_dir):
                    if file.endswith(".yaml"):
                        yaml_path = os.path.join(models_dir, file)
                        try:
                            with open(yaml_path, 'r', encoding='utf-8') as f:
                                yaml_config = yaml.safe_load(f)
                                if yaml_config and "names" in yaml_config:
                                    names = yaml_config["names"]
                                    if isinstance(names, list):
                                        self.class_names = {i: name for i, name in enumerate(names)}
                                        break  # 使用第一个找到的yaml文件
                        except Exception as e:
                            logging.warning(f"Failed to load class names from {yaml_path}: {str(e)}")
            # 如果没有找到yaml文件，使用默认值
            if not self.class_names:
                self.class_names = {
                    0: "person",
                    1: "car"
                }
        def update(self, **kwargs):
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
    
    ActualGraphicDetector = MockGraphicDetector
    ActualDetectionConfig = MockDetectionConfig

# Export the actual or mock classes
GraphicDetector = ActualGraphicDetector
DetectionConfig = ActualDetectionConfig

__all__ = [
    'GraphicDetector',
    'DetectionConfig',
    'YOLO_AVAILABLE'
]
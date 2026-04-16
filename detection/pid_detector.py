# -*- coding: utf-8 -*-
"""
图形检测核心模块

功能：
- 基于YOLOv8的图形元素检测
- 集成图像预处理和结果后处理
- 支持模型动态更新
- 提供简洁的检测接口

核心方法：
- detect: 执行图形检测
- update_model: 更新YOLOv8模型
"""

from .image_preprocessor import ImagePreprocessor
from .result_processor import ResultProcessor
from .config import DetectionConfig

class GraphicDetector:
    """图形检测核心类"""
    def __init__(self, model_path, config=None):
        """初始化图形检测器
        
        参数：
        - model_path: str，YOLOv8模型文件路径
        - config: DetectionConfig对象，检测配置，默认为None
        """
        self.config = config or DetectionConfig()
        self.model_path = model_path
        self.model = None
        self.preprocessor = ImagePreprocessor(self.config)
        self.result_processor = ResultProcessor(self.config)
        
        # Try to initialize the model here, but don't fail if it doesn't work
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
        except Exception as e:
            import logging
            logging.warning(f"Failed to initialize YOLOv8 model: {str(e)}")
            self.model = None
    
    def detect(self, image):
        """检测图形元素
        
        参数：
        - image: ndarray，输入图像（BGR格式）
        
        返回：
        - list，检测结果列表，每个元素为字典，包含class_id、class_name、confidence和bbox
        """
        if self.model is None:
            # If model initialization failed earlier, return empty results
            return []
        
        try:
            # 图像预处理
            processed_image = self.preprocessor.process(image)
            
            # 模型推理
            results = self.model(processed_image, **self.config.model_params)
            
            # 结果后处理
            processed_results = self.result_processor.process(results)
            
            return processed_results
        except Exception as e:
            import logging
            logging.error(f"Error during detection: {str(e)}")
            return []
    
    def update_model(self, new_model_path):
        """更新YOLOv8模型
        
        参数：
        - new_model_path: str，新的YOLOv8模型文件路径
        """
        try:
            from ultralytics import YOLO
            self.model = YOLO(new_model_path)
            self.model_path = new_model_path
        except Exception as e:
            import logging
            logging.error(f"Failed to update YOLOv8 model: {str(e)}")
    
    def get_model_info(self):
        """获取模型信息
        
        返回：
        - dict，包含模型的基本信息
        """
        if self.model is None:
            return {
                'model_type': 'YOLOv8',
                'model_path': self.model_path,
                'class_names': self.config.class_names
            }
        
        try:
            # 优先使用配置文件中的class_names，这样可以覆盖模型自带的names
            return {
                'model_type': type(self.model).__name__,
                'model_path': self.model.ckpt_path if hasattr(self.model, 'ckpt_path') else self.model_path,
                'class_names': self.config.class_names
            }
        except Exception as e:
            import logging
            logging.error(f"Error getting model info: {str(e)}")
            return {
                'model_type': 'YOLOv8',
                'model_path': self.model_path,
                'class_names': self.config.class_names
            }
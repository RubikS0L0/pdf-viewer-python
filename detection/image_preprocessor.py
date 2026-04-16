# -*- coding: utf-8 -*-
"""
化工PID图纸图像预处理模块

功能：
- 对输入图像进行预处理，使其适合YOLOv8模型输入
- 支持图像缩放、归一化等操作
- 模块化设计，便于扩展新的预处理方法
"""

import cv2
import numpy as np

class ImagePreprocessor:
    """图像预处理类"""
    def __init__(self, config):
        self.config = config
    
    def process(self, image):
        """预处理图像，适应YOLOv8输入要求
        
        参数：
        - image: ndarray，输入图像（BGR格式）
        
        返回：
        - processed_image: ndarray，预处理后的图像
        """
        # 缩放图像
        resized = cv2.resize(image, (self.config.input_size, self.config.input_size))
        
        # 归一化
        normalized = resized / 255.0
        
        return normalized
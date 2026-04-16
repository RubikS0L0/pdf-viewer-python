# -*- coding: utf-8 -*-
"""
图形检测结果后处理模块

功能：
- 处理YOLOv8模型的原始检测结果
- 过滤低置信度检测结果
- 格式化检测结果，便于后续使用
- 支持非极大值抑制（NMS）处理
"""

class ResultProcessor:
    """结果后处理类"""
    def __init__(self, config):
        self.config = config
    
    def process(self, results):
        """处理YOLOv8推理结果
        
        参数：
        - results: YOLOv8模型推理结果对象
        
        返回：
        - processed_results: list，处理后的检测结果列表，每个元素为字典
        """
        processed_results = []
        
        for result in results:
            boxes = result.boxes.cpu().numpy()
            for box in boxes:
                # 过滤低置信度结果
                if box.conf[0] >= self.config.conf_threshold:
                    class_id = int(box.cls[0])
                    # 优先使用配置文件中的class_names，如果不存在则使用模型自带的names
                    if class_id in self.config.class_names:
                        class_name = self.config.class_names[class_id]
                    else:
                        class_name = result.names[class_id] if hasattr(result, 'names') and result.names else f"class_{class_id}"
                    
                    processed_results.append({
                        'class_id': class_id,
                        'class_name': class_name,
                        'confidence': float(box.conf[0]),
                        'bbox': box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    })
        
        return processed_results
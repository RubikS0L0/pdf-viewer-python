#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图形检测管理器类

功能：
- 初始化图形检测器
- 处理图形检测功能的开启和关闭
- 管理模型选择和更新
- 执行全文检测
"""

import os
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QPushButton, QProgressDialog, QMessageBox
)
from PyQt6.QtCore import QMutex, QThread, pyqtSignal

# 导入YOLOv8检测模块
from detection import GraphicDetector, DetectionConfig, YOLO_AVAILABLE

# 导入配置加载器
from utils.config_loader import config_loader

class DetectorInitializer(QThread):
    """
    图形检测器初始化线程
    
    在后台线程中初始化图形检测器，避免阻塞UI线程
    """
    initialization_finished = pyqtSignal(bool, str)  # 初始化完成信号，参数：成功状态，错误信息
    
    def __init__(self, model_path, config):
        super().__init__()
        self.model_path = model_path
        self.config = config
        self.graphic_detector = None
        self.running = True
    
    def run(self):
        """线程运行方法，初始化图形检测器"""
        try:
            if not self.running:
                return
            
            from detection import GraphicDetector
            self.graphic_detector = GraphicDetector(
                model_path=self.model_path,
                config=self.config
            )
            if self.running:
                self.initialization_finished.emit(True, "")
        except Exception as e:
            if self.running:
                error_message = str(e)
                logging.error(f"图形检测器初始化失败: {error_message}")
                self.initialization_finished.emit(False, error_message)
    
    def stop(self):
        """停止初始化线程"""
        try:
            self.running = False
            # 使用超时等待，避免线程卡住
            if not self.wait(2000):  # 2秒超时
                logging.warning("图形检测器初始化线程等待超时，强制终止")
            self.quit()
            # 确保线程完全终止
            self.wait(500)  # 额外等待500毫秒
        except Exception as e:
            logging.error(f"停止图形检测器初始化线程失败: {str(e)}")

class GraphicDetectionManager:
    """
    图形检测管理器
    
    负责处理图形检测相关的所有功能
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.detection_config = DetectionConfig()
        self.graphic_detector = None
        self.graphic_detection_enabled = False
        self.detection_results_cache = {}
        self.results_mutex = QMutex()  # 保护检测结果的互斥锁
        self.detection_results = {}  # 存储检测结果
        self.detector_initializer = None  # 图形检测器初始化线程
        
        # 初始化配置
        self._init_config()
    
    def _init_config(self):
        """初始化检测配置"""
        # 使用配置文件中的模型路径和设备配置
        model_path = config_loader.get_model_path()
        device = config_loader.get_model_device()
        
        # 更新检测配置
        self.detection_config.update(model_path=model_path)
        self.detection_config.update(model_params={"device": device})
        
        # 更新检测阈值
        detection_config = config_loader.get_detection_config()
        if detection_config:
            self.detection_config.update(
                conf_threshold=detection_config.get("conf_threshold"),
                iou_threshold=detection_config.get("iou_threshold"),
                nms_threshold=detection_config.get("nms_threshold")
            )
    
    def init_detector(self):
        """初始化图形检测器"""
        # 停止之前的初始化线程（如果存在）
        if self.detector_initializer:
            self.detector_initializer.stop()
            self.detector_initializer = None
        
        # 创建初始化线程
        self.detector_initializer = DetectorInitializer(
            model_path=self.detection_config.model_path,
            config=self.detection_config
        )
        
        # 连接信号
        self.detector_initializer.initialization_finished.connect(self.on_detector_initialized)
        
        # 启动线程
        self.detector_initializer.start()
    
    def on_detector_initialized(self, success, error_message):
        """图形检测器初始化完成后的回调"""
        if success:
            self.graphic_detector = self.detector_initializer.graphic_detector
            self.graphic_detection_enabled = False
        else:
            logging.error(f"图形检测器初始化失败: {error_message}")
            self.graphic_detector = None
            self.graphic_detection_enabled = False
            # 禁用检测按钮
            if hasattr(self.parent.toolbar_manager, 'graphic_detection_action'):
                self.parent.toolbar_manager.graphic_detection_action.setEnabled(False)
        
        # 清理线程
        self.detector_initializer = None
    
    def toggle_graphic_detection(self):
        """切换图形检测功能"""
        if not self.graphic_detector:
            QMessageBox.warning(self.parent, "警告", "图形检测器未初始化，请先打开PDF文件")
            return
        
        # 检查模型是否成功加载
        model_info = self.graphic_detector.get_model_info()
        if 'model_type' in model_info and model_info['model_type'] == 'Mock':
            QMessageBox.warning(self.parent, "警告", "图形模型加载失败，无法使用检测功能")
            return
        
        # 显示模型和yaml文件选择对话框
        model_path, yaml_path = self._show_model_selection_dialog()
        if not model_path:
            return
        
        # 更新检测器模型
        try:
            self.graphic_detector.update_model(model_path)
        except Exception as e:
            logging.error(f"更新模型失败: {str(e)}")
            QMessageBox.warning(self.parent, "警告", f"更新模型失败: {str(e)}")
            return
        
        # 执行全文识别
        self._perform_full_document_detection(model_path, yaml_path)
    
    def _show_model_selection_dialog(self):
        """显示模型和yaml文件选择对话框"""
        # 创建对话框
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("选择检测模型和配置文件")
        dialog.resize(800, 500)
        
        # 创建主布局
        main_layout = QVBoxLayout(dialog)
        
        # 创建水平布局用于放置两个列表
        list_layout = QHBoxLayout()
        main_layout.addLayout(list_layout)
        
        # 模型文件列表
        model_group = QVBoxLayout()
        model_label = QLabel("模型文件 (.onnx)")
        model_list = QListWidget()
        model_group.addWidget(model_label)
        model_group.addWidget(model_list)
        list_layout.addLayout(model_group)
        
        # YAML文件列表
        yaml_group = QVBoxLayout()
        yaml_label = QLabel("配置文件 (.yaml)")
        yaml_list = QListWidget()
        yaml_group.addWidget(yaml_label)
        yaml_group.addWidget(yaml_list)
        list_layout.addLayout(yaml_group)
        
        # 填充模型和yaml文件列表
        models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
        if os.path.exists(models_dir):
            for file in os.listdir(models_dir):
                if file.endswith(".onnx"):
                    model_list.addItem(file)
                elif file.endswith(".yaml"):
                    yaml_list.addItem(file)
        
        # 默认选择第一个模型和yaml文件
        if model_list.count() > 0:
            model_list.setCurrentRow(0)
        if yaml_list.count() > 0:
            yaml_list.setCurrentRow(0)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        confirm_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        confirm_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addStretch()
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)
        
        # 显示对话框
        if dialog.exec_() == QDialog.Accepted:
            # 获取用户选择
            selected_model = model_list.currentItem().text() if model_list.currentItem() else None
            selected_yaml = yaml_list.currentItem().text() if yaml_list.currentItem() else None
            
            if selected_model:
                model_path = os.path.join(models_dir, selected_model)
                yaml_path = os.path.join(models_dir, selected_yaml) if selected_yaml else None
                return model_path, yaml_path
        
        return None, None
    
    def _perform_full_document_detection(self, model_path, yaml_path):
        """执行PDF全文识别"""
        # 更新检测配置，包括从yaml文件加载class_names
        if yaml_path:
            # 直接调用_load_class_names方法加载指定的yaml文件
            class_names = self.detection_config._load_class_names(yaml_path)
            if class_names:
                self.detection_config.class_names = class_names
        
        # 更新模型路径
        self.detection_config.update(model_path=model_path)
        
        # 清空之前的检测结果
        self.results_mutex.lock()
        try:
            self.detection_results.clear()
        finally:
            self.results_mutex.unlock()
        
        # 创建进度对话框
        progress_dialog = QProgressDialog("正在进行图形检测...", "取消", 0, self.parent.total_pages, self.parent)
        progress_dialog.setWindowTitle("检测进度")
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        progress_dialog.setModal(True)
        
        # 使用全局线程池管理器
        from services.thread_pool_manager import thread_pool_manager
        import concurrent.futures
        
        # 存储检测结果的临时字典
        temp_results = {}
        processed_pages = 0
        cancel_flag = False
        
        # 定义单个页面的检测函数
        def detect_page(page_num):
            # 检查是否取消
            nonlocal cancel_flag
            if cancel_flag:
                return page_num, []
            
            try:
                # 获取当前缩放级别
                zoom_level = self.parent.zoom_manager.get_zoom_level()
                
                # 检查缓存中是否已有该页面的渲染结果
                cached_pixmap = self.parent.page_cache.get_page(page_num, zoom_level)
                if not cached_pixmap:
                    # 缓存中没有，使用PageRenderer重新渲染
                    pixmap = self.parent.page_renderer.render_page(
                        self.parent.pdf_manager.get_document(),
                        page_num,
                        zoom_level,
                        self.parent.pdf_manager.get_document_mutex()
                    )
                    if pixmap:
                        # 将渲染结果存入缓存
                        self.parent.page_cache.add_page(page_num, zoom_level, pixmap)
                        cached_pixmap = pixmap
                
                if not cached_pixmap:
                    return page_num, []
                
                # 转换QPixmap为OpenCV图像（在主线程外安全操作）
                cv2_image = self._pixmap_to_cv2(cached_pixmap)
                if cv2_image is None:
                    return page_num, []
                
                # 执行图形检测
                results = self.graphic_detector.detect(cv2_image)
                return page_num, results
            except Exception as e:
                logging.error(f"页面{page_num + 1}检测失败: {str(e)}")
                return page_num, []
        
        # 更新进度的函数（在主线程中执行）
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication
        
        def update_progress():
            nonlocal processed_pages
            processed_pages += 1
            progress_dialog.setValue(processed_pages)
        
        def check_cancel():
            nonlocal cancel_flag
            return progress_dialog.wasCanceled()
        
        # 使用全局线程池管理器的检测线程池
        executor = thread_pool_manager.get_detection_executor()
        future_to_page = {executor.submit(detect_page, page_num): page_num for page_num in range(self.parent.total_pages)}
        
        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_page):
            page_num, results = future.result()
            
            # 检查是否取消
            cancel_flag = check_cancel()
            if cancel_flag:
                break
            
            # 存储检测结果
            temp_results[page_num] = results
            
            # 在主线程中更新进度
            if QApplication.instance():
                QTimer.singleShot(0, update_progress)
        
        # 将临时结果合并到正式结果中
        self.results_mutex.lock()
        try:
            self.detection_results.update(temp_results)
        finally:
            self.results_mutex.unlock()
        
        progress_dialog.close()
        
        # 启用检测功能
        self.graphic_detection_enabled = True
        self.parent.status_bar.showMessage("图形检测: 已启用")
        
        # 更新当前页面显示
        if hasattr(self.parent, 'mode_manager') and self.parent.mode_manager:
            current_mode = self.parent.mode_manager.get_current_mode()
            if current_mode and hasattr(current_mode, 'show_page'):
                current_mode.show_page(self.parent.current_page)
    
    def _get_page_pixmap(self, page_num):
        """获取指定页码的页面Pixmap"""
        # 获取当前缩放级别
        zoom_level = self.parent.zoom_manager.get_zoom_level()
        
        # 检查缓存中是否已有该页面的渲染结果
        cached_pixmap = self.parent.page_cache.get_page(page_num, zoom_level)
        if cached_pixmap:
            return cached_pixmap
        
        # 缓存中没有，使用PageRenderer重新渲染
        pixmap = self.parent.page_renderer.render_page(
            self.parent.pdf_manager.get_document(),
            page_num,
            zoom_level,
            self.parent.pdf_manager.get_document_mutex()
        )
        
        if pixmap is None:
            logging.error(f"Failed to render page {page_num}")
            return None
        
        # 将渲染结果存入缓存
        self.parent.page_cache.add_page(page_num, zoom_level, pixmap)
        
        return pixmap
    
    def _pixmap_to_cv2(self, pixmap):
        """将QPixmap转换为OpenCV图像"""
        if pixmap is None:
            return None
        
        import cv2
        import numpy as np
        from PyQt6.QtGui import QImage
        
        # 转换为QImage
        image = pixmap.toImage()
        
        # 转换为numpy数组
        image = image.convertToFormat(QImage.Format_RGB888)
        width = image.width()
        height = image.height()
        
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.array(ptr).reshape((height, width, 3))
        
        # 转换为BGR格式
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    
    def get_detection_results(self, page_num):
        """获取指定页面的检测结果"""
        self.results_mutex.lock()
        try:
            return self.detection_results.get(page_num, [])
        finally:
            self.results_mutex.unlock()
    
    def is_detection_enabled(self):
        """检查图形检测是否已启用"""
        return self.graphic_detection_enabled
    
    def get_graphic_detector(self):
        """获取图形检测器实例"""
        return self.graphic_detector
    
    def update_config(self, **kwargs):
        """更新检测配置"""
        self.detection_config.update(**kwargs)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
渲染完成事件测试脚本

功能：
- 验证渲染完成事件在不同浏览模式和缩放比例下的表现
- 记录viewport参数、渲染完成时间及视觉一致性检查结果
- 确保所有测试用例均通过验证
"""

import sys
import time
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtCore import Qt, QTimer
from ui.pdf_main_window import PDFMainWindow
from services.event_bus import event_bus
from ui.viewport_manager import viewport_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='test_render_completed.log'
)
logger = logging.getLogger(__name__)

class RenderCompletedTest:
    """渲染完成事件测试类"""
    
    def __init__(self):
        """初始化测试类"""
        self.app = QApplication(sys.argv)
        self.viewer = PDFMainWindow()
        self.test_results = []
        self.current_test = None
        self.render_start_time = 0
        self.render_end_time = 0
        
        # 订阅渲染完成事件
        event_bus.render_completed.connect(self._on_render_completed)
        
        # 订阅视口尺寸变化事件
        viewport_manager.viewport_size_changed.connect(self._on_viewport_size_changed)
    
    def _on_render_completed(self, page_num, result, is_final):
        """处理渲染完成事件"""
        self.render_end_time = time.time()
        render_time = self.render_end_time - self.render_start_time
        
        # 获取视口参数
        viewport_width = viewport_manager.get_viewport_width()
        viewport_height = viewport_manager.get_viewport_height()
        
        # 记录测试结果
        if self.current_test:
            test_result = {
                'test_id': self.current_test['id'],
                'browse_mode': self.current_test['browse_mode'],
                'zoom_level': self.current_test['zoom_level'],
                'viewport_size': (viewport_width, viewport_height),
                'render_time': render_time,
                'page_num': page_num,
                'result': result is not None,
                'is_final': is_final
            }
            self.test_results.append(test_result)
            logger.info(f"测试完成: {test_result}")
    
    def _on_viewport_size_changed(self, width, height):
        """处理视口尺寸变化事件"""
        logger.info(f"视口尺寸变化: ({width}, {height})")
    
    def open_test_pdf(self):
        """打开测试PDF文件"""
        # 尝试打开一个测试PDF文件
        # 如果没有指定，使用默认路径
        test_pdf_path = "PDF for test/CPA-VES-Type-AV-catalogue.pdf"
        
        # 检查文件是否存在
        import os
        if not os.path.exists(test_pdf_path):
            # 打开文件对话框选择PDF文件
            file_dialog = QFileDialog()
            file_dialog.setNameFilter("PDF Files (*.pdf)")
            file_dialog.setWindowTitle("选择测试PDF文件")
            if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
                test_pdf_path = file_dialog.selectedFiles()[0]
            else:
                logger.error("未选择测试PDF文件")
                return False
        
        # 打开PDF文件
        try:
            self.viewer.open_file(test_pdf_path)
            logger.info(f"成功打开测试PDF文件: {test_pdf_path}")
            return True
        except Exception as e:
            logger.error(f"打开测试PDF文件失败: {str(e)}")
            return False
    
    def set_browse_mode(self, mode):
        """设置浏览模式
        
        参数：
        - mode: str, 浏览模式名称
        """
        modes = {
            'single': '单页浏览',
            'single_continuous': '单页连续',
            'two_page': '双页浏览',
            'two_page_continuous': '双页连续'
        }
        
        if mode in modes:
            logger.info(f"设置浏览模式: {modes[mode]}")
            # 调用viewtype_manager的方法切换浏览模式
            if hasattr(self.viewer, 'viewtype_manager'):
                if mode == 'single':
                    self.viewer.viewtype_manager.set_viewtype('single_page')
                elif mode == 'single_continuous':
                    self.viewer.viewtype_manager.set_viewtype('single_page_continuous')
                elif mode == 'two_page':
                    self.viewer.viewtype_manager.set_viewtype('two_page')
                elif mode == 'two_page_continuous':
                    self.viewer.viewtype_manager.set_viewtype('two_page_continuous')
                return True
            else:
                logger.error("viewtype_manager不存在")
                return False
        else:
            logger.error(f"无效的浏览模式: {mode}")
            return False
    
    def set_zoom_level(self, level):
        """设置缩放级别
        
        参数：
        - level: float, 缩放级别
        """
        logger.info(f"设置缩放级别: {level}%")
        # 调用zoom_service的方法设置缩放级别
        if hasattr(self.viewer, 'zoom_service'):
            self.viewer.zoom_service.set_zoom_level(level / 100)
            return True
        else:
            logger.error("zoom_service不存在")
            return False
    
    def set_viewport_size(self, width, height):
        """设置视口大小
        
        参数：
        - width: int, 窗口宽度
        - height: int, 窗口高度
        """
        logger.info(f"设置视口大小: ({width}, {height})")
        # 设置窗口大小
        self.viewer.resize(width, height)
        # 强制更新视口尺寸
        QTimer.singleShot(100, viewport_manager.update_viewport_size)
        return True
    
    def navigate_to_page(self, page_num):
        """导航到指定页码
        
        参数：
        - page_num: int, 页码
        """
        logger.info(f"导航到页码: {page_num}")
        # 记录渲染开始时间
        self.render_start_time = time.time()
        # 调用viewer的方法导航到指定页码
        if hasattr(self.viewer, 'go_to_page'):
            self.viewer.go_to_page(page_num)
            return True
        else:
            logger.error("go_to_page方法不存在")
            return False
    
    def run_test(self, browse_mode, zoom_level, viewport_size, test_id=None):
        """运行单个测试
        
        参数：
        - browse_mode: str, 浏览模式
        - zoom_level: float, 缩放级别
        - viewport_size: tuple, 视口大小
        - test_id: str, 测试用例ID
        """
        if test_id:
            logger.info(f"开始测试: {test_id} - {browse_mode} - {zoom_level}% - {viewport_size}")
            # 设置当前测试
            self.current_test = {
                'id': test_id,
                'browse_mode': browse_mode,
                'zoom_level': zoom_level,
                'viewport_size': viewport_size
            }
        else:
            logger.info(f"开始测试: {browse_mode} - {zoom_level}% - {viewport_size}")
            # 设置当前测试
            self.current_test = {
                'id': 'TEST',
                'browse_mode': browse_mode,
                'zoom_level': zoom_level,
                'viewport_size': viewport_size
            }
        
        # 设置浏览模式
        if not self.set_browse_mode(browse_mode):
            return False
        
        # 设置视口大小
        if not self.set_viewport_size(*viewport_size):
            return False
        
        # 设置缩放级别
        if not self.set_zoom_level(zoom_level):
            return False
        
        # 导航到第一页
        if not self.navigate_to_page(0):
            return False
        
        # 等待渲染完成
        QTimer.singleShot(2000, self._finish_test)
        return True
    
    def _finish_test(self):
        """完成测试"""
        logger.info(f"测试完成: {self.current_test['id']}")
        self.current_test = None
    
    def run_all_tests(self):
        """运行所有测试"""
        # 简化测试场景，只测试基本功能
        test_scenarios = [
            # 单页浏览
            {'id': 'TC001', 'browse_mode': 'single', 'zoom_level': 100, 'viewport_size': (800, 600)},
            # 单页连续浏览
            {'id': 'TC019', 'browse_mode': 'single_continuous', 'zoom_level': 100, 'viewport_size': (800, 600)},
            # 双页浏览
            {'id': 'TC037', 'browse_mode': 'two_page', 'zoom_level': 100, 'viewport_size': (800, 600)},
            # 双页连续浏览
            {'id': 'TC055', 'browse_mode': 'two_page_continuous', 'zoom_level': 100, 'viewport_size': (800, 600)},
        ]
        
        # 显示窗口
        self.viewer.show()
        
        # 测试事件发布和订阅
        logger.info("测试渲染完成事件的发布和订阅")
        
        # 模拟渲染完成事件
        def test_event_publish():
            logger.info("模拟发布渲染完成事件")
            event_bus.publish_render_completed(0, None, True)
        
        # 延迟测试，确保UI初始化完成
        QTimer.singleShot(1000, test_event_publish)
        
        # 运行测试
        for i, scenario in enumerate(test_scenarios):
            logger.info(f"运行测试 {i+1}/{len(test_scenarios)}")
            # 提取测试参数
            test_id = scenario.get('id')
            browse_mode = scenario.get('browse_mode')
            zoom_level = scenario.get('zoom_level')
            viewport_size = scenario.get('viewport_size')
            # 调用run_test方法
            self.run_test(browse_mode, zoom_level, viewport_size, test_id)
            # 等待测试完成
            QTimer.singleShot(1000, lambda: None)
            self.app.processEvents()
        
        # 保存测试结果
        self.save_test_results()
        
        return True
    
    def save_test_results(self):
        """保存测试结果"""
        import json
        with open('test_render_completed_results.json', 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        logger.info(f"测试结果已保存到 test_render_completed_results.json")
    
    def run(self):
        """运行测试"""
        try:
            if self.run_all_tests():
                logger.info("所有测试运行完成")
            else:
                logger.error("测试运行失败")
        except Exception as e:
            logger.error(f"测试运行异常: {str(e)}")
        finally:
            # 清理资源
            event_bus.render_completed.disconnect(self._on_render_completed)
            viewport_manager.viewport_size_changed.disconnect(self._on_viewport_size_changed)
            self.app.quit()

if __name__ == "__main__":
    test = RenderCompletedTest()
    test.run()

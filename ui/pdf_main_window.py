#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF浏览器主窗口类

功能：
- 初始化主窗口UI
- 管理工具栏和菜单
- 处理主要事件
- 协调各功能模块
"""

import os
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QMessageBox, QWidget, QVBoxLayout, QSplitter, QStatusBar, QProgressBar, QFileDialog, QLabel
)
from PyQt6.QtGui import QAction, QPixmap, QPainter, QFont, QColor, QKeySequence
from PyQt6.QtCore import Qt, QEvent

# 导入异常处理模块
from utils.exception_handler import handle_exception, ResourceManager

# 导入模式管理器
from viewtypes import ViewtypeManager

# 导入常量
from utils.constants import Constants

# 导入新的依赖注入容器
from utils.di_container import container

# 导入自定义UI组件
from ui.thumbnail_manager import ThumbnailManager
from ui.toolbar_manager import ToolbarManager
from ui.navigation_controller import NavigationController
from ui.zoom_controller import ZoomController
from ui.viewport_manager import viewport_manager
from ui.content_area import ContentArea
from ui.styles import get_stylesheet, apply_stylesheet

class PDFMainWindow(QMainWindow):
    """
    PDF浏览器主窗口
    
    负责协调各功能模块，管理主窗口UI和事件处理
    """
    
    def __init__(self):
        super().__init__()
        
        # 初始化日志记录器
        self.logger = logging.getLogger(__name__)
        
        # 从依赖注入容器获取服务和管理器
        self.pdf_service = container.pdf_service()
        self.pdf_manager = container.pdf_manager()
        self.page_renderer = container.page_renderer()
        self.page_cache = container.page_cache()
        self.zoom_service = container.zoom_service()
        # 创建视图类型服务
        self.viewtype_service = container.viewtype_service(pdf_viewer=self)
        
        # 使用全局线程池管理器
        from services.thread_pool_manager import thread_pool_manager
        self.preload_executor = thread_pool_manager.get_preload_executor()
        
        # UI相关变量
        self.current_page = 0
        self.total_pages = 0
        self.reading_mode = False
        
        # 初始化主窗口UI
        self.init_ui()
        
        # 初始化组件管理器
        self._init_managers()
    
    def _init_managers(self):
        """初始化各功能管理器"""
        # 工具栏管理器
        self.toolbar_manager = ToolbarManager(self)
        
        # 导航控制器
        self.navigation_controller = NavigationController(self)
        
        # 缩放控制器
        self.zoom_controller = ZoomController(self, self.zoom_service)

        # 视图类型管理器
        self.viewtype_manager = ViewtypeManager(self, self.viewtype_service)
        
        # 缩略图管理器
        self.thumbnail_manager = ThumbnailManager(self)
        
        # 完成UI初始化
        self._complete_ui_initialization()
        # 移除过早的视图类型激活调用，改为在打开PDF文件后激活
        # self.viewtype_manager.current_viewtype.activate()
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口标题和大小
        self.setWindowTitle("PDF浏览器")
        self.setGeometry(100, 100, 1200, 800)
        
        # 应用全局样式表
        apply_stylesheet(self)
        
        # 创建中央部件
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QStatusBar
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建内容区域和缩略图面板
        self.content_area, self.scroll_area = self._create_content_area()
        
        # 初始化视口管理器
        from ui.viewport_manager import viewport_manager
        self.viewport_manager = viewport_manager
        # 设置滚动区域
        self.viewport_manager.set_scroll_area(self.scroll_area)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._setup_statusbar()
        
        # 添加事件过滤器，监听scroll_area的背景色变化
        self.scroll_area.installEventFilter(self)
        
        # 初始化内容区域背景色
        self.update_content_background()
    
    def _setup_statusbar(self):
        """设置状态栏样式和内容"""
        from ui.styles import get_colors
        colors = get_colors()
        
        # 设置状态栏样式 - Windows风格
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {colors.statusbar_bg},
                    stop:1 #E8E8E8);
                border-top: 1px solid {colors.toolbar_border};
                padding: 2px 8px;
                font-size: 12px;
                color: {colors.text_secondary};
            }}
            QStatusBar::item {{
                border: none;
            }}
        """)
        
        # 显示就绪状态
        self.status_bar.showMessage("就绪")
        
        # 添加忙碌指示器
        from PyQt6.QtWidgets import QProgressBar
        self.busy_indicator = QProgressBar(self.status_bar)
        self.busy_indicator.setMaximumWidth(200)
        self.busy_indicator.setMinimum(0)
        self.busy_indicator.setMaximum(0)  # 设置为忙碌模式
        self.busy_indicator.setVisible(False)
        self.status_bar.addPermanentWidget(self.busy_indicator)
        
        # 添加信息标签（页码、缩放、视图模式）
        self.status_page_label = QLabel("第 -/- 页")
        self.status_zoom_label = QLabel("缩放: 100%")
        self.status_mode_label = QLabel("单页浏览")
        
        # 设置标签样式
        label_style = f"""
            QLabel {{
                color: {colors.text_secondary};
                font-size: 12px;
                padding: 0 8px;
            }}
        """
        for label in [self.status_page_label, self.status_zoom_label, self.status_mode_label]:
            label.setStyleSheet(label_style)
            self.status_bar.addPermanentWidget(label)
    
    def _create_content_area(self):
        """创建右侧内容显示区域"""
        from ui.content_area import ContentArea
        self.content_area = ContentArea(self)
        return self.content_area, self.content_area.scroll_area
    
    def _complete_ui_initialization(self):
        """完成UI初始化，在所有管理器初始化后调用"""
        # 创建工具栏
        self.toolbar = self.toolbar_manager.create_toolbar()
        self.main_layout.addWidget(self.toolbar)
        
        # 创建缩略图面板
        self.thumbnail_list = self.thumbnail_manager.create_thumbnail_panel()
        
        # 添加到分割器
        self.splitter.addWidget(self.thumbnail_list)
        self.splitter.addWidget(self.scroll_area)
        
        # 设置分割器初始大小
        self.splitter.setSizes([200, 1000])
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, True)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        
        # 为分割器添加尺寸约束
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        
        self.main_layout.addWidget(self.splitter)
        
        # 添加浏览模式按钮
        self.toolbar_manager.add_browsing_viewtype_buttons()
        
        # 创建菜单
        self.create_menus()
        
        # 初始化禁用导航按钮
        self.navigation_controller.disable_navigation()
    
    def _on_splitter_moved(self, _, index):
        """处理分割器移动事件"""
        pass
    
    def eventFilter(self, obj, event):
        """事件过滤器,监听scroll_area的背景色变化"""
        try:
            # 避免无限递归：不处理由update_content_background触发的PaletteChange事件
            if obj == self.scroll_area and event.type() == QEvent.Type.PaletteChange:
                # 背景色变化时，更新内容区域的背景色
                # 使用一个标志来防止无限递归
                if not hasattr(self, '_updating_bg') or not self._updating_bg:
                    self._updating_bg = True
                    try:
                        self.update_content_background()
                    finally:
                        self._updating_bg = False
        except RuntimeError as e:
            if 'wrapped C/C++ object has been deleted' in str(e):
                # 忽略已删除对象的错误
                pass
            else:
                raise
        return super().eventFilter(obj, event)
    
    def update_content_background(self):
        """更新内容区域的背景色,确保所有子部件使用相同的背景色"""
        try:
            # 检查scroll_area是否有效
            if not hasattr(self, 'scroll_area') or not self.scroll_area:
                return
            
            # 获取当前背景色
            bg_color = self.scroll_area.palette().color(self.scroll_area.backgroundRole())
            
            # 设置scroll_area和center_container的背景色
            # 直接设置背景色，不使用样式表，避免触发PaletteChange事件
            
            # 更新scroll_area的背景色
            palette = self.scroll_area.palette()
            palette.setColor(self.scroll_area.backgroundRole(), bg_color)
            self.scroll_area.setPalette(palette)
            
            # 更新center_container的背景色
            if self.scroll_area.widget():
                center_container = self.scroll_area.widget()
                center_palette = center_container.palette()
                center_palette.setColor(center_container.backgroundRole(), bg_color)
                center_container.setPalette(center_palette)
            
            # 更新缩略图列表的背景色
            if hasattr(self, 'thumbnail_list') and self.thumbnail_list:
                try:
                    if hasattr(self.thumbnail_list, 'update_background'):
                        self.thumbnail_list.update_background()
                    else:
                        # 直接设置缩略图列表的背景色
                        thumbnail_palette = self.thumbnail_list.palette()
                        thumbnail_palette.setColor(self.thumbnail_list.backgroundRole(), bg_color)
                        self.thumbnail_list.setPalette(thumbnail_palette)
                except Exception as e:
                    self.logger.error(f"更新缩略图背景色失败: {str(e)}")
            
            # 更新页面标签的背景色（如果存在）
            if hasattr(self, 'viewtype_manager') and self.viewtype_manager.current_viewtype:
                current_viewtype = self.viewtype_manager.current_viewtype
                if hasattr(current_viewtype, 'page_label') and current_viewtype.page_label:
                    page_label_palette = current_viewtype.page_label.palette()
                    page_label_palette.setColor(current_viewtype.page_label.backgroundRole(), bg_color)
                    current_viewtype.page_label.setPalette(page_label_palette)
        except RuntimeError as e:
            if 'wrapped C/C++ object has been deleted' in str(e):
                # 忽略已删除对象的错误
                pass
            else:
                self.logger.error(f"更新内容背景色失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"更新内容背景色失败: {str(e)}")
    
    def create_menus(self):
        """创建菜单"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')
        
        open_action = QAction('打开(&O)...', self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.setStatusTip('打开PDF文件 (Ctrl+O)')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出(&X)', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip('退出程序 (Ctrl+Q)')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图(&V)')
        
        # 浏览模式子菜单
        view_mode_menu = view_menu.addMenu('浏览模式(&M)')
        
        single_page_action = QAction('单页浏览(&S)', self)
        single_page_action.setShortcut('Ctrl+1')
        single_page_action.triggered.connect(self.navigation_controller.switch_to_single_page)
        view_mode_menu.addAction(single_page_action)
        
        single_continuous_action = QAction('单页连续(&C)', self)
        single_continuous_action.setShortcut('Ctrl+2')
        single_continuous_action.triggered.connect(self.navigation_controller.switch_to_single_page_continuous)
        view_mode_menu.addAction(single_continuous_action)
        
        two_page_action = QAction('双页浏览(&T)', self)
        two_page_action.setShortcut('Ctrl+3')
        two_page_action.triggered.connect(self.navigation_controller.switch_to_two_page_spread)
        view_mode_menu.addAction(two_page_action)
        
        two_continuous_action = QAction('双页连续(&D)', self)
        two_continuous_action.setShortcut('Ctrl+4')
        two_continuous_action.triggered.connect(self.navigation_controller.switch_to_two_page_spread_continuous)
        view_mode_menu.addAction(two_continuous_action)
        
        view_menu.addSeparator()
        
        # 缩放菜单
        zoom_in_action = QAction('放大(&I)', self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.setStatusTip('放大页面 (Ctrl++)')
        zoom_in_action.triggered.connect(self.zoom_controller.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('缩小(&O)', self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.setStatusTip('缩小页面 (Ctrl+-)')
        zoom_out_action.triggered.connect(self.zoom_controller.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        view_menu.addSeparator()
        
        actual_size_action = QAction('实际大小(&A)', self)
        actual_size_action.setShortcut('Ctrl+0')
        actual_size_action.setStatusTip('设置为实际大小 (100%)')
        actual_size_action.triggered.connect(self.zoom_controller.zoom_actual_size)
        view_menu.addAction(actual_size_action)
        
        fit_page_action = QAction('适合页面(&P)', self)
        fit_page_action.setShortcut('Ctrl+9')
        fit_page_action.setStatusTip('缩放以适应整个页面')
        fit_page_action.triggered.connect(self.zoom_controller.zoom_fit_page)
        view_menu.addAction(fit_page_action)
        
        fit_width_action = QAction('适合宽度(&W)', self)
        fit_width_action.setShortcut('Ctrl+8')
        fit_width_action.setStatusTip('缩放以适应页面宽度')
        fit_width_action.triggered.connect(self.zoom_controller.zoom_fit_width)
        view_menu.addAction(fit_width_action)
        
        # 导航菜单
        nav_menu = menubar.addMenu('导航(&N)')
        
        first_page_action = QAction('首页(&F)', self)
        first_page_action.setShortcut('Ctrl+Home')
        first_page_action.setStatusTip('跳转到第一页')
        first_page_action.triggered.connect(self._go_to_first_page)
        nav_menu.addAction(first_page_action)
        
        prev_page_action = QAction('上一页(&P)', self)
        prev_page_action.setShortcut('Ctrl+PageUp')
        prev_page_action.setStatusTip('跳转到上一页')
        prev_page_action.triggered.connect(self.navigation_controller.prev_page)
        nav_menu.addAction(prev_page_action)
        
        next_page_action = QAction('下一页(&N)', self)
        next_page_action.setShortcut('Ctrl+PageDown')
        next_page_action.setStatusTip('跳转到下一页')
        next_page_action.triggered.connect(self.navigation_controller.next_page)
        nav_menu.addAction(next_page_action)
        
        last_page_action = QAction('末页(&L)', self)
        last_page_action.setShortcut('Ctrl+End')
        last_page_action.setStatusTip('跳转到最后一页')
        last_page_action.triggered.connect(self._go_to_last_page)
        nav_menu.addAction(last_page_action)
        
        nav_menu.addSeparator()
        
        reading_mode_action = QAction('阅读模式(&R)', self)
        reading_mode_action.setCheckable(True)
        reading_mode_action.setShortcut('F11')
        reading_mode_action.setStatusTip('切换阅读模式')
        reading_mode_action.triggered.connect(self.toggle_reading_mode)
        nav_menu.addAction(reading_mode_action)
    
    def _go_to_first_page(self):
        """跳转到第一页"""
        if self.pdf_manager.is_open and self.total_pages > 0:
            self.show_page(0)
    
    def _go_to_last_page(self):
        """跳转到最后页"""
        if self.pdf_manager.is_open and self.total_pages > 0:
            self.show_page(self.total_pages - 1)
    
    def toggle_reading_mode(self):
        """切换阅读模式"""
        self.reading_mode = not self.reading_mode
        
        if self.reading_mode:
            # 进入阅读模式
            self.status_bar.showMessage("阅读模式: 已启用")
            # 隐藏缩略图面板
            self.splitter.setSizes([0, self.width()])
        else:
            # 退出阅读模式
            self.status_bar.showMessage("阅读模式: 已禁用")
            # 显示缩略图面板
            self.splitter.setSizes([200, self.width() - 200])
    
    def open_file(self, filename=None):
        """打开PDF文件"""
        # 选择文件
        filename = self._select_file(filename)
        if not filename:
            return
            
        resource_manager = ResourceManager()
        
        try:
            # 显示忙碌指示器
            self.show_busy_indicator("打开PDF文件...")
            
            # 打开文档
            self._open_document(filename)
            
            # 生成缩略图
            self._generate_thumbnails(filename)
            
            # 初始化视图
            self._initialize_view()
            
            # 更新状态信息
            self.status_bar.showMessage(f"已打开: {os.path.basename(filename)}, 共{self.total_pages}页")
            
        except Exception as e:
            self._handle_open_file_error(e, filename)
        finally:
            # 隐藏忙碌指示器
            self.hide_busy_indicator()
    
    def _select_file(self, filename):
        """选择PDF文件"""
        if not filename:
            filename, _ = QFileDialog.getOpenFileName(self, "打开PDF文件", "", "PDF文件 (*.pdf)")
        return filename
    
    def _open_document(self, filename):
        """打开PDF文档"""
        if self.pdf_service.open_document(filename):
            self.total_pages = self.pdf_service.get_page_count()
            self.current_page = 0
        else:
            raise Exception("Failed to open document")
        
        # 清除旧的缩略图
        self.thumbnail_list.clear()
    
    def _generate_thumbnails(self, filename):
        """生成缩略图"""
        try:
            self.thumbnail_manager.generate_thumbnails(
                self.pdf_manager.doc, 
                self.pdf_manager.doc_mutex
            )
        except FileNotFoundError as e:
            error_info = handle_exception(e, self.logger, {"action": "generate_thumbnails", "file": filename})
            QMessageBox.warning(self, "警告", f"生成缩略图失败: {error_info.message}")
        except PermissionError as e:
            error_info = handle_exception(e, self.logger, {"action": "generate_thumbnails", "file": filename})
            QMessageBox.warning(self, "警告", f"生成缩略图失败: {error_info.message}")
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "generate_thumbnails", "file": filename})
            QMessageBox.warning(self, "警告", f"生成缩略图失败: {error_info.message}")
    
    def _initialize_view(self):
        """初始化视图"""
        # 显示第一页
        self.show_page(self.current_page)
        
        # 激活默认视图类型
        try:
            self.viewtype_manager.current_viewtype.activate()
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "activate_viewtype"})
            QMessageBox.warning(self, "警告", f"激活视图类型失败: {error_info.message}")
        
        # 启用导航按钮
        self.navigation_controller.enable_navigation()
    
    def _handle_open_file_error(self, e, filename):
        """处理打开文件时的错误"""
        error_info = handle_exception(e, self.logger, {"action": "open_file", "file": filename})
        QMessageBox.critical(self, "错误", f"打开PDF文件失败: {error_info.message}")
        self.navigation_controller.disable_navigation()
    
    def show_page(self, page_num):
        """显示指定页码的页面"""
        # 确保页码有效
        if not self._is_valid_page(page_num):
            return
            
        # 标记用户操作开始
        self._mark_user_operation_start()
        
        try:
            # 先尝试显示页面
            self._display_page_content(page_num)
            
            # 显示成功后再更新页码
            self.current_page = page_num
            
            # 更新UI状态
            self._update_ui_state(page_num)
            
            # 更新状态栏信息
            self._update_status_bar(page_num)
            
            # 预加载页面
            self._preload_pages(page_num)
        except Exception as e:
            self.logger.error(f"显示页面失败: {e}")
            # 恢复页码输入框显示
            self.navigation_controller.update_page_input()
        finally:
            # 标记用户操作完成
            self._mark_user_operation_end()
    
    def _is_valid_page(self, page_num):
        """检查页码是否有效"""
        if page_num < 0 or page_num >= self.total_pages:
            logging.warning(f"Invalid page number: {page_num}, total pages: {self.total_pages}")
            return False
        return True
    
    def _mark_user_operation_start(self):
        """标记用户操作开始"""
        if hasattr(self, 'thumbnail_manager'):
            self.thumbnail_manager.set_user_operation_in_progress(True)
    
    def _mark_user_operation_end(self):
        """标记用户操作完成"""
        if hasattr(self, 'thumbnail_manager'):
            try:
                self.thumbnail_manager.set_user_operation_in_progress(False)
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "set_user_operation"})
                self.logger.error(f"标记用户操作完成失败: {error_info.message}")
    
    def _display_page_content(self, page_num):
        """显示页面内容"""
        current_viewtype = self.viewtype_manager.current_viewtype
        if current_viewtype:
            try:
                current_viewtype.show_page(page_num)
            except FileNotFoundError as e:
                error_info = handle_exception(e, self.logger, {"action": "show_page", "page_num": page_num})
                self.logger.error(f"显示页面失败: {error_info.message}")
            except PermissionError as e:
                error_info = handle_exception(e, self.logger, {"action": "show_page", "page_num": page_num})
                self.logger.error(f"显示页面失败: {error_info.message}")
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "show_page", "page_num": page_num})
                self.logger.error(f"显示页面失败: {error_info.message}")
    
    def _update_ui_state(self, page_num):
        """更新UI状态"""
        try:
            self.thumbnail_manager.update_current_page(page_num)
            self.navigation_controller.update_page_input()
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "update_ui_state", "page_num": page_num})
            self.logger.error(f"更新UI状态失败: {error_info.message}")
    
    def _update_status_bar(self, page_num):
        """更新状态栏信息"""
        try:
            zoom_level = self.zoom_service.get_zoom_level()
            browsing_mode = self.viewtype_manager.get_current_viewtype_name()
            
            # 更新状态栏消息
            self.status_bar.showMessage(f"已打开: {self.pdf_manager.get_file_path() or '未打开文件'}")
            
            # 更新信息标签
            self.status_page_label.setText(f"第 {page_num + 1}/{self.total_pages} 页")
            self.status_zoom_label.setText(f"缩放: {int(zoom_level * 100)}%")
            
            # 转换视图模式名称为中文
            mode_names = {
                "single_page": "单页浏览",
                "single_page_continuous": "单页连续",
                "two_page_spread": "双页浏览",
                "two_page_spread_continuous": "双页连续",
            }
            self.status_mode_label.setText(mode_names.get(browsing_mode, browsing_mode))
            
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "update_status_bar", "page_num": page_num})
            self.logger.error(f"更新状态栏信息失败: {error_info.message}")
    
    def show_busy_indicator(self, text="处理中..."):
        """显示忙碌指示器并设置提示文本"""
        self.status_bar.showMessage(text)
        self.busy_indicator.setVisible(True)
    
    def hide_busy_indicator(self):
        """隐藏忙碌指示器"""
        self.busy_indicator.setVisible(False)
        # 恢复显示当前页面信息
        self._update_status_bar(self.current_page)
    
    def _preload_pages(self, current_page):
        """预加载前后几页到缓存中"""
        # 使用PDFService预加载页面（使用当前缩放级别）
        preload_range = Constants.PRELOAD_RANGE.value
        zoom_level = self.zoom_service.get_zoom_level()
        self.pdf_service.preload_pages(current_page, preload_range, zoom_level)
    
    def get_current_page(self):
        """获取当前页码"""
        return self.current_page
    
    def get_total_pages(self):
        """获取总页数"""
        return self.total_pages
    
    def get_pdf_manager(self):
        """获取PDF管理器"""
        return self.pdf_manager
    
    def get_page_cache(self):
        """获取页面缓存"""
        return self.page_cache
    

    
    def get_page_renderer(self):
        """获取页面渲染器"""
        return self.page_renderer
    
    def get_viewtype_manager(self):
        """获取视图类型管理器"""
        return self.viewtype_manager
    
    def get_scroll_area(self):
        """获取滚动区域"""
        return self.scroll_area
    
    def get_status_bar(self):
        """获取状态栏"""
        return self.status_bar
    
    def _get_page_pixmap(self, page_num):
        """获取指定页码的页面Pixmap（同步方法）"""
        # 使用PDFService渲染页面（使用当前缩放级别）
        zoom_level = self.zoom_service.get_zoom_level()
        pixmap = self.pdf_service.render_page(page_num, zoom_level)
        
        if pixmap:
            return pixmap
        
        # 如果渲染失败，创建一个错误信息的pixmap
        self.logger.error(f"Failed to render page {page_num}")
        error_pixmap = QPixmap(800, 600)
        error_pixmap.fill(Qt.GlobalColor.white)
        painter = QPainter(error_pixmap)
        painter.setPen(Qt.GlobalColor.red)
        painter.setFont(QFont("Arial", 16))
        error_text = f"页面 {page_num + 1} 渲染失败\n请尝试重新加载或缩放"
        painter.drawText(error_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, error_text)
        painter.end()
        return error_pixmap
    
    def _get_page_pixmap_async(self, page_num, callback):
        """异步获取指定页码的页面Pixmap"""
        # 使用PDFService异步渲染页面（使用当前缩放级别）
        zoom_level = self.zoom_service.get_zoom_level()
        
        # 提交异步渲染请求
        # 注意：渲染结果将通过事件总线的render_completed事件处理
        # 这里保留callback参数是为了保持向后兼容
        request_id = self.pdf_service.render_page_async(page_num, zoom_level, priority=0)
        return request_id
    
    def _get_two_pages_pixmap_async(self, page1_num, page2_num, callback):
        """异步获取双页的合并Pixmap"""
        # 注意：渲染结果将通过事件总线的render_completed事件处理
        # 这里保留callback参数是为了保持向后兼容
        # 异步获取两个页面的pixmap
        self._get_page_pixmap_async(page1_num, None)
        self._get_page_pixmap_async(page2_num, None)
    
    def _merge_two_pages(self, page1_num, page2_num, page1_pixmap=None, page2_pixmap=None):
        """合并两页为一个pixmap"""
        if not page1_pixmap:
            page1_pixmap = self._get_page_pixmap(page1_num)
        if not page2_pixmap:
            page2_pixmap = self._get_page_pixmap(page2_num) if page2_num != page1_num else None
        
        if page1_pixmap:
            spacing = Constants.PAGE_SPACING.value
            width = page1_pixmap.width() + (page2_pixmap.width() if page2_pixmap else 0) + (spacing if page2_pixmap else 0)
            height = max(page1_pixmap.height(), page2_pixmap.height() if page2_pixmap else 0)
            
            combined_pixmap = QPixmap(width, height)
            
            # 检查scroll_area是否有效
            try:
                if hasattr(self, 'scroll_area') and self.scroll_area:
                    bg_color = self.scroll_area.palette().color(self.scroll_area.backgroundRole())
                else:
                    # 使用默认背景色
                    bg_color = QColor(255, 255, 255)  # 白色
            except RuntimeError as e:
                if 'wrapped C/C++ object has been deleted' in str(e):
                    # 使用默认背景色
                    bg_color = QColor(255, 255, 255)  # 白色
                else:
                    raise
            
            combined_pixmap.fill(bg_color)
            
            painter = QPainter(combined_pixmap)
            
            # 绘制第一页，垂直居中
            page1_y = (height - page1_pixmap.height()) // 2
            painter.drawPixmap(0, page1_y, page1_pixmap)
            
            # 绘制第二页，垂直居中
            if page2_pixmap:
                page2_y = (height - page2_pixmap.height()) // 2
                painter.drawPixmap(page1_pixmap.width() + spacing, page2_y, page2_pixmap)
            
            painter.end()
            
            return combined_pixmap
        return None
    
    def _update_content_layout(self):
        """更新内容布局，确保页面正确显示"""
        if hasattr(self, 'content_area'):
            self.content_area.update_layout()
        # 移除QApplication.processEvents()调用，避免事件处理混乱
        # 强制处理所有待处理事件，确保UI立即更新
        # from PyQt5.QtWidgets import QApplication
        # QApplication.processEvents()
    
    def resizeEvent(self, event):
        """处理窗口大小变化事件"""
        super().resizeEvent(event)
        
        # 检查scroll_area是否有效
        if hasattr(self, 'scroll_area') and self.scroll_area:
            # 更新内容区域背景色
            self.update_content_background()
        
        # 如果当前视图类型已激活，更新布局
        if hasattr(self, 'viewtype_manager') and self.viewtype_manager.current_viewtype:
            current_viewtype = self.viewtype_manager.current_viewtype
            if current_viewtype.is_active:
                current_viewtype.update_config()
        
        # 强制更新布局
        self._update_content_layout()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        key = event.key()
        modifiers = event.modifiers()
        
        # 处理全局快捷键（即使没有打开PDF文件也有效）
        # F11 - 切换阅读模式
        if key == Qt.Key.Key_F11:
            self.toggle_reading_mode()
            return
        
        # Ctrl+O - 打开文件
        if key == Qt.Key.Key_O and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.open_file()
            return
        
        # 检查是否有打开的PDF文件
        if not self.pdf_manager.is_open or self.total_pages == 0:
            super().keyPressEvent(event)
            return
        
        # 处理Ctrl+数字键 - 切换浏览模式
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_1:
                self.navigation_controller.switch_to_single_page()
                return
            elif key == Qt.Key.Key_2:
                self.navigation_controller.switch_to_single_page_continuous()
                return
            elif key == Qt.Key.Key_3:
                self.navigation_controller.switch_to_two_page_spread()
                return
            elif key == Qt.Key.Key_4:
                self.navigation_controller.switch_to_two_page_spread_continuous()
                return
            elif key == Qt.Key.Key_0:
                self.zoom_controller.zoom_actual_size()
                return
            elif key == Qt.Key.Key_8:
                self.zoom_controller.zoom_fit_width()
                return
            elif key == Qt.Key.Key_9:
                self.zoom_controller.zoom_fit_page()
                return
            elif key == Qt.Key.Key_Home:
                self._go_to_first_page()
                return
            elif key == Qt.Key.Key_End:
                self._go_to_last_page()
                return
            elif key == Qt.Key.Key_PageUp:
                self.navigation_controller.prev_page()
                return
            elif key == Qt.Key.Key_PageDown:
                self.navigation_controller.next_page()
                return
        
        # 处理Ctrl++ / Ctrl+- 缩放
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal:
                self.zoom_controller.zoom_in()
                return
            elif key == Qt.Key.Key_Minus:
                self.zoom_controller.zoom_out()
                return
        
        # 处理Page Up和Page Down键 - 在每个浏览模式内都有效
        if key == Qt.Key.Key_PageUp:
            self._handle_page_up()
            return
        elif key == Qt.Key.Key_PageDown:
            self._handle_page_down()
            return
        
        # 处理Home键 - 跳转到首页
        if key == Qt.Key.Key_Home:
            self._go_to_first_page()
            return
        
        # 处理End键 - 跳转到最后页
        if key == Qt.Key.Key_End:
            self._go_to_last_page()
            return
        
        # 处理方向键
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
            self._handle_arrow_keys(event, key)
            return
        
        # 其他键交给父类处理
        super().keyPressEvent(event)
    
    def _handle_page_up(self):
        """处理Page Up键"""
        # 检查scroll_area是否有效
        if not self._is_scroll_area_valid():
            return
        
        try:
            v_scroll = self.scroll_area.verticalScrollBar()
            if not v_scroll:
                return
            
            current_value = v_scroll.value()
            viewport_height = self.viewport_manager.get_viewport_height()
            page_step = self._calculate_page_step(viewport_height)
            new_value = max(0, current_value - page_step)
            
            if new_value == 0 and self.current_page > 0:
                self._handle_page_up_at_top(v_scroll)
            else:
                # 在当前页面内向上滚动
                v_scroll.setValue(new_value)
        except RuntimeError as e:
            if 'wrapped C/C++ object has been deleted' in str(e):
                # 忽略已删除对象的错误
                pass
            else:
                raise
    
    def _is_scroll_area_valid(self):
        """检查scroll_area是否有效"""
        return hasattr(self, 'scroll_area') and self.scroll_area
    
    def _calculate_page_step(self, viewport_height):
        """计算翻页步长"""
        return int(viewport_height * 0.75)
    
    def _handle_page_up_at_top(self, v_scroll):
        """处理页面顶部的Page Up操作"""
        prev_page = self._calculate_previous_page()
        self.show_page(prev_page)
        # 滚动到新页面底部
        if v_scroll.maximum() > 0:
            v_scroll.setValue(v_scroll.maximum())
    
    def _calculate_previous_page(self):
        """计算前一页的页码"""
        # 使用统一的视图类型服务判断双页模式
        if self.viewtype_service.is_two_page_mode():
            # 在双页浏览模式下，以双页为单位向前翻页
            return max(0, self.current_page - 2)
        else:
            # 在其他浏览模式下，以单页为单位向前翻页
            return max(0, self.current_page - 1)
    
    def _handle_page_down(self):
        """处理Page Down键"""
        # 检查scroll_area是否有效
        if not self._is_scroll_area_valid():
            return
        
        try:
            v_scroll = self.scroll_area.verticalScrollBar()
            if not v_scroll:
                return
            
            current_value = v_scroll.value()
            max_value = v_scroll.maximum()
            viewport_height = self.viewport_manager.get_viewport_height()
            page_step = self._calculate_page_step(viewport_height)
            new_value = min(max_value, current_value + page_step)
            
            if new_value == max_value and self.current_page < self.total_pages - 1:
                self._handle_page_down_at_bottom(v_scroll)
            else:
                # 在当前页面内向下滚动
                v_scroll.setValue(new_value)
        except RuntimeError as e:
            if 'wrapped C/C++ object has been deleted' in str(e):
                # 忽略已删除对象的错误
                pass
            else:
                raise
    
    def _handle_page_down_at_bottom(self, v_scroll):
        """处理页面底部的Page Down操作"""
        next_page = self._calculate_next_page()
        self.show_page(next_page)
        # 滚动到新页面顶部
        v_scroll.setValue(0)
    
    def _calculate_next_page(self):
        """计算后一页的页码"""
        # 使用统一的视图类型服务判断双页模式
        if self.viewtype_service.is_two_page_mode():
            # 在双页浏览模式下，以双页为单位向后翻页
            return min(self.total_pages - 1, self.current_page + 2)
        else:
            # 在其他浏览模式下，以单页为单位向后翻页
            return min(self.total_pages - 1, self.current_page + 1)
    
    def _handle_arrow_keys(self, event, key):
        """处理方向键"""
        # 检查scroll_area是否有效
        if not self._is_scroll_area_valid():
            super().keyPressEvent(event)
            return
        
        try:
            # 检查视图类型是否激活
            if not self._is_viewtype_active():
                super().keyPressEvent(event)
                return
            
            # 获取滚动条
            h_scroll, v_scroll = self._get_scrollbars()
            if not h_scroll or not v_scroll:
                super().keyPressEvent(event)
                return
            
            # 获取视口和页面尺寸
            viewport_width, viewport_height, page_width, page_height = self._get_viewport_and_page_size()
            
            # 检查页面是否大于视口
            if page_width > viewport_width or page_height > viewport_height:
                # 定义移动步长
                move_step = 20
                
                # 处理方向键
                if key == Qt.Key.Up:
                    self._handle_up_arrow(v_scroll, move_step)
                elif key == Qt.Key.Down:
                    self._handle_down_arrow(v_scroll, move_step)
                elif key == Qt.Key.Left:
                    self._handle_left_arrow(h_scroll, move_step)
                elif key == Qt.Key.Right:
                    self._handle_right_arrow(h_scroll, move_step)
        except RuntimeError as e:
            if 'wrapped C/C++ object has been deleted' in str(e):
                # 忽略已删除对象的错误
                super().keyPressEvent(event)
            else:
                raise
    
    def _is_viewtype_active(self):
        """检查视图类型是否激活"""
        current_viewtype = self.viewtype_manager.current_viewtype
        return current_viewtype and current_viewtype.is_active
    
    def _get_scrollbars(self):
        """获取滚动条"""
        scroll_area = self.scroll_area
        h_scroll = scroll_area.horizontalScrollBar()
        v_scroll = scroll_area.verticalScrollBar()
        return h_scroll, v_scroll
    
    def _get_viewport_and_page_size(self):
        """获取视口和页面尺寸"""
        # 从ViewportManager获取视口尺寸
        viewport_width = self.viewport_manager.get_viewport_width()
        viewport_height = self.viewport_manager.get_viewport_height()
        
        # 获取当前页面尺寸（使用当前缩放级别）
        zoom_level = self.zoom_service.get_zoom_level()
        page_size = self.pdf_service.get_page_size(
            self.current_page,
            zoom_level
        )
        
        page_width, page_height = page_size
        return viewport_width, viewport_height, page_width, page_height
    
    def _handle_up_arrow(self, v_scroll, move_step):
        """处理向上箭头"""
        current_value = v_scroll.value()
        if current_value > 0:
            # 页面可以向上移动
            new_value = max(0, current_value - move_step)
            v_scroll.setValue(new_value)
        else:
            # 页面已到达顶部，向前翻页
            if self.current_page > 0:
                self.navigation_controller.prev_page()
                # 滚动到新页面底部
                if v_scroll.maximum() > 0:
                    v_scroll.setValue(v_scroll.maximum())
    
    def _handle_down_arrow(self, v_scroll, move_step):
        """处理向下箭头"""
        current_value = v_scroll.value()
        if current_value < v_scroll.maximum():
            # 页面可以向下移动
            new_value = min(v_scroll.maximum(), current_value + move_step)
            v_scroll.setValue(new_value)
        else:
            # 页面已到达底部，向后翻页
            if self.current_page < self.total_pages - 1:
                self.navigation_controller.next_page()
                # 滚动到新页面顶部
                v_scroll.setValue(0)
    
    def _handle_left_arrow(self, h_scroll, move_step):
        """处理向左箭头"""
        current_value = h_scroll.value()
        if current_value > 0:
            new_value = max(0, current_value - move_step)
            h_scroll.setValue(new_value)
    
    def _handle_right_arrow(self, h_scroll, move_step):
        """处理向右箭头"""
        current_value = h_scroll.value()
        if current_value < h_scroll.maximum():
            new_value = min(h_scroll.maximum(), current_value + move_step)
            h_scroll.setValue(new_value)
    
    def closeEvent(self, event):
        """关闭窗口时的事件处理"""
        resource_manager = ResourceManager()
        
        try:
            # 设置关闭标志
            self._is_closing = True
            
            # 清理各种资源
            self._cleanup_viewport_manager()
            self._cleanup_thumbnail_manager()
            self._cleanup_page_cache()
            self._cleanup_logs()
            self._cleanup_process_files()
        except RuntimeError as e:
            if 'wrapped C/C++ object has been deleted' in str(e):
                # 忽略已删除对象的错误
                pass
            else:
                error_info = handle_exception(e, self.logger, {"action": "cleanup_resources"})
                self.logger.error(f"清理资源失败: {error_info.message}")
        except Exception as e:
            error_info = handle_exception(e, self.logger, {"action": "cleanup_resources"})
            self.logger.error(f"清理资源失败: {error_info.message}")
        finally:
            event.accept()
    
    def _cleanup_viewport_manager(self):
        """清理视口管理器"""
        if hasattr(self, 'viewport_manager') and self.viewport_manager:
            try:
                # 先禁用监听，避免在清理过程中触发事件
                self.viewport_manager.enable_listening(False)
                # 手动清理视口管理器的资源，避免在__del__中访问已删除的对象
                with self.viewport_manager._lock:
                    # 移除事件过滤器（小心处理，避免访问已删除的对象）
                    if self.viewport_manager._scroll_area:
                        try:
                            # 尝试访问scroll_area的基本属性，检查是否有效
                            _ = self.viewport_manager._scroll_area.objectName()
                            self.viewport_manager._scroll_area.removeEventFilter(self.viewport_manager)
                        except RuntimeError as e:
                            if 'wrapped C/C++ object has been deleted' in str(e):
                                # 忽略已删除对象的错误
                                pass
                            else:
                                error_info = handle_exception(e, self.logger, {"action": "remove_event_filter"})
                                self.logger.error(f"移除事件过滤器失败: {error_info.message}")
                        except Exception as e:
                            error_info = handle_exception(e, self.logger, {"action": "remove_event_filter"})
                            self.logger.error(f"移除事件过滤器失败: {error_info.message}")
                    # 清空观察者列表
                    with self.viewport_manager._observers_lock:
                        self.viewport_manager._observers.clear()
                    # 重置状态
                    self.viewport_manager._scroll_area = None
                    self.viewport_manager._viewport_width = 0.0
                    self.viewport_manager._viewport_height = 0.0
                    self.viewport_manager._viewport_size = (0.0, 0.0)
                    self.viewport_manager._listening_enabled = False
                # 最后设置为None
                self.viewport_manager = None
            except RuntimeError as e:
                if 'wrapped C/C++ object has been deleted' in str(e):
                    # 忽略已删除对象的错误
                    pass
                else:
                    error_info = handle_exception(e, self.logger, {"action": "cleanup_viewport_manager"})
                    self.logger.error(f"清理视口管理器失败: {error_info.message}")
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "cleanup_viewport_manager"})
                self.logger.error(f"清理视口管理器失败: {error_info.message}")
    
    def _cleanup_thumbnail_manager(self):
        """清理缩略图管理器"""
        if hasattr(self, 'thumbnail_manager') and self.thumbnail_manager:
            # 直接停止生成器，不尝试访问任何可能已销毁的对象
            try:
                if hasattr(self.thumbnail_manager, 'thumbnail_generator') and self.thumbnail_manager.thumbnail_generator:
                    self.thumbnail_manager.thumbnail_generator.running = False
                    self.thumbnail_manager.thumbnail_generator = None
            except RuntimeError as e:
                if 'wrapped C/C++ object has been deleted' in str(e):
                    # 忽略已删除对象的错误
                    pass
                else:
                    error_info = handle_exception(e, self.logger, {"action": "cleanup_thumbnail_generator"})
                    self.logger.error(f"清理缩略图生成器失败: {error_info.message}")
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "cleanup_thumbnail_generator"})
                self.logger.error(f"清理缩略图生成器失败: {error_info.message}")
            
            # 清理thumbnail_sync对象
            try:
                self.thumbnail_manager.thumbnail_sync = None
            except RuntimeError as e:
                if 'wrapped C/C++ object has been deleted' in str(e):
                    # 忽略已删除对象的错误
                    pass
                else:
                    error_info = handle_exception(e, self.logger, {"action": "cleanup_thumbnail_sync"})
                    self.logger.error(f"清理thumbnail_sync失败: {error_info.message}")
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "cleanup_thumbnail_sync"})
                self.logger.error(f"清理thumbnail_sync失败: {error_info.message}")
    
    def _cleanup_page_cache(self):
        """清理页面缓存"""
        if hasattr(self, 'page_cache') and self.page_cache:
            try:
                self.page_cache.clear()
            except RuntimeError as e:
                if 'wrapped C/C++ object has been deleted' in str(e):
                    # 忽略已删除对象的错误
                    pass
                else:
                    error_info = handle_exception(e, self.logger, {"action": "clear_page_cache"})
                    self.logger.error(f"清理页面缓存失败: {error_info.message}")
            except Exception as e:
                error_info = handle_exception(e, self.logger, {"action": "clear_page_cache"})
                self.logger.error(f"清理页面缓存失败: {error_info.message}")
            
            # 关闭文档
            if hasattr(self, 'pdf_service') and self.pdf_service:
                try:
                    self.pdf_service.close_document()
                except RuntimeError as e:
                    if 'wrapped C/C++ object has been deleted' in str(e):
                        # 忽略已删除对象的错误
                        pass
                    else:
                        error_info = handle_exception(e, self.logger, {"action": "close_document"})
                        self.logger.error(f"关闭文档失败: {error_info.message}")
                except Exception as e:
                    error_info = handle_exception(e, self.logger, {"action": "close_document"})
                    self.logger.error(f"关闭文档失败: {error_info.message}")
    
    def _cleanup_logs(self):
        """清理日志文件"""
        try:
            log_file = 'pdf_viewer.log'
            if os.path.exists(log_file):
                # 检查日志文件大小，如果超过10MB则清理
                if os.path.getsize(log_file) > 10 * 1024 * 1024:
                    with open(log_file, 'w') as f:
                        f.write(f"# 日志文件已清理 - {datetime.now().isoformat()}\n")
                    logging.info("日志文件已清理")
        except Exception as e:
            self.logger.error(f"清理日志文件失败: {str(e)}")
    
    def _cleanup_process_files(self):
        """清理过程文件"""
        try:
            # 清理磁盘缓存目录
            cache_dir = os.path.join(os.path.expanduser("~"), ".pdf_viewer_cache")
            if os.path.exists(cache_dir):
                # 计算缓存目录大小
                total_size = 0
                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            total_size += os.path.getsize(file_path)
                        except:
                            pass
                
                # 如果缓存目录超过50MB则清理
                if total_size > 50 * 1024 * 1024:
                    for root, dirs, files in os.walk(cache_dir):
                        for file in files:
                            if file.endswith('.cache'):
                                file_path = os.path.join(root, file)
                                try:
                                    os.remove(file_path)
                                except:
                                    pass
                    logging.info("磁盘缓存已清理")
        except Exception as e:
            self.logger.error(f"清理过程文件失败: {str(e)}")

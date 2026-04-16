#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工具栏管理类 - 现代化版本

功能：
- 创建和管理工具栏
- 添加图标+文字按钮
- 分段按钮组（视图模式切换）
- 现代化缩放控制
"""

from PyQt6.QtWidgets import (
    QToolBar, QLabel, QLineEdit, QSlider, QPushButton,
    QWidget, QHBoxLayout, QButtonGroup, QSpinBox, QSizePolicy,
    QToolButton, QMenu
)
from PyQt6.QtGui import QAction, QIcon, QFont
from PyQt6.QtCore import Qt, QSize, pyqtSignal

# 导入常量
from utils.constants import Constants
from ui.styles import get_colors, get_stylesheet


class SegmentedButtonGroup(QWidget):
    """分段按钮组 - 用于视图模式切换"""
    
    buttonClicked = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = []
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self.setLayout(layout)
        
        # 设置样式
        colors = get_colors()
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {colors.bg_content};
                border: 1px solid {colors.border};
                border-radius: 6px;
            }}
        """)
    
    def addButton(self, text: str, icon_text: str = None, tooltip: str = None) -> QPushButton:
        """添加按钮
        
        Args:
            text: 按钮文字
            icon_text: 图标字符（可选）
            tooltip: 提示文本（可选）
        """
        btn = QPushButton()
        
        # 设置按钮内容
        if icon_text:
            # 图标+文字
            btn.setText(f"{icon_text} {text}")
        else:
            btn.setText(text)
        
        if tooltip:
            btn.setToolTip(tooltip)
        
        # 设置样式
        colors = get_colors()
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                color: {colors.text_secondary};
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {colors.bg_hover};
                color: {colors.text_primary};
            }}
            QPushButton:checked {{
                background-color: {colors.bg_card};
                color: {colors.primary};
                border: 1px solid {colors.border};
            }}
        """)
        
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 添加到按钮组
        index = len(self.buttons)
        self.button_group.addButton(btn, index)
        self.buttons.append(btn)
        self.layout().addWidget(btn)
        
        # 连接信号
        btn.clicked.connect(lambda: self.buttonClicked.emit(index))
        
        return btn
    
    def setChecked(self, index: int):
        """设置选中状态（仅更新UI，不触发信号）"""
        if 0 <= index < len(self.buttons):
            # 临时阻断信号，避免触发 clicked 信号
            self.buttons[index].blockSignals(True)
            self.buttons[index].setChecked(True)
            self.buttons[index].blockSignals(False)
    
    def _set_checked_and_emit(self, index: int):
        """设置选中状态并触发信号（用于用户交互）"""
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)
            self.buttonClicked.emit(index)
    
    def getCheckedIndex(self) -> int:
        """获取当前选中的索引"""
        checked_btn = self.button_group.checkedButton()
        return self.button_group.id(checked_btn) if checked_btn else -1


class ZoomControlWidget(QWidget):
    """缩放控制组件 - 紧凑的 +/- 按钮组"""
    
    zoomChanged = pyqtSignal(float)
    fitPageRequested = pyqtSignal()
    fitWidthRequested = pyqtSignal()
    actualSizeRequested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_levels = [20, 30, 40, 50, 60, 70, 80, 90, 100, 
                            110, 120, 150, 175, 200, 250, 300, 400, 500]
        self._current_zoom = 100
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        colors = get_colors()
        
        # 缩小按钮
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedSize(28, 28)
        self.zoom_out_btn.setToolTip("缩小")
        self.zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        
        # 缩放百分比显示
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet(f"""
            color: {colors.text_primary};
            font-size: 13px;
            font-weight: 500;
        """)
        
        # 放大按钮
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(28, 28)
        self.zoom_in_btn.setToolTip("放大")
        self.zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        
        # 适合页面按钮
        self.fit_btn = QPushButton("⊡")
        self.fit_btn.setFixedSize(28, 28)
        self.fit_btn.setToolTip("适合页面")
        self.fit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fit_btn.clicked.connect(self.fitPageRequested.emit)
        
        # 适合宽度按钮
        self.fit_width_btn = QPushButton("⇔")
        self.fit_width_btn.setFixedSize(28, 28)
        self.fit_width_btn.setToolTip("适合宽度")
        self.fit_width_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fit_width_btn.clicked.connect(self.fitWidthRequested.emit)
        
        # 设置按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: {colors.bg_card};
                border: 1px solid {colors.border};
                border-radius: 4px;
                color: {colors.text_primary};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors.bg_hover};
                border-color: {colors.text_secondary};
            }}
            QPushButton:pressed {{
                background-color: {colors.bg_selected};
                border-color: {colors.primary};
            }}
        """
        
        for btn in [self.zoom_out_btn, self.zoom_in_btn, self.fit_btn, self.fit_width_btn]:
            btn.setStyleSheet(btn_style)
            layout.addWidget(btn)
        
        layout.addWidget(self.zoom_label)
        
        self.setLayout(layout)
    
    def _zoom_in(self):
        """放大"""
        for level in self._zoom_levels:
            if level > self._current_zoom:
                self._set_zoom_and_emit(level)
                return
        self._set_zoom_and_emit(500)
    
    def _zoom_out(self):
        """缩小"""
        for level in reversed(self._zoom_levels):
            if level < self._current_zoom:
                self._set_zoom_and_emit(level)
                return
        self._set_zoom_and_emit(20)
    
    def _set_zoom_and_emit(self, zoom: float):
        """设置缩放比例并触发信号（用于用户交互）"""
        new_zoom = max(20, min(500, zoom))
        if abs(new_zoom - self._current_zoom) < 0.5:
            return
        self._current_zoom = new_zoom
        self.zoom_label.setText(f"{int(self._current_zoom)}%")
        self.zoomChanged.emit(self._current_zoom)
    
    def setZoom(self, zoom: float):
        """设置缩放比例（仅更新UI，不触发信号）"""
        new_zoom = max(20, min(500, zoom))
        # 如果缩放值没有变化，不触发信号避免递归
        if abs(new_zoom - self._current_zoom) < 0.5:
            self._current_zoom = new_zoom
            self.zoom_label.setText(f"{int(self._current_zoom)}%")
            return
        self._current_zoom = new_zoom
        self.zoom_label.setText(f"{int(self._current_zoom)}%")
    
    def getZoom(self) -> float:
        """获取当前缩放比例"""
        return self._current_zoom


class PageNavigator(QWidget):
    """页面导航组件 - 上一页/页码/下一页"""
    
    pageChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._total_pages = 0
        self._current_page = 1
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        colors = get_colors()
        
        # 上一页按钮
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(32, 28)
        self.prev_btn.setToolTip("上一页 (PageUp)")
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.clicked.connect(self._go_prev)
        
        # 页码输入框
        self.page_spin = QSpinBox()
        self.page_spin.setFixedWidth(60)
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(99999)
        self.page_spin.setValue(1)
        self.page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.page_spin.valueChanged.connect(self._on_page_changed)
        
        # 总页数标签
        self.total_label = QLabel("/ 1")
        self.total_label.setStyleSheet(f"color: {colors.text_secondary}; font-size: 13px;")
        
        # 下一页按钮
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(32, 28)
        self.next_btn.setToolTip("下一页 (PageDown)")
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self._go_next)
        
        # 设置样式
        btn_style = f"""
            QPushButton {{
                background-color: {colors.bg_card};
                border: 1px solid {colors.border};
                border-radius: 4px;
                color: {colors.text_primary};
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {colors.bg_hover};
                border-color: {colors.text_secondary};
            }}
            QPushButton:pressed {{
                background-color: {colors.bg_selected};
            }}
            QPushButton:disabled {{
                color: {colors.text_disabled};
                background-color: {colors.bg_hover};
            }}
        """
        
        input_style = f"""
            QSpinBox {{
                background-color: {colors.bg_card};
                border: 1px solid {colors.border};
                border-radius: 4px;
                padding: 4px 8px;
                color: {colors.text_primary};
                font-size: 13px;
            }}
            QSpinBox:focus {{
                border-color: {colors.primary};
            }}
        """
        
        self.prev_btn.setStyleSheet(btn_style)
        self.next_btn.setStyleSheet(btn_style)
        self.page_spin.setStyleSheet(input_style)
        
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.page_spin)
        layout.addWidget(self.total_label)
        layout.addWidget(self.next_btn)
        
        self.setLayout(layout)
    
    def _go_prev(self):
        """上一页"""
        if self._current_page > 1:
            new_page = self._current_page - 1
            self._set_page_and_emit(new_page)
    
    def _go_next(self):
        """下一页"""
        if self._current_page < self._total_pages:
            new_page = self._current_page + 1
            self._set_page_and_emit(new_page)
    
    def _set_page_and_emit(self, page: int):
        """设置页码并触发信号（用于用户交互）"""
        new_page = max(1, min(self._total_pages, page))
        if new_page == self._current_page:
            return
        self._current_page = new_page
        self.page_spin.setValue(self._current_page)
        self._update_buttons()
        self.pageChanged.emit(self._current_page)
    
    def _on_page_changed(self, value: int):
        """页码改变"""
        if value != self._current_page:
            self._current_page = value
            self.pageChanged.emit(value)
    
    def setPage(self, page: int):
        """设置当前页（仅更新UI，不触发信号）"""
        new_page = max(1, min(self._total_pages, page))
        if new_page == self._current_page:
            # 即使页码相同，也更新UI以确保显示一致
            self.page_spin.blockSignals(True)
            self.page_spin.setValue(self._current_page)
            self.page_spin.blockSignals(False)
            return
        self._current_page = new_page
        # 临时断开信号连接，避免触发pageChanged信号
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self._current_page)
        self.page_spin.blockSignals(False)
        self._update_buttons()
    
    def setTotalPages(self, total: int):
        """设置总页数"""
        self._total_pages = max(1, total)
        self.page_spin.setMaximum(self._total_pages)
        self.total_label.setText(f"/ {self._total_pages}")
        self._update_buttons()
    
    def _update_buttons(self):
        """更新按钮状态"""
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)
    
    def getCurrentPage(self) -> int:
        """获取当前页"""
        return self._current_page


class ToolbarManager:
    """
    工具栏管理类 - 现代化版本
    
    负责创建和管理工具栏，包括各种操作按钮和控件
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.toolbar = None
        
        # 组件引用
        self.page_navigator = None
        self.view_mode_group = None
        self.zoom_control = None
        
        # 旧版兼容引用
        self.page_input = None  # 兼容旧代码
        self.zoom_slider = None  # 兼容旧代码
        self.zoom_percentage_label = None  # 兼容旧代码
        
        # 视图模式按钮（兼容旧代码）
        self.single_page_btn = None
        self.single_page_continuous_btn = None
        self.two_page_spread_btn = None
        self.two_page_spread_continuous_btn = None
        
        # 导航按钮（兼容旧代码）
        self.prev_action = None
        self.next_action = None
        
        # 缩放控件（兼容旧代码）
        self.zoom_label = None
        self.actual_size_action = None
        self.fit_page_action = None
        self.fit_width_action = None
        self.zoom_in_action = None
        self.zoom_out_action = None
        
        # 图形检测按钮
        self.graphic_detection_action = None
        self.reading_mode_action = None
    
    def create_toolbar(self):
        """创建工具栏"""
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        
        # 应用样式
        colors = get_colors()
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {colors.toolbar_bg},
                    stop:1 #E8E8E8);
                border-bottom: 1px solid {colors.toolbar_border};
                padding: 6px 12px;
                spacing: 12px;
            }}
            QToolBar::separator {{
                background-color: {colors.border};
                width: 1px;
                height: 24px;
                margin: 4px 8px;
            }}
        """)
        
        # 添加工具栏按钮
        self._add_file_buttons()
        self.toolbar.addSeparator()
        self._add_navigation_section()
        self.toolbar.addSeparator()
        self._add_view_mode_section()
        self.toolbar.addSeparator()
        self._add_zoom_section()
        self.toolbar.addSeparator()
        self._add_reading_mode_button()
        
        return self.toolbar
    
    def _add_file_buttons(self):
        """添加文件相关按钮"""
        colors = get_colors()
        
        # 打开文件按钮 - 图标+文字
        open_btn = QPushButton("📂 打开")
        open_btn.setToolTip("打开PDF文件 (Ctrl+O)")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(self._get_toolbutton_style())
        open_btn.clicked.connect(self.parent.open_file)
        self.toolbar.addWidget(open_btn)
    
    def _add_navigation_section(self):
        """添加导航区域"""
        self.page_navigator = PageNavigator()
        self.page_navigator.pageChanged.connect(
            lambda page: self.parent.navigation_controller.go_to_page_number(page)
        )
        self.toolbar.addWidget(self.page_navigator)
        
        # 兼容旧代码
        self.page_input = self.page_navigator.page_spin
    
    def _add_view_mode_section(self):
        """添加视图模式区域 - 分段按钮组"""
        self.view_mode_group = SegmentedButtonGroup()
        
        # 添加视图模式按钮
        self.single_page_btn = self.view_mode_group.addButton(
            "单页", "▣", "单页浏览模式"
        )
        self.single_page_continuous_btn = self.view_mode_group.addButton(
            "连续", "☰", "单页连续浏览模式"
        )
        self.two_page_spread_btn = self.view_mode_group.addButton(
            "双页", "▣▣", "双页浏览模式"
        )
        self.two_page_spread_continuous_btn = self.view_mode_group.addButton(
            "双连", "☰☰", "双页连续浏览模式"
        )
        
        # 默认选中单页
        self.single_page_btn.setChecked(True)
        
        # 连接信号
        self.view_mode_group.buttonClicked.connect(self._on_view_mode_changed)
        
        self.toolbar.addWidget(self.view_mode_group)
    
    def _add_zoom_section(self):
        """添加缩放控制区域"""
        self.zoom_control = ZoomControlWidget()
        self.zoom_control.zoomChanged.connect(
            lambda zoom: self.parent.zoom_controller.set_zoom_percentage(zoom)
        )
        self.zoom_control.fitPageRequested.connect(
            self.parent.zoom_controller.zoom_fit_page
        )
        self.zoom_control.fitWidthRequested.connect(
            self.parent.zoom_controller.zoom_fit_width
        )
        
        self.toolbar.addWidget(self.zoom_control)
        
        # 兼容旧代码
        self.zoom_percentage_label = self.zoom_control.zoom_label
    
    def _add_reading_mode_button(self):
        """添加阅读模式切换按钮"""
        colors = get_colors()
        
        reading_btn = QPushButton("📖 阅读")
        reading_btn.setCheckable(True)
        reading_btn.setToolTip("切换阅读模式")
        reading_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reading_btn.setStyleSheet(self._get_toolbutton_style())
        reading_btn.clicked.connect(self.parent.toggle_reading_mode)
        
        self.toolbar.addWidget(reading_btn)
        self.reading_mode_action = reading_btn
    
    def _get_toolbutton_style(self) -> str:
        """获取工具按钮样式"""
        colors = get_colors()
        return f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px 12px;
                color: {colors.text_primary};
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {colors.bg_hover};
                border-color: {colors.border};
            }}
            QPushButton:pressed {{
                background-color: {colors.bg_selected};
                border-color: {colors.primary};
            }}
            QPushButton:checked {{
                background-color: {colors.primary_light};
                border-color: {colors.primary};
                color: {colors.primary};
            }}
        """
    
    def _on_view_mode_changed(self, index: int):
        """视图模式改变"""
        modes = [
            self.parent.navigation_controller.switch_to_single_page,
            self.parent.navigation_controller.switch_to_single_page_continuous,
            self.parent.navigation_controller.switch_to_two_page_spread,
            self.parent.navigation_controller.switch_to_two_page_spread_continuous,
        ]
        if 0 <= index < len(modes):
            modes[index]()
    
    def add_browsing_viewtype_buttons(self):
        """添加浏览模式切换按钮 - 已集成到工具栏，此方法保持兼容"""
        pass  # 视图模式按钮现在已经在工具栏中
    
    def update_browsing_viewtype_checks(self):
        """更新浏览视图类型按钮的选中状态"""
        if not self.view_mode_group:
            return
            
        current_mode = self.parent.viewtype_manager.get_current_viewtype_name()
        
        mode_map = {
            "single_page": 0,
            "single_page_continuous": 1,
            "two_page_spread": 2,
            "two_page_spread_continuous": 3,
        }
        
        index = mode_map.get(current_mode, 0)
        self.view_mode_group.setChecked(index)
    
    def update_page_display(self, current_page: int, total_pages: int):
        """更新页码显示"""
        if self.page_navigator:
            self.page_navigator.setTotalPages(total_pages)
            self.page_navigator.setPage(current_page)
    
    def update_zoom_display(self, zoom_percentage: float):
        """更新缩放显示"""
        if self.zoom_control:
            self.zoom_control.setZoom(zoom_percentage)
    
    # 兼容旧代码的方法
    def get_zoom_slider(self):
        """获取缩放滑块 - 兼容旧代码"""
        return self.zoom_slider
    
    def get_zoom_percentage_label(self):
        """获取缩放百分比标签 - 兼容旧代码"""
        return self.zoom_percentage_label
    
    def get_graphic_detection_action(self):
        """获取图形检测按钮 - 兼容旧代码"""
        return self.graphic_detection_action

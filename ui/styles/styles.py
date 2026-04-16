"""
样式表系统 - 生成Qt样式表
支持Windows风格 + 现代化设计
"""

from PyQt6.QtWidgets import QWidget
from .colors import get_colors, ColorScheme


class StyleSheet:
    """样式表生成器"""
    
    def __init__(self, colors: ColorScheme = None):
        self.colors = colors or get_colors()
    
    def get_global_style(self) -> str:
        """获取全局样式"""
        c = self.colors
        return f"""
        /* 全局字体 */
        QWidget {{
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            font-size: 13px;
        }}
        
        /* 主窗口 */
        QMainWindow {{
            background-color: {c.bg_window};
        }}
        
        /* 滚动条样式 */
        QScrollBar:vertical {{
            background-color: {c.bg_content};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {c.border};
            border-radius: 6px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {c.text_secondary};
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background-color: {c.bg_content};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {c.border};
            border-radius: 6px;
            min-width: 30px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {c.text_secondary};
        }}
        
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        /* 工具提示 */
        QToolTip {{
            background-color: {c.bg_card};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 12px;
        }}
        """
    
    def get_toolbar_style(self) -> str:
        """工具栏样式 - Windows风格"""
        c = self.colors
        return f"""
        QToolBar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c.toolbar_bg},
                stop:1 #E8E8E8);
            border-bottom: 1px solid {c.toolbar_border};
            padding: 4px 8px;
            spacing: 4px;
        }}
        
        QToolBar::separator {{
            background-color: {c.border};
            width: 1px;
            height: 24px;
            margin: 4px 8px;
        }}
        """
    
    def get_toolbutton_style(self) -> str:
        """工具栏按钮样式 - 图标+文字"""
        c = self.colors
        return f"""
        QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 4px 8px;
            color: {c.text_primary};
            font-size: 12px;
        }}
        
        QToolButton:hover {{
            background-color: {c.bg_hover};
            border-color: {c.border};
        }}
        
        QToolButton:pressed {{
            background-color: {c.bg_selected};
            border-color: {c.primary};
        }}
        
        QToolButton:checked {{
            background-color: {c.primary_light};
            border-color: {c.primary};
            color: {c.primary};
        }}
        
        QToolButton:disabled {{
            color: {c.text_disabled};
        }}
        
        QToolButton::icon {{
            padding: 2px;
        }}
        """
    
    def get_segmented_button_style(self) -> str:
        """分段按钮组样式（视图模式切换）"""
        c = self.colors
        return f"""
        /* 分段按钮容器 */
        QWidget#segmented_container {{
            background-color: {c.bg_content};
            border: 1px solid {c.border};
            border-radius: 6px;
            padding: 2px;
        }}
        
        /* 分段按钮 */
        QPushButton#segmented_button {{
            background-color: transparent;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            color: {c.text_secondary};
            font-size: 12px;
            font-weight: 500;
        }}
        
        QPushButton#segmented_button:hover {{
            background-color: {c.bg_hover};
            color: {c.text_primary};
        }}
        
        QPushButton#segmented_button:checked {{
            background-color: {c.bg_card};
            color: {c.primary};
            border: 1px solid {c.border};
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }}
        """
    
    def get_input_style(self) -> str:
        """输入框样式"""
        c = self.colors
        return f"""
        QLineEdit {{
            background-color: {c.bg_card};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 6px 10px;
            color: {c.text_primary};
            font-size: 13px;
            selection-background-color: {c.primary};
            selection-color: {c.text_inverse};
        }}
        
        QLineEdit:focus {{
            border-color: {c.border_focus};
        }}
        
        QLineEdit:hover {{
            border-color: {c.text_secondary};
        }}
        
        QLineEdit:disabled {{
            background-color: {c.bg_hover};
            color: {c.text_disabled};
        }}
        """
    
    def get_spinbox_style(self) -> str:
        """数字输入框样式（页码、缩放）"""
        c = self.colors
        return f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {c.bg_card};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 6px 10px;
            color: {c.text_primary};
            font-size: 13px;
        }}
        
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {c.border_focus};
        }}
        
        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: transparent;
            border: none;
            width: 20px;
        }}
        
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {c.bg_hover};
        }}
        """
    
    def get_thumbnail_style(self) -> str:
        """缩略图面板样式"""
        c = self.colors
        return f"""
        /* 缩略图列表 */
        QListWidget {{
            background-color: {c.bg_content};
            border: none;
            outline: none;
            padding: 8px;
        }}
        
        QListWidget::item {{
            background-color: {c.bg_card};
            border: 2px solid transparent;
            border-radius: 6px;
            margin: 4px 0px;
            padding: 8px;
        }}
        
        QListWidget::item:hover {{
            background-color: {c.bg_hover};
            border-color: {c.border};
        }}
        
        QListWidget::item:selected {{
            background-color: {c.bg_selected};
            border-color: {c.primary};
        }}
        
        QListWidget::item:selected:hover {{
            background-color: {c.bg_selected};
            border-color: {c.primary_hover};
        }}
        """
    
    def get_statusbar_style(self) -> str:
        """状态栏样式 - Windows风格"""
        c = self.colors
        return f"""
        QStatusBar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c.statusbar_bg},
                stop:1 #E8E8E8);
            border-top: 1px solid {c.toolbar_border};
            padding: 2px 8px;
            font-size: 12px;
            color: {c.text_secondary};
        }}
        
        QStatusBar::item {{
            border: none;
        }}
        """
    
    def get_menubar_style(self) -> str:
        """菜单栏样式 - Windows风格"""
        c = self.colors
        return f"""
        QMenuBar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {c.menubar_bg},
                stop:1 #E8E8E8);
            border-bottom: 1px solid {c.toolbar_border};
            padding: 2px 4px;
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 12px;
            border-radius: 4px;
            color: {c.text_primary};
        }}
        
        QMenuBar::item:selected {{
            background-color: {c.bg_hover};
            border: 1px solid {c.border};
        }}
        
        QMenuBar::item:pressed {{
            background-color: {c.bg_selected};
            border: 1px solid {c.primary};
        }}
        
        QMenu {{
            background-color: {c.bg_card};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 6px 24px;
            border-radius: 4px;
            color: {c.text_primary};
        }}
        
        QMenu::item:selected {{
            background-color: {c.bg_selected};
            color: {c.primary};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {c.border_light};
            margin: 4px 8px;
        }}
        """
    
    def get_splitter_style(self) -> str:
        """分割器样式"""
        c = self.colors
        return f"""
        QSplitter::handle {{
            background-color: {c.border};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        QSplitter::handle:hover {{
            background-color: {c.primary};
        }}
        """
    
    def get_combobox_style(self) -> str:
        """下拉框样式"""
        c = self.colors
        return f"""
        QComboBox {{
            background-color: {c.bg_card};
            border: 1px solid {c.border};
            border-radius: 4px;
            padding: 6px 10px;
            color: {c.text_primary};
            font-size: 13px;
            min-width: 80px;
        }}
        
        QComboBox:hover {{
            border-color: {c.text_secondary};
        }}
        
        QComboBox:focus {{
            border-color: {c.border_focus};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {c.text_secondary};
            width: 0;
            height: 0;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {c.bg_card};
            border: 1px solid {c.border};
            border-radius: 4px;
            selection-background-color: {c.bg_selected};
            selection-color: {c.primary};
        }}
        """
    
    def get_all_styles(self) -> str:
        """获取所有样式"""
        return (
            self.get_global_style() +
            self.get_toolbar_style() +
            self.get_toolbutton_style() +
            self.get_segmented_button_style() +
            self.get_input_style() +
            self.get_spinbox_style() +
            self.get_thumbnail_style() +
            self.get_statusbar_style() +
            self.get_menubar_style() +
            self.get_splitter_style() +
            self.get_combobox_style()
        )


# 便捷函数
def get_stylesheet() -> StyleSheet:
    """获取样式表生成器"""
    return StyleSheet()


def get_button_style(colors: ColorScheme = None) -> str:
    """获取按钮样式"""
    return StyleSheet(colors).get_toolbutton_style()


def get_input_style(colors: ColorScheme = None) -> str:
    """获取输入框样式"""
    return StyleSheet(colors).get_input_style()


def get_toolbar_style(colors: ColorScheme = None) -> str:
    """获取工具栏样式"""
    return StyleSheet(colors).get_toolbar_style()


def get_thumbnail_style(colors: ColorScheme = None) -> str:
    """获取缩略图样式"""
    return StyleSheet(colors).get_thumbnail_style()


def get_statusbar_style(colors: ColorScheme = None) -> str:
    """获取状态栏样式"""
    return StyleSheet(colors).get_statusbar_style()


def apply_stylesheet(widget: QWidget, colors: ColorScheme = None) -> None:
    """应用全局样式表到窗口"""
    stylesheet = StyleSheet(colors)
    widget.setStyleSheet(stylesheet.get_all_styles())

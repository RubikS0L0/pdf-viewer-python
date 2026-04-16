"""
颜色系统 - 定义PDF查看器的配色方案
支持浅色/深色主题切换
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ColorScheme:
    """颜色方案数据类"""
    # 主色调
    primary: str
    primary_hover: str
    primary_active: str
    primary_light: str
    
    # 背景色
    bg_window: str
    bg_content: str
    bg_card: str
    bg_hover: str
    bg_selected: str
    
    # 文字色
    text_primary: str
    text_secondary: str
    text_disabled: str
    text_inverse: str
    
    # 边框色
    border: str
    border_light: str
    border_focus: str
    
    # 状态色
    success: str
    warning: str
    error: str
    info: str
    
    # 工具栏/菜单栏（Windows风格）
    toolbar_bg: str
    toolbar_border: str
    menubar_bg: str
    statusbar_bg: str


# 浅色主题 - Windows风格
LIGHT_THEME = ColorScheme(
    # 主色调 - 蓝色系
    primary="#2563EB",
    primary_hover="#1D4ED8",
    primary_active="#1E40AF",
    primary_light="#DBEAFE",
    
    # 背景色
    bg_window="#F1F5F9",  # Windows经典浅灰
    bg_content="#F8FAFC",
    bg_card="#FFFFFF",
    bg_hover="#F1F5F9",
    bg_selected="#DBEAFE",
    
    # 文字色
    text_primary="#0F172A",
    text_secondary="#475569",
    text_disabled="#94A3B8",
    text_inverse="#FFFFFF",
    
    # 边框色
    border="#CBD5E1",
    border_light="#E2E8F0",
    border_focus="#2563EB",
    
    # 状态色
    success="#10B981",
    warning="#F59E0B",
    error="#EF4444",
    info="#3B82F6",
    
    # Windows风格工具栏
    toolbar_bg="#F0F0F0",
    toolbar_border="#D1D5DB",
    menubar_bg="#F0F0F0",
    statusbar_bg="#F0F0F0",
)

# 深色主题
DARK_THEME = ColorScheme(
    # 主色调
    primary="#3B82F6",
    primary_hover="#60A5FA",
    primary_active="#2563EB",
    primary_light="#1E3A8A",
    
    # 背景色
    bg_window="#1E293B",
    bg_content="#0F172A",
    bg_card="#1E293B",
    bg_hover="#334155",
    bg_selected="#1E3A8A",
    
    # 文字色
    text_primary="#F8FAFC",
    text_secondary="#94A3B8",
    text_disabled="#64748B",
    text_inverse="#0F172A",
    
    # 边框色
    border="#334155",
    border_light="#475569",
    border_focus="#3B82F6",
    
    # 状态色
    success="#34D399",
    warning="#FBBF24",
    error="#F87171",
    info="#60A5FA",
    
    # Windows风格工具栏（深色）
    toolbar_bg="#2D3748",
    toolbar_border="#4A5568",
    menubar_bg="#2D3748",
    statusbar_bg="#2D3748",
)


class ThemeManager:
    """主题管理器"""
    
    _instance: Optional['ThemeManager'] = None
    _current_theme: ColorScheme = LIGHT_THEME
    
    def __new__(cls) -> 'ThemeManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def current(self) -> ColorScheme:
        """获取当前主题"""
        return self._current_theme
    
    def set_theme(self, theme_name: str) -> None:
        """设置主题
        
        Args:
            theme_name: 'light' 或 'dark'
        """
        if theme_name.lower() == 'dark':
            self._current_theme = DARK_THEME
        else:
            self._current_theme = LIGHT_THEME
    
    def toggle_theme(self) -> None:
        """切换主题"""
        if self._current_theme == LIGHT_THEME:
            self._current_theme = DARK_THEME
        else:
            self._current_theme = LIGHT_THEME


# 便捷访问函数
def get_colors() -> ColorScheme:
    """获取当前颜色方案"""
    return ThemeManager().current


def get_theme_manager() -> ThemeManager:
    """获取主题管理器实例"""
    return ThemeManager()

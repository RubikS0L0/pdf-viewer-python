"""
浏览视图类型管理模块

功能：
- 负责浏览视图类型的注册、实例化、切换和生命周期管理
- 管理单页浏览、单页连续浏览、双页浏览、双页连续浏览等视图类型
- 处理视图类型激活和停用逻辑
- 协调不同视图类型之间的状态同步

开发环境：
- Python 3.14
- Windows系统

核心依赖：
- PyQt5：GUI界面组件

创建时间：2026-01-16
更新时间：2026-01-23
"""

from PyQt6.QtWidgets import QApplication

class ViewtypeManager:
    """浏览视图类型管理器"""
    
    def __init__(self, pdf_viewer, viewtype_service):
        """初始化视图类型管理器"""
        self.pdf_viewer = pdf_viewer
        self.viewtype_service = viewtype_service
        self.viewtypes = {}
        self.current_viewtype = None
        self._register_viewtypes()
        
    def _register_viewtypes(self):
        """注册所有浏览视图类型"""
        from .single_page_viewtype import SinglePageViewtype
        from .single_page_continuous_viewtype import SinglePageContinuousViewtype
        from .two_page_viewtype import TwoPageViewtype
        from .two_page_continuous_viewtype import TwoPageContinuousViewtype
        
        self.viewtypes = {
            "single_page": SinglePageViewtype(self.viewtype_service, self.pdf_viewer),
            "single_page_continuous": SinglePageContinuousViewtype(self.viewtype_service, self.pdf_viewer),
            "two_page_spread": TwoPageViewtype(self.viewtype_service, self.pdf_viewer),
            "two_page_spread_continuous": TwoPageContinuousViewtype(self.viewtype_service, self.pdf_viewer)
        }
        # 设置默认视图类型，但暂不激活
        self.current_viewtype = self.viewtypes["single_page"]
        # 注册默认视图类型为状态观察者
        if hasattr(self.pdf_viewer, 'state_notifier'):
            self.pdf_viewer.state_notifier.add_observer(self.current_viewtype)
        
    def _clear_center_layout(self):
        """清理中心布局的所有内容，确保不会残留上一视图类型的显示元素"""
        # 增强空值检查，确保所有依赖属性存在
        if not hasattr(self.pdf_viewer, 'scroll_area') or not self.pdf_viewer.scroll_area:
            return
        
        scroll_area = self.pdf_viewer.scroll_area
        center_container = scroll_area.widget()
        if not center_container or not hasattr(center_container, 'layout'):
            return
        
        center_layout = center_container.layout()
        if not center_layout:
            return
            
        # 移除所有子部件
        while center_layout.count() > 0:
            item = center_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 递归清理子布局
                sub_layout = item.layout()
                if sub_layout:
                    # 定义递归清理函数
                    def cleanup_layout(layout):
                        while layout.count() > 0:
                            sub_item = layout.takeAt(0)
                            if sub_item.widget():
                                sub_item.widget().deleteLater()
                            elif sub_item.layout() and sub_item.layout() != layout:  # 防止递归自身
                                cleanup_layout(sub_item.layout())
                    # 调用递归清理函数
                    cleanup_layout(sub_layout)
                    del sub_layout
        
        # 强制更新布局
        center_layout.invalidate()
        center_layout.activate()
    
    def _deactivate_current_viewtype(self):
        """停用当前视图类型"""
        if self.current_viewtype:
            # 保存当前视图类型的滚动位置
            self.current_viewtype.save_scroll_position()
            
            self.current_viewtype.deactivate()
            # 移除当前视图类型的观察者注册
            if hasattr(self.pdf_viewer, 'state_notifier'):
                self.pdf_viewer.state_notifier.remove_observer(self.current_viewtype)
    
    def _activate_viewtype(self, viewtype_name):
        """激活指定视图类型"""
        self.current_viewtype = self.viewtypes[viewtype_name]
        self.current_viewtype.activate()
        
        # 恢复当前视图类型的滚动位置
        self.current_viewtype.restore_scroll_position()
        
        # 注册新视图类型为状态观察者
        if hasattr(self.pdf_viewer, 'state_notifier'):
            self.pdf_viewer.state_notifier.add_observer(self.current_viewtype)
        
        # 更新PDF查看器的视图类型标识
        if hasattr(self.pdf_viewer, 'browsing_viewtype'):
            self.pdf_viewer.browsing_viewtype = viewtype_name
        
        # 更新当前视图类型名称缓存
        self._current_viewtype_name = viewtype_name
    
    def set_viewtype(self, viewtype_name):
        """切换到指定视图类型"""
        if viewtype_name not in self.viewtypes:
            raise ValueError(f"未知的浏览视图类型: {viewtype_name}")
            
        # 检查是否为当前已激活的视图类型，如果是则不执行切换
        if self.current_viewtype == self.viewtypes[viewtype_name]:
            return
            
        # 停用当前视图类型
        self._deactivate_current_viewtype()
        
        # 清理中心布局
        self._clear_center_layout()
        
        # 激活新视图类型
        self._activate_viewtype(viewtype_name)
        
        # 更新当前视图类型名称缓存
        self._current_viewtype_name = viewtype_name
        
    def get_current_viewtype(self):
        """获取当前视图类型"""
        return self.current_viewtype
        
    def get_current_viewtype_name(self):
        """获取当前视图类型名称"""
        # 更高效的实现，避免遍历
        current_name = getattr(self, '_current_viewtype_name', None)
        if current_name:
            return current_name
        # 回退到遍历方式
        for viewtype_name, viewtype in self.viewtypes.items():
            if viewtype == self.current_viewtype:
                self._current_viewtype_name = viewtype_name
                return viewtype_name
        return "single_page"  # 默认返回单页视图类型
        
    def get_viewtype(self, viewtype_name):
        """获取指定视图类型"""
        if viewtype_name not in self.viewtypes:
            raise ValueError(f"未知的浏览视图类型: {viewtype_name}")
        return self.viewtypes[viewtype_name]
        
    def reactivate_current_viewtype(self):
        """重新激活当前视图类型
        
        当打开新文件或需要强制刷新视图类型时使用，确保视图类型被正确重新激活
        即使当前视图类型已经是激活状态，也会重新执行激活流程
        """
        if not self.current_viewtype:
            return
            
        # 获取当前视图类型名称
        current_viewtype_name = None
        for name, viewtype in self.viewtypes.items():
            if viewtype == self.current_viewtype:
                current_viewtype_name = name
                break
                
        if not current_viewtype_name:
            return
            
        # 停用当前视图类型
        self._deactivate_current_viewtype()
        
        # 清理中心布局
        self._clear_center_layout()
        
        # 激活当前视图类型
        self._activate_viewtype(current_viewtype_name)
        
    def update_config_for_all_viewtypes(self):
        """更新所有视图类型的配置，只更新激活状态的视图类型"""
        for viewtype in self.viewtypes.values():
            if viewtype.is_active:
                viewtype.update_config()
        
    def reset_all_viewtypes(self):
        """重置所有视图类型"""
        for viewtype in self.viewtypes.values():
            viewtype.reset_display()
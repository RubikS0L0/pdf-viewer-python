#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
导航控制器类

功能：
- 处理页面导航逻辑
- 管理页码输入和显示
- 处理浏览模式切换
"""

class NavigationController:
    """
    导航控制器
    
    负责处理页面导航、页码输入和浏览模式切换
    """
    
    def __init__(self, parent):
        self.parent = parent
    
    def disable_navigation(self):
        """禁用导航按钮"""
        # 获取工具栏管理器的控件引用
        toolbar_manager = self.parent.toolbar_manager
        
        # 禁用页面导航
        if toolbar_manager.page_navigator:
            toolbar_manager.page_navigator.prev_btn.setEnabled(False)
            toolbar_manager.page_navigator.next_btn.setEnabled(False)
            toolbar_manager.page_navigator.page_spin.setEnabled(False)
        
        # 禁用缩放控制
        if toolbar_manager.zoom_control:
            toolbar_manager.zoom_control.zoom_in_btn.setEnabled(False)
            toolbar_manager.zoom_control.zoom_out_btn.setEnabled(False)
            toolbar_manager.zoom_control.fit_btn.setEnabled(False)
            toolbar_manager.zoom_control.fit_width_btn.setEnabled(False)
        
        # 禁用浏览模式切换按钮
        if toolbar_manager.view_mode_group:
            for btn in toolbar_manager.view_mode_group.buttons:
                btn.setEnabled(False)
    
    def enable_navigation(self):
        """启用导航按钮"""
        # 获取工具栏管理器的控件引用
        toolbar_manager = self.parent.toolbar_manager
        
        current_page = self.parent.current_page
        total_pages = self.parent.total_pages
        
        # 启用页面导航
        if toolbar_manager.page_navigator:
            toolbar_manager.page_navigator.prev_btn.setEnabled(current_page > 0)
            toolbar_manager.page_navigator.next_btn.setEnabled(current_page < total_pages - 1)
            toolbar_manager.page_navigator.page_spin.setEnabled(True)
            toolbar_manager.page_navigator.setTotalPages(total_pages)
            # PageNavigator 使用从1开始的页码，需要转换
            toolbar_manager.page_navigator.setPage(current_page + 1)
        
        # 启用缩放控制
        if toolbar_manager.zoom_control:
            toolbar_manager.zoom_control.zoom_in_btn.setEnabled(True)
            toolbar_manager.zoom_control.zoom_out_btn.setEnabled(True)
            toolbar_manager.zoom_control.fit_btn.setEnabled(True)
            toolbar_manager.zoom_control.fit_width_btn.setEnabled(True)
        
        # 启用浏览模式切换按钮
        if toolbar_manager.view_mode_group:
            for btn in toolbar_manager.view_mode_group.buttons:
                btn.setEnabled(True)
    
    def update_page_input(self):
        """更新页码输入框"""
        current_page = self.parent.current_page
        if self.parent.toolbar_manager.page_navigator:
            # PageNavigator 使用从1开始的页码，需要转换
            self.parent.toolbar_manager.page_navigator.setPage(current_page + 1)
    
    def go_to_page_number(self, page_num: int):
        """跳转到指定页码（新版接口）
        
        Args:
            page_num: 页码（从1开始）
        """
        if 0 <= page_num - 1 < self.parent.total_pages:
            self.parent.show_page(page_num - 1)
        else:
            # 页码无效，恢复当前页码
            self.update_page_input()
    
    def prev_page(self):
        """上一页"""
        if self.parent.toolbar_manager.page_navigator:
            self.parent.toolbar_manager.page_navigator._go_prev()
        else:
            # 兼容旧代码
            current_page = self.parent.current_page
            if current_page > 0:
                # 根据浏览模式确定翻页数量
                if self._is_two_page_viewtype():
                    # 双页浏览模式下，上一页应该后退两页
                    new_page = max(0, current_page - 2)
                else:
                    # 单页浏览模式下，上一页后退一页
                    new_page = current_page - 1
                
                self.parent.show_page(new_page)
    
    def next_page(self):
        """下一页"""
        if self.parent.toolbar_manager.page_navigator:
            self.parent.toolbar_manager.page_navigator._go_next()
        else:
            # 兼容旧代码
            current_page = self.parent.current_page
            total_pages = self.parent.total_pages
            
            if current_page < total_pages - 1:
                # 根据浏览模式确定翻页数量
                if self._is_two_page_viewtype():
                    # 双页浏览模式下，下一页应该前进两页
                    new_page = min(total_pages - 1, current_page + 2)
                else:
                    # 单页浏览模式下，下一页前进一页
                    new_page = current_page + 1
                
                self.parent.show_page(new_page)
    
    def go_to_page(self):
        """跳转到指定页码（旧版兼容接口）"""
        try:
            if self.parent.toolbar_manager.page_navigator:
                page_num = self.parent.toolbar_manager.page_navigator.page_spin.value() - 1
            else:
                # 兼容旧代码
                page_num = int(self.parent.toolbar_manager.page_input.text()) - 1
            
            if 0 <= page_num < self.parent.total_pages:
                self.parent.show_page(page_num)
            else:
                # 页码无效，恢复当前页码
                self.update_page_input()
        except ValueError:
            # 输入不是数字，恢复当前页码
            self.update_page_input()
    
    def switch_to_single_page(self):
        """切换到单页浏览模式"""
        self.parent.viewtype_manager.set_viewtype("single_page")
        self.parent.toolbar_manager.update_browsing_viewtype_checks()
        self.parent.status_bar.showMessage("浏览模式: 单页浏览")
        # 更新页面显示
        if self.parent.pdf_manager.is_open:
            self.parent.show_page(self.parent.current_page)
    
    def switch_to_single_page_continuous(self):
        """切换到单页连续浏览模式"""
        self.parent.viewtype_manager.set_viewtype("single_page_continuous")
        self.parent.toolbar_manager.update_browsing_viewtype_checks()
        self.parent.status_bar.showMessage("浏览模式: 单页连续浏览")
        # 更新页面显示
        if self.parent.pdf_manager.is_open:
            self.parent.show_page(self.parent.current_page)
    
    def switch_to_two_page_spread(self):
        """切换到双页浏览模式"""
        # 如果当前是奇数页，可能需要调整到前一页以确保双页显示正确
        current_page = self.parent.current_page
        if current_page % 2 == 1 and current_page > 0:
            current_page -= 1
            self.parent.current_page = current_page
        
        self.parent.viewtype_manager.set_viewtype("two_page_spread")
        self.parent.toolbar_manager.update_browsing_viewtype_checks()
        self.parent.status_bar.showMessage("浏览模式: 双页浏览")
        # 更新页面显示
        if self.parent.pdf_manager.is_open:
            self.parent.show_page(current_page)
    
    def switch_to_two_page_spread_continuous(self):
        """切换到双页连续浏览模式"""
        # 如果当前是奇数页，可能需要调整到前一页以确保双页显示正确
        current_page = self.parent.current_page
        if current_page % 2 == 1 and current_page > 0:
            current_page -= 1
            self.parent.current_page = current_page
        
        self.parent.viewtype_manager.set_viewtype("two_page_spread_continuous")
        self.parent.toolbar_manager.update_browsing_viewtype_checks()
        self.parent.status_bar.showMessage("浏览模式: 双页连续")
        # 更新页面显示
        if self.parent.pdf_manager.is_open:
            self.parent.show_page(current_page)
    
    def _is_two_page_viewtype(self):
        """检查当前是否为双页浏览视图类型"""
        return self.parent.viewtype_service.is_two_page_mode()

"""
单页浏览视图类型模块

功能：
- 实现PDF单页浏览视图类型
- 只显示当前页码的内容，页面居中显示
- 支持页面缩放和导航
- 处理单页视图类型下的用户交互

开发环境：
- Python 3.14
- Windows系统

核心依赖：
- PyQt5：GUI界面组件
- BrowsingViewtype：浏览视图类型抽象基类

创建时间：2026-01-16
更新时间：2026-01-23
"""

from .base import BrowsingViewtype
from services.event_bus import event_bus

class SinglePageViewtype(BrowsingViewtype):
    """单页浏览视图类型"""
    
    def __init__(self, viewtype_service, pdf_viewer):
        super().__init__(viewtype_service, pdf_viewer)
        # 订阅渲染完成事件
        event_bus.render_completed.connect(self._on_render_completed)
    
    def show_page(self, page_num):
        """显示指定页码的页面"""
        if not self.is_active:
            return
            
        # 确保PDF文档已打开
        if not hasattr(self.pdf_viewer, 'pdf_manager') or not self.pdf_viewer.pdf_manager.is_open:
            return
            
        # 确保页码有效
        if page_num < 0 or page_num >= self.viewtype_service.get_total_pages():
            return
            
        # 更新当前页码
        self.current_page = page_num
            
        # 确保页面标签已初始化
        if self.page_label is None:
            self._initialize_page_label()
            
        # 发布页面更新事件
        self._on_page_changed(page_num)
            
        # 使用异步方法获取页面pixmap，不传递回调函数，通过事件总线处理渲染完成
        self.viewtype_service.get_page_pixmap_async(page_num)
    
    def update_config(self):
        """更新配置"""
        # 调用基类的update_config方法
        super().update_config()
        
        # 移除无效的空延迟
        # 布局更新会在事件循环的下一个周期自动完成，不需要额外延迟
    
    def _initialize_page_label(self):
        """初始化页面标签"""
        # 确保center_layout有效
        if self.center_layout is None:
            if not self._ensure_center_layout():
                return
        
        # 创建ViewtypePageLabel实例
        from .base import ViewtypePageLabel
        self.page_label = ViewtypePageLabel(self)
        # 连接信号，在页面显示后更新布局
        self.page_label.pixmapChanged.connect(self.viewtype_service.update_content_layout)
        self.center_layout.addWidget(self.page_label)
        
    def _ensure_center_layout(self):
        """确保center_layout有效"""
        if self.center_layout is None:
            # 直接从ContentArea获取，不依赖scroll_area和center_container
            if hasattr(self.pdf_viewer, 'content_area') and self.pdf_viewer.content_area is not None:
                self.center_layout = self.pdf_viewer.content_area.get_center_layout()
                self.center_container = self.pdf_viewer.content_area.get_center_container()
            else:
                import logging
                logging.warning(f"{self.__class__.__name__}激活失败：center_layout为None")
                return False
        return True
    
    def _on_render_completed(self, page_num, zoom_level, result, is_final):
        """处理渲染完成事件"""
        # 检查必要的状态
        if result is None or not self.is_active:
            return
        # 缩放校验：只处理对应当前缩放级别的渲染结果，防止旧缩放结果覆盖显示
        if not self._is_current_zoom(zoom_level):
            return
            
        # 确保页面标签已初始化
        if self.page_label is None:
            self._initialize_page_label()
            
        # 直接操作page_label，确保页面图像正确设置
        try:
            # 只处理当前页面的渲染结果
            if self.current_page == page_num:
                self.page_label.setPixmap(result)
                self.page_label.show()
                
                # 优化布局更新，避免重复计算
                if self.center_layout is not None:
                    # 先更新page_label的几何信息
                    self.page_label.updateGeometry()
                    # 然后一次性更新布局（activate()会自动调用invalidate()）
                    self.center_layout.activate()
                
                # 使用pixmap大小而不是page_label大小来计算滚动位置
                pixmap_size = result.size()
                page_width = pixmap_size.width()
                page_height = pixmap_size.height()
                
                # 更新配置
                self.update_config()
                
                # 确保页面在viewport中居中显示
                scroll_area = self.scroll_area
                
                if scroll_area is not None:
                    # 从ViewportManager获取视口尺寸
                    from ui.viewport_manager import viewport_manager
                    viewport_width = viewport_manager.get_viewport_width()
                    viewport_height = viewport_manager.get_viewport_height()
                    
                    # 如果页面小于视口，QLabel默认居中，不需要滚动
                    if page_width <= viewport_width and page_height <= viewport_height:
                        return
                    
                    # 计算居中位置（仅当页面大于视口时）
                    h_pos = max(0, (page_width - viewport_width) // 2)
                    v_pos = max(0, (page_height - viewport_height) // 2)
                    
                    # 直接设置滚动条位置，不使用ensureWidgetVisible（避免冲突）
                    v_scroll = scroll_area.verticalScrollBar()
                    h_scroll = scroll_area.horizontalScrollBar()
                    
                    if v_scroll is not None:
                        v_scroll.setValue(v_pos)
                    if h_scroll is not None:
                        h_scroll.setValue(h_pos)
        except Exception as e:
            import logging
            logging.error(f"单页视图类型: 处理渲染完成事件失败，页码：{page_num}，错误：{str(e)}")


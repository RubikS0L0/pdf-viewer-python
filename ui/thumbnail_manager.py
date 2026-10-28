#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缩略图管理类

功能：
- 生成和管理PDF文档的缩略图
- 处理缩略图与浏览区的随动
- 管理缩略图的显示和交互
"""

import logging
from PyQt6.QtWidgets import QScrollArea, QWidget, QGridLayout, QLabel
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QLinearGradient
from PyQt6.QtCore import Qt, pyqtSignal, QMutex, QThread

from utils.constants import Constants

# Import event bus
from services.event_bus import event_bus

class ThumbnailCache:
    """
    缩略图缓存类
    
    功能：
    - 缓存生成的缩略图，避免重复生成
    - 使用文件路径和修改时间作为缓存键的一部分
    - 实现LRU缓存机制，限制缓存大小
    """
    def __init__(self, max_size=500):
        self.max_size = max_size
        self.cache = {}
        self.lru = []
    
    def get(self, key):
        """获取缓存的缩略图"""
        if key in self.cache:
            # 更新LRU
            if key in self.lru:
                self.lru.remove(key)
            self.lru.append(key)
            return self.cache[key]
        return None
    
    def set(self, key, value):
        """设置缓存的缩略图"""
        if key in self.cache:
            # 更新LRU
            if key in self.lru:
                self.lru.remove(key)
        elif len(self.cache) >= self.max_size:
            # 移除最旧的项
            oldest_key = self.lru.pop(0)
            if oldest_key in self.cache:
                del self.cache[oldest_key]
        
        self.cache[key] = value
        self.lru.append(key)
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.lru.clear()

class ThumbnailGenerator(QThread):
    """
    缩略图生成器
    
    功能：
    - 并行生成PDF文档所有页面的缩略图
    - 支持LRU缓存机制，提高缩略图获取效率
    - 线程安全设计，使用互斥锁保护文档访问
    - 使用线程池实现并行处理，提升生成速度
    
    信号：
    - thumbnail_generated(int, QPixmap): 当单个页面缩略图生成完成时发射
      参数1: 页面编号
      参数2: 生成的QPixmap对象
    """
    thumbnail_generated = pyqtSignal(int, QPixmap)
    
    # 类级别的缩略图缓存
    thumbnail_cache = ThumbnailCache()
    
    def __init__(self, doc, doc_mutex, file_path, parent=None, max_workers=2):
        """
        初始化缩略图生成器
        
        参数：
        - doc: fitz.Document, PDF文档对象
        - doc_mutex: QMutex, 文档访问锁
        - file_path: str, 文件路径
        - parent: QObject, 父对象
        - max_workers: int, 最大工作线程数
        """
        super().__init__(parent)
        self.doc = doc
        self.doc_mutex = doc_mutex  # 文档访问锁
        self.file_path = file_path
        self.parent = parent
        self.running = True
        self.paused = False  # 暂停标志
        
        # 使用全局线程池管理器
        from services.thread_pool_manager import thread_pool_manager
        self._executor = thread_pool_manager.get_thumbnail_executor()
        
        self._futures = []
        self.current_page = 0  # 当前页面编号
        self.user_operation_in_progress = False  # 用户操作标志

    def _generate_thumbnail(self, page_num, quality_level=0):
        """生成单页缩略图
        
        参数：
        - page_num: int, 页面编号
        - quality_level: int, 质量级别，0-低质量，1-中质量，2-高质量
        
        返回：
        - tuple: (page_num, QPixmap) 页面编号和生成的缩略图
        """
        try:
            import os
            import fitz  # PyMuPDF
            from PyQt6.QtGui import QPixmap, QImage, QPainter
            from PyQt6.QtCore import Qt
            
            # 检查是否需要暂停
            while self.paused and self.running:
                import time
                time.sleep(0.1)
            
            if not self.running:
                return page_num, None
            
            # 检查用户操作状态
            while self.user_operation_in_progress and self.running:
                import time
                time.sleep(0.05)
            
            if not self.running:
                return page_num, None
            
            # 缩略图固定尺寸
            thumbnail_width = 90
            thumbnail_height = 120
            
            # 生成缓存键，包含文件路径、文件修改时间、页码和质量级别
            file_mtime = os.path.getmtime(self.file_path) if os.path.exists(self.file_path) else 0
            cache_key = f"{self.file_path}_{file_mtime}_{page_num}_{quality_level}"
            
            # 检查缓存中是否已有该缩略图
            cached_thumbnail = self.thumbnail_cache.get(cache_key)
            if cached_thumbnail:
                return page_num, cached_thumbnail
            
            # 缓存中没有，生成新的缩略图
            self.doc_mutex.lock()
            try:
                # 再次检查运行状态
                if not self.running:
                    return page_num, None
                
                page = self.doc.load_page(page_num)
                
                # 先按高质量渲染原始页面
                base_zoom = 1.0
                if quality_level == 0:
                    base_zoom = 0.5
                elif quality_level == 1:
                    base_zoom = 0.75
                else:
                    base_zoom = 1.0
                
                mat = fitz.Matrix(base_zoom, base_zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # 转换为QImage
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                
                # 创建固定尺寸的QPixmap并填充背景
                pixmap = QPixmap(thumbnail_width, thumbnail_height)
                pixmap.fill(Qt.GlobalColor.white)
                
                # 计算缩放后的尺寸，保持宽高比
                painter = QPainter(pixmap)
                
                # 计算保持宽高比的缩放尺寸
                src_ratio = pix.width / pix.height
                dst_ratio = thumbnail_width / thumbnail_height
                
                if src_ratio > dst_ratio:
                    # 原图更宽，按宽度缩放
                    scaled_width = thumbnail_width
                    scaled_height = int(thumbnail_width / src_ratio)
                else:
                    # 原图更高，按高度缩放
                    scaled_height = thumbnail_height
                    scaled_width = int(thumbnail_height * src_ratio)
                
                # 居中绘制缩略图
                x = (thumbnail_width - scaled_width) // 2
                y = (thumbnail_height - scaled_height) // 2
                
                # 缩放并绘制图像
                scaled_img = img.scaled(scaled_width, scaled_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                painter.drawImage(x, y, scaled_img)
                painter.end()
                
            finally:
                self.doc_mutex.unlock()
            
            # 将生成的缩略图存入缓存
            self.thumbnail_cache.set(cache_key, pixmap)
            
            return page_num, pixmap
        except Exception as e:
            import logging
            logging.error(f"生成第{page_num}页缩略图失败: {str(e)}")
            # 返回None作为失败标志
            return page_num, None
    
    def run(self):
        """QThread的运行方法"""
        # 使用实例变量current_page
        self.generate_thumbnails(current_page=self.current_page)
    
    def generate_thumbnails(self, start_page=0, end_page=None, current_page=0, batch_size=10):
        """生成所有页面的缩略图（增量生成）
        
        参数：
        - start_page: int, 起始页面编号
        - end_page: int, 结束页面编号，None表示所有页面
        - current_page: int, 当前页面编号
        - batch_size: int, 每批生成的缩略图数量
        """
        if not self.running:
            return
        
        total_pages = len(self.doc)
        end_page = end_page or total_pages
        
        # 1. 先生成当前页面的最高优先级缩略图
        highest_priority_pages = [current_page]
        self._generate_batch(highest_priority_pages, priority=-1)  # 最高优先级
        
        # 2. 生成当前页面附近的高优先级缩略图
        high_priority_pages = self._get_priority_pages(current_page, total_pages, range_size=2)
        high_priority_pages = [p for p in high_priority_pages if p != current_page]
        self._generate_batch(high_priority_pages, priority=0)  # 高优先级
        
        # 3. 生成当前页面周围的中优先级缩略图
        medium_priority_pages = self._get_priority_pages(current_page, total_pages, range_size=5)
        # 排除已经生成的高优先级页面
        medium_priority_pages = [p for p in medium_priority_pages if p not in highest_priority_pages and p not in high_priority_pages]
        self._generate_batch(medium_priority_pages, priority=1)  # 中优先级
        
        # 4. 生成当前页面周围的低优先级缩略图
        low_priority_pages = self._get_priority_pages(current_page, total_pages, range_size=10)
        # 排除已经生成的页面
        low_priority_pages = [p for p in low_priority_pages if p not in highest_priority_pages and p not in high_priority_pages and p not in medium_priority_pages]
        self._generate_batch(low_priority_pages, priority=2)  # 低优先级
        
        # 5. 后台渐进式生成其他最低优先级缩略图
        all_pages = list(range(start_page, min(end_page, total_pages)))
        lowest_priority_pages = [p for p in all_pages if p not in highest_priority_pages and p not in high_priority_pages and p not in medium_priority_pages and p not in low_priority_pages]
        
        # 分批生成最低优先级缩略图
        self._generate_in_batches(lowest_priority_pages, batch_size, priority=3)  # 最低优先级
    
    def _get_priority_pages(self, current_page, total_pages, range_size=2):
        """获取优先生成的页面范围
        
        参数：
        - current_page: int, 当前页面编号
        - total_pages: int, 总页面数
        - range_size: int, 范围大小
        
        返回：
        - list: 页面编号列表
        """
        start = max(0, current_page - range_size)
        end = min(total_pages, current_page + range_size + 1)
        return list(range(start, end))
    
    def _generate_batch(self, page_numbers, priority=0):
        """批量生成缩略图
        
        参数：
        - page_numbers: list, 页面编号列表
        - priority: int, 优先级，0-高，1-中，2-低
        """
        import time
        
        # 限制每批提交的任务数量，避免线程池被填满
        batch_size = 2  # 减少批处理大小，提高响应速度
        
        for i in range(0, len(page_numbers), batch_size):
            if not self.running:
                break
                
            batch = page_numbers[i:i + batch_size]
            for page_num in batch:
                if not self.running:
                    break
                    
                # 检查用户操作状态，优先响应用户操作
                if self.user_operation_in_progress:
                    time.sleep(0.1)
                    if not self.running:
                        break
                
                # 检查线程池是否可用
                try:
                    future = self._executor.submit(self._generate_thumbnail, page_num, 2)  # 总是生成高质量
                    future.add_done_callback(lambda f, pn=page_num: self._task_completed(f, pn, 2))
                    self._futures.append(future)
                except RuntimeError as e:
                    if 'cannot schedule new futures after shutdown' in str(e):
                        # 线程池已关闭，停止生成
                        self.running = False
                        break
                    else:
                        raise
            
            # 每批提交后暂停一下，给线程池时间处理
            if i + batch_size < len(page_numbers):
                time.sleep(0.1)  # 增加延迟，提高系统响应速度
    
    def _generate_in_batches(self, page_numbers, batch_size, priority=2):
        """分批生成缩略图
        
        参数：
        - page_numbers: list, 页面编号列表
        - batch_size: int, 每批大小
        - priority: int, 优先级
        """
        import time
        
        for i in range(0, len(page_numbers), batch_size):
            if not self.running:
                break
                
            # 检查用户操作状态，优先响应用户操作
            if self.user_operation_in_progress:
                time.sleep(0.2)
                if not self.running:
                    break
                continue
                
            batch = page_numbers[i:i + batch_size]
            self._generate_batch(batch, priority)
            
            # 每批生成后暂停一下，给系统一点时间处理其他任务
            time.sleep(0.2)  # 增加延迟，提高系统响应速度
    
    def _task_completed(self, future, page_num, quality_level):
        """任务完成回调"""
        if not self.running:
            return
        
        try:
            result = future.result()
            if result:
                page_num, pixmap = result
                # 低质量和高质量结果都发射信号，低质量快速显示，高质量更新替换
                if quality_level <= 1:
                    # 低质量或中质量缩略图直接显示
                    try:
                        self.thumbnail_generated.emit(page_num, pixmap)
                    except RuntimeError:
                        # 捕获"wrapped C/C++ object has been deleted"错误
                        pass
                else:
                    # 高质量缩略图更新替换
                    try:
                        self.thumbnail_generated.emit(page_num, pixmap)
                    except RuntimeError:
                        # 捕获"wrapped C/C++ object has been deleted"错误
                        pass
                logging.debug(f"缩略图生成完成：页面{page_num}，质量级别{quality_level}")
        except Exception as e:
            # 捕获所有异常，确保不会影响程序关闭
            try:
                logging.error(f"生成第{page_num}页缩略图失败: {str(e)}")
            except:
                pass
    
    def stop(self):
        """停止生成线程"""
        try:
            self.running = False
            self.paused = False
            
            # 取消所有未完成的任务
            for future in self._futures:
                if not future.done():
                    future.cancel()
            
            # 线程池由全局 ThreadPoolManager 统一管理，此处不关闭共享池
            # （避免组件销毁时误关全局 thumbnail 池，统一在应用退出时由 thread_pool_manager.shutdown 关闭）
            
            # 等待线程完全停止
            if self.isRunning():
                self.wait()
                
        except Exception as e:
            logging.error(f"停止缩略图生成器失败: {str(e)}")
    
    def pause(self):
        """暂停缩略图生成"""
        self.paused = True
    
    def resume(self):
        """恢复缩略图生成"""
        self.paused = False
    
    def set_user_operation_in_progress(self, in_progress):
        """设置用户操作状态
        
        参数：
        - in_progress: bool, 用户操作是否进行中
        """
        self.user_operation_in_progress = in_progress

class ThumbnailItem(QWidget):
    """
    单个缩略图项组件 - 卡片式设计
    
    功能：
    - 显示单个PDF页面的缩略图
    - 支持选中状态显示（蓝色边框高亮）
    - 显示页码标签
    - 支持点击事件
    - 悬停效果
    """
    clicked = pyqtSignal(int, int)  # 点击信号：(页码, 修饰键 0=无 1=Ctrl 2=Shift)
    
    def __init__(self, page_num, pixmap, parent=None):
        super().__init__(parent)
        self.page_num = page_num
        self.is_selected = False  # 当前浏览页（左侧竖条 + 实框 + 渐变背景）
        self.is_range_selected = False  # 区间选中（左侧竖条 + 虚框）
        self._hovering = False  # 鼠标悬停状态
        self._pixmap = pixmap
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置UI布局"""
        from PyQt6.QtWidgets import QVBoxLayout
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 缩略图标签
        self.image_label = QLabel()
        self.image_label.setPixmap(self._pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(self._pixmap.width(), self._pixmap.height())
        
        # 页码标签
        self.page_label = QLabel(f"{self.page_num + 1}")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.setLayout(layout)
        
        # 设置固定大小（包含边距）
        total_width = self._pixmap.width() + 16  # 左右边距各8px
        total_height = self._pixmap.height() + 8 + 20 + 8  # 上边距 + 图片 + 间距 + 文字 + 下边距
        self.setFixedSize(total_width, total_height)
        
        # 设置鼠标光标
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _apply_styles(self):
        """应用默认样式（未选中 / 无区间选中）"""
        from ui.styles import get_colors
        colors = get_colors()
        
        # 背景透明，由 paintEvent 绘制
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                border: none;
            }}
            QLabel {{
                background-color: transparent;
                border: none;
            }}
        """)
        self.page_label.setStyleSheet(f"""
            color: {colors.text_secondary};
            font-size: 11px;
            font-weight: 500;
            background-color: transparent;
            border: none;
        """)
        self.update()
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self._hovering = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._hovering = False
        self.update()
        super().leaveEvent(event)
    

    def mousePressEvent(self, event):
        """处理鼠标点击事件，传递修饰键信息"""
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()
            mod_flag = 0
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                mod_flag = 1  # Ctrl
            elif modifiers & Qt.KeyboardModifier.ShiftModifier:
                mod_flag = 2  # Shift
            self.clicked.emit(self.page_num, mod_flag)
        super().mousePressEvent(event)
    
    def set_selected(self, selected):
        """设置当前浏览页选中状态（左侧竖条 + 实线边框 + 渐变背景）"""
        from ui.styles import get_colors
        colors = get_colors()
        
        self.is_selected = selected
        if selected:
            # 背景透明，由 paintEvent 绘制
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: transparent;
                    border: none;
                }}
                QLabel {{
                    background-color: transparent;
                    border: none;
                }}
            """)
            self.page_label.setStyleSheet(f"""
                color: {colors.primary};
                font-size: 12px;
                font-weight: 700;
                background-color: transparent;
                border: none;
            """)
        else:
            if self.is_range_selected:
                self._apply_range_selected_style()
            else:
                self._apply_styles()
        self.update()
    
    def set_range_selected(self, selected):
        """设置区间选中状态（蓝色虚框/半透明背景）"""
        if self.is_selected:
            return  # 当前浏览页保持实框，不降级
        self.is_range_selected = selected
        if selected:
            self._apply_range_selected_style()
        else:
            self._apply_styles()
    
    def _apply_range_selected_style(self):
        """应用区间选中样式（左侧竖条 + 虚线边框 + 半透明背景）"""
        from ui.styles import get_colors
        colors = get_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                border: none;
            }}
            QLabel {{
                background-color: transparent;
                border: none;
            }}
        """)
        self.page_label.setStyleSheet(f"""
            color: {colors.primary};
            font-size: 11px;
            font-weight: 600;
            background-color: transparent;
            border: none;
        """)
        self.update()

    def paintEvent(self, event):
        """自绘选中框 — 左侧竖条 + 边框 + 背景渐变"""
        from ui.styles import get_colors
        colors = get_colors()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        r = 8  # border-radius
        
        # ── 1. 绘制背景 ──
        if self.is_selected:
            # 渐变背景：左侧从 primary_light 开始，向右淡出
            grad = QLinearGradient(0, 0, w, 0)
            primary_light = QColor(colors.primary_light)
            grad.setColorAt(0, primary_light)
            grad.setColorAt(0.4, primary_light)
            # 右侧稍微淡一点
            faded = QColor(colors.primary_light)
            faded.setAlpha(int(faded.alpha() * 0.4))
            grad.setColorAt(1, faded)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawRoundedRect(0, 0, w, h, r, r)
        elif self.is_range_selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors.primary_light))
            painter.drawRoundedRect(0, 0, w, h, r, r)
        elif self._hovering:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors.bg_hover))
            painter.drawRoundedRect(0, 0, w, h, r, r)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors.bg_card))
            painter.drawRoundedRect(0, 0, w, h, r, r)
        
        # ── 2. 绘制边框 ──
        if self.is_selected:
            pen = QPen(QColor(colors.primary), 3)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(1, 1, w - 2, h - 2, r, r)
        elif self.is_range_selected:
            pen = QPen(QColor(colors.primary), 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(1, 1, w - 2, h - 2, r, r)
        elif self._hovering:
            pen = QPen(QColor(colors.border), 2)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(1, 1, w - 2, h - 2, r, r)
        
        # ── 3. 绘制左侧竖条（仅选中/区间选中时）──
        bar_width = 4 if self.is_selected else 3
        if self.is_selected or self.is_range_selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors.primary))
            # 竖条：左侧圆角只画左半边，右侧直角
            bar_rect_x = 1
            bar_rect_y = 4
            bar_rect_w = bar_width
            bar_rect_h = h - 8
            # 简单画一个小圆角矩形
            painter.drawRoundedRect(bar_rect_x, bar_rect_y, bar_rect_w, bar_rect_h, 2, 2)
        
        painter.end()

class ThumbnailWidget(QScrollArea):
    """
    自定义缩略图组件 - 卡片式网格布局
    
    核心设计原则：
    - 卡片式缩略图设计，带页码标签
    - 当前浏览页蓝色实框高亮
    - 支持多选区间（Shift区间 / Ctrl切换单页）
    - 区间选中页蓝色虚框半透明
    - 支持根据可用宽度自动调整列数
    - 实现缩略图的居中对齐
    - 支持缩略图的添加、移除和点击事件
    """
    thumbnail_clicked = pyqtSignal(int)  # 缩略图点击信号，传递页码（跳转浏览区）
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_viewer = parent
        self.icon_width = 90  # 缩略图图片宽度
        self.icon_height = 120  # 缩略图图片高度
        self.card_width = self.icon_width + 16  # 卡片总宽度（包含边距）
        self.card_height = self.icon_height + 36  # 卡片总高度（图片 + 页码 + 边距）
        self.horizontal_spacing = 12  # 缩略图水平间距
        self.vertical_spacing = 12  # 缩略图垂直间距
        self.top_margin = 12  # 顶部边距
        self.bottom_margin = 12  # 底部边距
        
        # 多选状态
        self._range_selected_pages = set()  # 区间选中的页码集合
        self._last_clicked_page = None  # 上次点击的页码（用于Shift区间选择）
        
        # 设置滚动条政策
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setWidgetResizable(True)
        
        # 创建内容部件和网格布局
        self.content_widget = QWidget()
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)  # 顶部居中
        self.grid_layout.setHorizontalSpacing(self.horizontal_spacing)
        self.grid_layout.setVerticalSpacing(self.vertical_spacing)
        self.grid_layout.setContentsMargins(12, self.top_margin, 12, self.bottom_margin)
        
        # 设置内容部件
        self.setWidget(self.content_widget)
        
        # 存储缩略图项
        self.thumbnail_items = []
        
        # 应用现代样式
        self._apply_modern_style()
    
    def _apply_modern_style(self):
        """应用现代样式"""
        from ui.styles import get_colors
        colors = get_colors()
        
        # 设置滚动区域背景
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {colors.bg_content};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {colors.bg_content};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {colors.border};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {colors.text_secondary};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        self.content_widget.setStyleSheet(f"""
            background-color: {colors.bg_content};
        """)
    
    def update_background(self):
        """更新背景色（已集成到_apply_modern_style）"""
        pass  # 现代样式已统一处理背景色
    
    def add_thumbnail(self, page_num, pixmap):
        """添加缩略图"""
        # 创建缩略图项
        thumbnail_item = ThumbnailItem(page_num, pixmap, self.content_widget)
        thumbnail_item.clicked.connect(self._on_item_clicked)
        
        # 添加到列表
        self.thumbnail_items.append(thumbnail_item)
        
        # 重新排列缩略图
        self.rearrange_thumbnails()
    
    def _on_item_clicked(self, page_num, mod_flag):
        """处理缩略图点击事件，支持 Ctrl/Shift 多选"""
        if mod_flag == 0:
            # 普通点击：清除区间选中，跳转浏览区
            self.clear_range_selection()
            self._last_clicked_page = page_num
            self.thumbnail_clicked.emit(page_num)
        elif mod_flag == 1:
            # Ctrl+点击：切换该页的区间选中状态
            if page_num in self._range_selected_pages:
                self._range_selected_pages.discard(page_num)
                item = self._get_item_by_page(page_num)
                if item:
                    item.set_range_selected(False)
            else:
                self._range_selected_pages.add(page_num)
                item = self._get_item_by_page(page_num)
                if item and not item.is_selected:
                    item.set_range_selected(True)
            self._last_clicked_page = page_num
            # Ctrl+点击不跳转浏览区，只更新选中状态
            self._emit_range_navigation()
        elif mod_flag == 2:
            # Shift+点击：区间选择（从上次点击到当前页）
            self.clear_range_selection()
            if self._last_clicked_page is not None:
                start = min(self._last_clicked_page, page_num)
                end = max(self._last_clicked_page, page_num)
                for pn in range(start, end + 1):
                    self._range_selected_pages.add(pn)
                    item = self._get_item_by_page(pn)
                    if item and not item.is_selected:
                        item.set_range_selected(True)
            self._last_clicked_page = page_num
            self._emit_range_navigation()
    
    def _emit_range_navigation(self):
        """当区间选中存在时，发射跳转信号（跳转到最小页码）"""
        all_selected = self._range_selected_pages.copy()
        # 加上当前浏览页
        for item in self.thumbnail_items:
            if item.is_selected:
                all_selected.add(item.page_num)
                break
        if all_selected:
            self.thumbnail_clicked.emit(min(all_selected))
    
    def remove_all_thumbnails(self):
        """移除所有缩略图"""
        # 移除所有布局中的项
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widget.deleteLater()
        
        # 清空列表
        self.thumbnail_items.clear()
    
    def rearrange_thumbnails(self):
        """重新排列缩略图，根据可用宽度调整列数"""
        # 移除所有项但保留widget引用
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                self.grid_layout.removeItem(item)
        
        if not self.thumbnail_items:
            return
        
        # 计算可用宽度（考虑滚动条宽度）
        scrollbar_width = self.verticalScrollBar().width() if self.verticalScrollBar().isVisible() else 0
        available_width = self.width() - scrollbar_width - 24  # 减去滚动条宽度和左右边距
        
        # 计算最大列数（基于卡片宽度）
        max_columns = max(1, available_width // (self.card_width + self.horizontal_spacing))
        
        # 按页码排序缩略图
        sorted_thumbnails = sorted(self.thumbnail_items, key=lambda x: x.page_num)
        
        # 排列缩略图到网格中
        for index, thumbnail in enumerate(sorted_thumbnails):
            row = index // max_columns
            col = index % max_columns
            self.grid_layout.addWidget(thumbnail, row, col, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def resizeEvent(self, event):
        """窗口大小变化时重新排列缩略图"""
        super().resizeEvent(event)
        self.rearrange_thumbnails()
    
    def select_thumbnail(self, page_num):
        """选中指定页码的缩略图（当前浏览页）
        
        同时清除区间选中状态，保持单选语义。
        参考 Adobe Acrobat / pdf.js 标准：无论双页还是单页模式，
        缩略图始终只高亮一个（当前可见的第一个页面）。
        """
        self.clear_range_selection()
        for thumbnail in self.thumbnail_items:
            if thumbnail.page_num == page_num:
                thumbnail.set_selected(True)
            else:
                thumbnail.set_selected(False)
                thumbnail.set_range_selected(False)
    
    def clear_range_selection(self):
        """清除所有区间选中状态"""
        for page_num in list(self._range_selected_pages):
            item = self._get_item_by_page(page_num)
            if item:
                item.set_range_selected(False)
        self._range_selected_pages.clear()
    
    def _get_item_by_page(self, page_num):
        """根据页码查找缩略图项"""
        for item in self.thumbnail_items:
            if item.page_num == page_num:
                return item
        return None
    
    def get_selected_pages(self):
        """获取所有选中的页码（当前浏览页 + 区间选中页）"""
        pages = set(self._range_selected_pages)
        for item in self.thumbnail_items:
            if item.is_selected:
                pages.add(item.page_num)
                break
        return sorted(pages)
    
    def scroll_to_thumbnail(self, page_num):
        """滚动到指定页码的缩略图"""
        for thumbnail in self.thumbnail_items:
            if thumbnail.page_num == page_num:
                self.ensureWidgetVisible(thumbnail)
                break
    
    def count(self):
        """返回缩略图数量"""
        return len(self.thumbnail_items)
    
    def clear(self):
        """清除所有缩略图"""
        self.remove_all_thumbnails()
    
    def item(self, index):
        """返回指定索引的缩略图项（兼容旧接口）"""
        if 0 <= index < len(self.thumbnail_items):
            return self.thumbnail_items[index]
        return None
    
    def visualItemRect(self, item):
        """返回指定项的可视矩形（兼容旧接口）"""
        if item in self.thumbnail_items:
            return item.geometry()
        return None
    
    def viewport(self):
        """返回视口（兼容旧接口）"""
        return super().viewport()

class ThumbnailSync:
    """
    缩略图与浏览区随动功能封装
    
    功能：
    - 实现缩略图列表与浏览区域的双向同步
    - 浏览区域滚动时自动高亮并滚动到对应缩略图
    - 点击缩略图时自动滚动浏览区域到对应页面
    - 管理缩略图的高亮显示和滚动定位
    """
    
    def __init__(self, thumbnail_list, scroll_area, pdf_viewer):
        super().__init__()
        self.thumbnail_list = thumbnail_list
        self.scroll_area = scroll_area
        self.pdf_viewer = pdf_viewer
        self.current_page = pdf_viewer.current_page if hasattr(pdf_viewer, 'current_page') else 0
        self.total_pages = pdf_viewer.total_pages if hasattr(pdf_viewer, 'total_pages') else 0
        self._is_valid = True  # 标记对象是否有效
        self._updating = False  # 标记是否正在更新，防止递归
        self._user_action = False  # 标记是否为用户操作
        self._scroll_in_progress = False  # 标记是否正在滚动页面，防止递归
        self._programmatic_scroll = False  # 标记是否为程序主动设置的滚动位置（非用户滚动）
        
        try:
            # 设置信号连接
            self.setup_connections()
        except Exception as e:
            logging.error(f"初始化ThumbnailSync失败: {str(e)}")
            self._is_valid = False
    
    def setup_connections(self):
        """设置随动功能的信号连接"""
        # 导入QTimer用于防抖
        from PyQt6.QtCore import QTimer
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self._on_scroll_timeout)
        
        # 存储当前滚动值
        self.current_scroll_value = 0
        
        # 监听浏览区滚动事件
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)
        
        # 监听缩略图点击事件
        self.thumbnail_list.thumbnail_clicked.connect(self.on_thumbnail_clicked)
    
    def _on_scroll_value_changed(self, value):
        """滚动值变化时的处理，使用防抖机制
        
        程序主动设置滚动位置时（_programmatic_scroll=True）不启动防抖定时器，
        避免程序性滚动被错误地解释为用户翻页。
        
        检查两处锁：
        1. ThumbnailSync 自身的 _programmatic_scroll（缩略图点击、scroll_to_page）
        2. 当前视图类型的 _programmatic_scroll（show_page、_scroll_to_unit）
        """
        if not self._is_valid:
            return
        # 检查自身锁
        if self._programmatic_scroll:
            return
        # 检查当前视图类型的锁
        if self._is_viewtype_scrolling():
            return
        try:
            self.current_scroll_value = value
            # 设置防抖时间为30ms
            self.scroll_timer.start(30)
        except Exception as e:
            logging.error(f"处理滚动值变化失败: {str(e)}")
            self._is_valid = False
    
    def _on_scroll_timeout(self):
        """防抖超时后更新缩略图位置
        
        核心原则：只更新缩略图高亮，不触发主视图的 show_page。
        主视图的 current_page 由自身 show_page() 统一管理，
        缩略图随动只做"读滚动位置→高亮缩略图"这一件事。
        """
        if not self._is_valid or self._updating or self._user_action:
            return
        try:
            self._updating = True
            # 尝试根据滚动位置计算当前页面
            current_page = self._calculate_current_page_from_scroll(self.current_scroll_value)
            
            # 如果计算成功，更新缩略图高亮
            if current_page >= 0 and current_page < self.total_pages and current_page != self.current_page:
                self.current_page = current_page
                
                # 高亮显示对应的缩略图
                self.highlight_thumbnail(current_page)
                
                # 滚动缩略图列表到当前缩略图位置
                self.scroll_to_thumbnail(current_page)
        except Exception as e:
            logging.error(f"处理滚动超时失败: {str(e)}")
            self._is_valid = False
        finally:
            self._updating = False
    
    def _calculate_current_page_from_scroll(self, scroll_value):
        """根据滚动位置计算当前页面（支持单页连续和双页连续模式）"""
        if not self._is_valid:
            return self.current_page
        try:
            # 检查是否有视图类型管理器和当前视图类型
            if hasattr(self.pdf_viewer, 'viewtype_manager') and self.pdf_viewer.viewtype_manager:
                current_viewtype = self.pdf_viewer.viewtype_manager.current_viewtype
                if current_viewtype is None:
                    return self.current_page
                
                viewtype_name = self.pdf_viewer.viewtype_manager.get_current_viewtype_name()
                
                # 判断是双页连续模式还是单页连续模式
                if viewtype_name == "two_page_spread_continuous":
                    # ── 双页连续模式 ──
                    # spread_labels 键为 "spread_0", "spread_1", ...
                    # 每个 spread 包含两页: spread_0 → page 0+1, spread_1 → page 2+3
                    return self._calculate_page_from_spread_scroll(scroll_value, current_viewtype)
                elif viewtype_name == "single_page_continuous":
                    # ── 单页连续模式 ──
                    return self._calculate_page_from_single_scroll(scroll_value, current_viewtype)
                # 双页（非连续）和单页模式不存在滚动翻页，直接返回当前页
        except Exception as e:
            import logging
            logging.error(f"根据滚动位置计算当前页面失败: {str(e)}")
        
        # 如果计算失败，返回当前页面
        return self.current_page
    
    def _is_viewtype_scrolling(self):
        """检查当前视图类型是否在程序滚动状态中"""
        try:
            if hasattr(self.pdf_viewer, 'viewtype_manager') and self.pdf_viewer.viewtype_manager:
                viewtype = self.pdf_viewer.viewtype_manager.current_viewtype
                if viewtype and hasattr(viewtype, '_programmatic_scroll'):
                    return viewtype._programmatic_scroll
        except Exception:
            pass
        return False
    
    def _calculate_page_from_single_scroll(self, scroll_value, current_viewtype):
        """单页连续模式：根据滚动位置计算当前页面"""
        cumulative_height = 0
        page_spacing = 10  # 默认页面间距
        
        try:
            from utils.constants import Constants
            page_spacing = Constants.PAGE_SPACING.value
        except:
            pass
        
        for page_num, page_label in sorted(current_viewtype.page_labels.items()):
            try:
                page_height = page_label.height()
            except RuntimeError:
                continue
            
            half_page_height = page_height / 2
            
            if scroll_value < cumulative_height + half_page_height + page_spacing:
                return page_num
            
            cumulative_height += page_height + page_spacing
        
        return self.current_page
    
    def _calculate_page_from_spread_scroll(self, scroll_value, current_viewtype):
        """双页连续模式：根据滚动位置计算当前页面
        
        spread_labels 键为 "spread_0", "spread_1", ...
        spread_N 包含 page (N*2) 和 page (N*2+1)
        """
        total_pages = self.total_pages
        
        # 将 spread_labels 按序号排序
        sorted_spreads = []
        for key in current_viewtype.spread_labels:
            try:
                spread_num = int(key.split('_')[1])
                sorted_spreads.append((spread_num, key))
            except (ValueError, IndexError):
                continue
        sorted_spreads.sort()
        
        if not sorted_spreads:
            return self.current_page
        
        cumulative_height = 0
        page_spacing = 10
        
        try:
            from utils.constants import Constants
            page_spacing = Constants.PAGE_SPACING.value
        except:
            pass
        
        for spread_num, key in sorted_spreads:
            page_label = current_viewtype.spread_labels[key]
            try:
                if page_label is not None:
                    spread_height = page_label.height()
                else:
                    spread_height = 0
            except RuntimeError:
                continue
            
            # 每个 spread 的起始页码
            page1_num = spread_num * 2
            
            # 如果是最后一个 spread 且只有一个页面
            is_last_spread = (page1_num + 1 >= total_pages)
            
            half_spread_height = spread_height / 2
            
            if scroll_value < cumulative_height + half_spread_height + page_spacing:
                # 滚动位置在这个 spread 内，返回左侧页码
                # （配对右侧页码由 _get_visible_pages 自动计算）
                return page1_num
            
            cumulative_height += spread_height + page_spacing
        
        # 如果超出所有已知 spread，返回最后一个已知 spread 的页码
        if sorted_spreads:
            last_spread_num = sorted_spreads[-1][0]
            return last_spread_num * 2
        
        return self.current_page
    
    def highlight_thumbnail(self, page_num):
        """高亮显示指定页码的缩略图
        
        参考 pdf.js / Adobe Acrobat 标准：
        无论双页还是单页模式，缩略图始终只高亮一个。
        """
        if not self._is_valid:
            return
        try:
            self.thumbnail_list.select_thumbnail(page_num)
        except Exception as e:
            logging.error(f"高亮缩略图失败: {str(e)}")
            self._is_valid = False
    
    def scroll_to_thumbnail(self, page_num):
        """滚动缩略图列表到指定页码的缩略图位置"""
        if not self._is_valid:
            return
        try:
            self.thumbnail_list.scroll_to_thumbnail(page_num)
        except Exception as e:
            logging.error(f"滚动缩略图失败: {str(e)}")
            self._is_valid = False
    
    def on_thumbnail_clicked(self, page_num):
        """缩略图点击时更新浏览区位置"""
        if not self._is_valid or self._updating:
            return
        try:
            self._updating = True
            self._user_action = True  # 标记为用户操作
            self._programmatic_scroll = True  # 后续的滚动是程序主动设置的
            if page_num is not None and page_num >= 0 and page_num < self.total_pages:
                # 更新当前页码
                self.current_page = page_num
                
                # 滚动浏览区到对应的页面位置
                self.scroll_to_page(page_num)
        except Exception as e:
            logging.error(f"处理缩略图点击失败: {str(e)}")
            self._is_valid = False
        finally:
            # 延迟重置标志，避免滚动事件干扰
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(300, self._reset_user_action)
    
    def _reset_user_action(self):
        """重置用户操作标志和程序滚动标志"""
        self._updating = False
        self._user_action = False
        self._programmatic_scroll = False
    
    def _reset_programmatic_scroll(self):
        """仅重置程序滚动标志"""
        self._programmatic_scroll = False
    
    def scroll_to_page(self, page_num):
        """滚动浏览区到指定页码的页面位置"""
        if not self._is_valid:
            return
        # 防止递归调用
        if hasattr(self, '_scroll_in_progress') and self._scroll_in_progress:
            return
        try:
            self._scroll_in_progress = True
            self._programmatic_scroll = True  # 标记为程序主动滚动
            if self.pdf_viewer and hasattr(self.pdf_viewer, 'show_page'):
                self.pdf_viewer.show_page(page_num)
            # 延迟重置，让布局事件处理完毕
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(300, self._reset_programmatic_scroll)
        except Exception as e:
            logging.error(f"滚动到页面失败: {str(e)}")
            self._is_valid = False
        finally:
            self._scroll_in_progress = False
    
    def update_current_page(self, page_num):
        """更新当前页码信息"""
        if not self._is_valid or self._updating:
            return
        try:
            self._updating = True
            self.current_page = page_num
            self.highlight_thumbnail(page_num)
            # 滚动缩略图列表到当前缩略图位置
            self.scroll_to_thumbnail(page_num)
        except Exception as e:
            logging.error(f"更新当前页码失败: {str(e)}")
            self._is_valid = False
        finally:
            self._updating = False
    
    def update_total_pages(self, total_pages):
        """更新总页数信息"""
        if not self._is_valid:
            return
        try:
            self.total_pages = total_pages
        except Exception as e:
            logging.error(f"更新总页数失败: {str(e)}")
            self._is_valid = False

class ThumbnailManager:
    """
    缩略图管理类
    
    负责：
    - 创建和管理缩略图面板
    - 异步生成缩略图
    - 管理缩略图与浏览区的随动
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.thumbnail_generator = None
        self.current_generator = None
        self.thumbnail_sync = None
        self.thumbnail_list = None
        
        # 订阅页面更新事件
        event_bus.page_updated.connect(self._on_page_updated)
    
    def create_thumbnail_panel(self):
        """创建左侧缩略图面板"""
        # 使用自定义的缩略图组件，实现居中对齐和自适应布局
        self.thumbnail_list = ThumbnailWidget(self.parent)
        
        # 修复：当viewport背景色变化时，同步更新缩略图区域背景色
        if hasattr(self.parent, 'scroll_area'):
            self.parent.scroll_area.installEventFilter(self.parent)
        
        return self.thumbnail_list
    
    def generate_thumbnails(self, doc, doc_mutex):
        """生成文档的所有缩略图"""
        # 停止之前的生成器（如果存在）
        self.stop_generation()
        
        # 清空旧的缩略图列表
        if self.thumbnail_list:
            self.thumbnail_list.remove_all_thumbnails()
            # 强制触发UI更新
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
        
        # 获取文件路径
        file_path = ""
        if hasattr(self.parent, 'pdf_manager') and self.parent.pdf_manager:
            file_path = self.parent.pdf_manager.get_file_path() or ""
        
        # 创建新的生成器
        try:
            self.thumbnail_generator = ThumbnailGenerator(doc, doc_mutex, file_path, self.parent)
            self.thumbnail_generator.thumbnail_generated.connect(self.update_thumbnail)
            
            # 设置当前生成器
            self.current_generator = self.thumbnail_generator
            
            # 获取当前页面编号
            current_page = self.parent.current_page if hasattr(self.parent, 'current_page') else 0
            
            # 开始生成缩略图，提供当前页面参数
            self.thumbnail_generator.current_page = current_page
            self.thumbnail_generator.start()
            
            # 初始化缩略图与浏览区随动功能
            if hasattr(self.parent, 'scroll_area') and self.thumbnail_list:
                try:
                    # 断开之前的信号连接
                    if self.thumbnail_sync:
                        self.thumbnail_sync = None
                    
                    # 创建新的thumbnail_sync对象
                    self.thumbnail_sync = ThumbnailSync(self.thumbnail_list, self.parent.scroll_area, self.parent)
                    # 更新总页数
                    total_pages = self.parent.total_pages if hasattr(self.parent, 'total_pages') else 0
                    self.thumbnail_sync.update_total_pages(total_pages)
                    # 更新当前页码
                    current_page = self.parent.current_page if hasattr(self.parent, 'current_page') else 0
                    self.thumbnail_sync.update_current_page(current_page)
                except Exception as e:
                    import logging
                    logging.error(f"初始化缩略图随动功能失败: {str(e)}")
        except Exception as e:
            import logging
            logging.error(f"创建缩略图生成器失败: {str(e)}")
    
    def update_thumbnail(self, page_num, pixmap):
        """更新单个缩略图"""
        # 确保只处理当前ThumbnailGenerator线程发射的信号
        if not self.current_generator:
            return
        
        # 检查缩略图列表是否有效
        if not self.thumbnail_list:
            return
        
        try:
            # 添加缩略图
            self.thumbnail_list.add_thumbnail(page_num, pixmap)
            
            # 强制触发UI更新
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
        except Exception as e:
            import logging
            logging.error(f"更新缩略图失败: {str(e)}")
    
    def update_current_page(self, page_num):
        """更新当前页码，用于同步缩略图"""
        if self.thumbnail_sync:
            self.thumbnail_sync.update_current_page(page_num)
    
    def update_total_pages(self, total_pages):
        """更新总页数，用于同步缩略图"""
        if self.thumbnail_sync:
            self.thumbnail_sync.update_total_pages(total_pages)
    
    def pause_thumbnail_generation(self):
        """暂停缩略图生成"""
        if self.thumbnail_generator:
            self.thumbnail_generator.pause()
    
    def resume_thumbnail_generation(self):
        """恢复缩略图生成"""
        if self.thumbnail_generator:
            self.thumbnail_generator.resume()
    
    def set_user_operation_in_progress(self, in_progress):
        """设置用户操作状态
        
        参数：
        - in_progress: bool, 用户操作是否进行中
        """
        if self.thumbnail_generator:
            self.thumbnail_generator.set_user_operation_in_progress(in_progress)
        
        # 同时设置 thumbnail_sync 的用户操作标志，防止循环更新
        if self.thumbnail_sync:
            self.thumbnail_sync._user_action = in_progress
    
    def stop_generation(self):
        """停止缩略图生成"""
        # 清理thumbnail_sync对象
        if hasattr(self, 'thumbnail_sync') and self.thumbnail_sync:
            # 直接设置为None，不再尝试访问可能已销毁的对象
            self.thumbnail_sync = None
        
        # 停止生成器
        if self.thumbnail_generator:
            # 先设置running为False
            self.thumbnail_generator.running = False
            # 等待线程结束
            if self.thumbnail_generator.isRunning():
                self.thumbnail_generator.wait(1000)  # 最多等待1秒
            # 清理引用
            self.thumbnail_generator = None
        
        # 重置当前生成器
        self.current_generator = None
    
    def _on_page_updated(self, page_num):
        """处理页面更新事件
        
        当页面更新时，更新缩略图的高亮和滚动位置
        
        参数：
        - page_num: int, 页面编号
        """
        try:
            # 更新当前页码，用于同步缩略图
            self.update_current_page(page_num)
        except Exception as e:
            logging.error(f"处理页面更新事件失败: {str(e)}")

# PDF浏览器 - 用户手册

## 1. 功能说明

PDF浏览器是一款功能丰富的PDF文件浏览工具，支持多种浏览模式和高级功能。

### 1.1 核心功能

- **PDF文件浏览**：打开、查看PDF文件
- **页面导航**：前后翻页、跳转到指定页面
- **缩放控制**：放大、缩小、适应窗口
- **多浏览视图类型**：
  - 单页浏览
  - 单页连续浏览
  - 双页浏览
  - 双页连续浏览
- **缩略图导航**：左侧显示缩略图，支持点击切换页面
- **区域选择**：支持选择PDF中的区域，提取图像
- **图形检测**：基于模板匹配的图形检测与统计
- **实时可视化**：检测结果实时显示在PDF页面上
- **阅读模式**：专注阅读体验，隐藏缩略图面板

### 1.2 技术特点

- 基于PyQt6的现代化GUI界面
- 采用MVC架构，代码结构清晰
- 依赖注入设计，提高代码可维护性和可测试性
- 线程安全设计，确保多线程操作的稳定性
- 支持LRU缓存，提高性能
- 实时日志记录，便于调试和问题追踪
- 服务层设计，封装核心业务逻辑

## 2. 操作指南

### 2.1 基本操作

#### 2.1.1 打开文件

1. 点击工具栏中的"打开"按钮
2. 在弹出的文件选择对话框中选择PDF文件
3. 点击"打开"按钮

#### 2.1.2 页面导航

- **上一页**：点击工具栏中的"上一页"按钮或使用Page Up键
- **下一页**：点击工具栏中的"下一页"按钮或使用Page Down键
- **跳转到指定页面**：在页码输入框中输入页码，按Enter键

#### 2.1.3 缩放控制

- **放大**：点击工具栏中的"放大"按钮或使用Ctrl++快捷键
- **缩小**：点击工具栏中的"缩小"按钮或使用Ctrl+-快捷键
- **适应窗口**：点击工具栏中的"适应窗口"按钮

#### 2.1.4 浏览视图类型切换

在工具栏中点击对应的浏览视图类型按钮：
- 单页浏览
- 单页连续浏览
- 双页浏览
- 双页连续浏览

#### 2.1.5 阅读模式切换

点击工具栏中的"阅读模式"按钮，可切换到专注阅读模式，隐藏左侧缩略图面板。

### 2.2 高级操作

#### 2.2.1 区域选择

1. 点击工具栏中的"选择模式"按钮
2. 在PDF页面上拖动鼠标选择区域
3. 松开鼠标完成选择
4. 可以提取选中的图像用于检测

#### 2.2.2 图形检测

1. 选择一个区域作为模板图像
2. 点击工具栏中的"图形检测"按钮
3. 在弹出的参数设置对话框中调整检测参数
4. 点击"开始检测"按钮
5. 检测结果将实时显示在PDF页面上

### 2.3 缩略图操作

- **点击缩略图**：跳转到对应的页面
- **调整缩略图面板大小**：拖动分割线调整左侧缩略图面板的宽度
- **单列/多列显示**：缩略图会根据面板宽度自动调整列数

## 3. 快捷键说明

| 快捷键 | 功能 |
|--------|------|
| Ctrl++ | 放大 |
| Ctrl+- | 缩小 |
| Ctrl+0 | 适应窗口 |
| Page Up | 上一页 |
| Page Down | 下一页 |
| Home | 第一页 |
| End | 最后一页 |
| 方向键 | 滚动页面 |

---

# PDF浏览器 - 技术文档

## 1. 架构设计

### 1.1 整体架构

PDF浏览器采用MVC（Model-View-Controller）架构设计，结合依赖注入模式，将应用程序分为多个层次：

- **Model**：负责数据管理和业务逻辑
- **View**：负责用户界面显示
- **Controller**：负责处理用户输入和协调Model与View
- **Service**：封装核心业务逻辑，提供统一接口
- **Dependency Injection**：管理对象依赖，提高代码可测试性

### 1.2 模块划分

```
├── business/        # 业务逻辑层
│   ├── interfaces/  # 接口定义
│   ├── page_cache.py       # 页面缓存
│   ├── page_renderer.py    # 页面渲染
│   └── pdf_manager.py      # PDF文档管理
├── config/          # 配置文件
├── detection/       # 图形检测模块
├── models/          # 模型文件
├── services/        # 服务层
│   ├── event_bus.py         # 事件总线
│   ├── pdf_service.py       # PDF服务
│   └── zoom_service.py      # 缩放服务
├── ui/              # UI组件
│   ├── content_area.py      # 内容区域
│   ├── graphic_detection_manager.py  # 图形检测管理器
│   ├── navigation_controller.py  # 导航控制器
│   ├── pdf_main_window.py   # 主窗口
│   ├── thumbnail_manager.py # 缩略图管理器
│   ├── toolbar_manager.py   # 工具栏管理器
│   ├── viewport_manager.py  # 视口管理器
│   └── zoom_controller.py   # 缩放控制器
├── utils/           # 工具函数
│   ├── config_loader.py     # 配置加载
│   ├── constants.py         # 常量定义
│   └── di_container.py      # 依赖注入容器
├── viewtypes/       # 浏览视图类型
│   ├── base.py              # 基础视图类型
│   ├── manager.py           # 视图类型管理器
│   ├── single_page_viewtype.py  # 单页视图
│   ├── single_page_continuous_viewtype.py  # 单页连续视图
│   ├── two_page_viewtype.py  # 双页视图
│   └── two_page_continuous_viewtype.py  # 双页连续视图
├── tests/           # 测试代码
└── pdf_viewer.py    # 主程序入口
```

### 1.3 核心类关系

```
PDFMainWindow (主窗口)
├── ToolbarManager (工具栏管理)
├── NavigationController (导航控制)
├── ZoomController (缩放控制)
├── ThumbnailManager (缩略图管理)
├── ViewtypeManager (视图类型管理)
│   ├── SinglePageViewtype (单页视图类型)
│   ├── SinglePageContinuousViewtype (单页连续视图类型)
│   ├── TwoPageViewtype (双页视图类型)
│   └── TwoPageContinuousViewtype (双页连续视图类型)
├── PDFService (PDF服务)
│   ├── PDFManager (文档管理)
│   ├── PDFProcessor (PDF渲染处理器)
│   └── PageCache (页面缓存)
└── ZoomService (缩放服务)
```

## 2. API说明

### 2.1 核心服务

#### 2.1.1 PDFService

```python
class PDFService:
    def open_document(self, file_path):
        """打开PDF文档"""
        pass
    
    def close_document(self):
        """关闭PDF文档"""
        pass
    
    def get_page_count(self):
        """获取文档页数"""
        pass
    
    def render_page(self, page_num, zoom_level):
        """渲染指定页码的页面"""
        pass
    
    def get_page_size(self, page_num, zoom_level):
        """获取页面尺寸"""
        pass
    
    def preload_pages(self, current_page, preload_range, zoom_level):
        """预加载页面"""
        pass
```

#### 2.1.2 ZoomService

```python
class ZoomService:
    def set_zoom_level(self, zoom_level):
        """设置缩放级别"""
        pass
    
    def get_zoom_level(self):
        """获取当前缩放级别"""
        pass
    
    def zoom_in(self):
        """放大"""
        pass
    
    def zoom_out(self):
        """缩小"""
        pass
    
    def fit_to_window(self):
        """适应窗口"""
        pass
```

### 2.2 核心管理器

#### 2.2.1 PDFManager

```python
class PDFManager:
    def open_document(self, file_path):
        """打开PDF文档"""
        pass
    
    def close_document(self):
        """关闭PDF文档"""
        pass
    
    def get_page_count(self):
        """获取文档页数"""
        pass
    
    def get_document(self):
        """获取文档对象"""
        pass
    
    def get_document_mutex(self):
        """获取文档访问锁"""
        pass
    
    def is_document_open(self):
        """检查文档是否打开"""
        pass
```

#### 2.2.2 PageRenderer

```python
class PageRenderer:
    def render_page(self, doc, page_num, zoom_level):
        """渲染指定页码的页面"""
        pass
    
    def get_page_size(self, doc, page_num, zoom_level):
        """获取渲染后的页面尺寸"""
        pass
```

#### 2.2.3 PageCache

```python
class PageCache:
    def add_page(self, page_num, zoom_level, pixmap):
        """添加页面到缓存"""
        pass
    
    def get_page(self, page_num, zoom_level):
        """从缓存获取页面"""
        pass
    
    def clear(self):
        """清空缓存"""
        pass
```

#### 2.2.4 ViewportManager

```python
class ViewportManager:
    def set_scroll_area(self, scroll_area):
        """设置滚动区域"""
        pass
    
    def get_viewport_width(self):
        """获取当前视口宽度"""
        pass
    
    def get_viewport_height(self):
        """获取当前视口高度"""
        pass
    
    def get_viewport_size(self):
        """获取当前视口尺寸"""
        pass
    
    def get_viewport_center(self):
        """获取当前视口中心坐标"""
        pass
    
    def add_observer(self, observer):
        """添加视口尺寸变化的观察者"""
        pass
    
    def remove_observer(self, observer):
        """移除视口尺寸变化的观察者"""
        pass
    
    def update_viewport_size(self):
        """更新视口尺寸"""
        pass
    
    def enable_listening(self, enabled):
        """启用或禁用尺寸变化监听"""
        pass
    
    def is_listening_enabled(self):
        """检查是否启用了尺寸变化监听"""
        pass
    
    def clear(self):
        """清理资源"""
        pass
```

## 3. 模块关系

### 3.1 模块依赖关系

```
pdf_viewer.py
├── ui/pdf_main_window.py
│   ├── services/pdf_service.py
│   │   ├── business/pdf_manager.py
│   │   ├── business/page_renderer.py
│   │   └── business/page_cache.py
│   ├── services/zoom_service.py
│   ├── viewtypes/manager.py
│   ├── ui/toolbar_manager.py
│   ├── ui/navigation_controller.py
│   ├── ui/zoom_controller.py
│   ├── ui/thumbnail_manager.py
│   └── ui/content_area.py
└── utils/di_container.py
```

### 3.2 模块交互流程

#### 3.2.1 打开文件流程

1. 用户点击"打开"按钮
2. PDFMainWindow调用PDFService.open_document()
3. PDFService调用PDFManager.open_document()
4. PDFManager打开PDF文档并返回结果
5. PDFMainWindow调用ThumbnailManager.generate_thumbnails()
6. ThumbnailManager异步生成缩略图
7. 显示第一页内容
8. 激活默认视图类型

#### 3.2.2 页面渲染流程

1. 用户切换页面或调整缩放级别
2. PDFMainWindow调用PDFService.render_page()
3. PDFService检查PageCache中是否有缓存
4. 如果有缓存，直接返回缓存内容
5. 如果没有缓存，调用PageRenderer渲染页面并添加到缓存
6. 更新UI显示渲染结果

## 4. 代码注释规范

### 4.1 类注释

```python
class ClassName:
    """
    类的功能描述
    
    参数：
    - param1: 参数1的描述
    - param2: 参数2的描述
    
    功能：
    - 功能1描述
    - 功能2描述
    
    依赖：
    - 依赖1描述
    - 依赖2描述
    """
    pass
```

### 4.2 方法注释

```python
def method_name(self, param1, param2):
    """
    方法功能描述
    
    参数：
    - param1: 参数1的描述
    - param2: 参数2的描述
    
    返回：
    - 返回值类型：返回值描述
    
    异常：
    - ExceptionType: 异常描述
    """
    pass
```

### 4.3 代码注释示例

```python
# 这是一个单行注释

"""
这是一个多行注释，
用于描述复杂的代码块
"""

# 初始化变量
variable = 0

# 循环处理列表
for item in items:  # 遍历所有项目
    process_item(item)
```

## 5. 开发环境

### 5.1 系统要求

- Python 3.14+
- Windows系统

### 5.2 核心依赖

- PyQt6>=6.0.0: GUI界面实现
- PyMuPDF>=1.19.0: PDF加载与渲染
- opencv-python>=4.5.0: 图像处理与目标检测
- numpy>=1.19.0: 数值计算
- ultralytics>=8.0.0: 目标检测模型

### 5.3 安装依赖

```bash
pip install -r requirements.txt
```

## 6. 运行程序

```bash
python pdf_viewer.py
```

## 7. 测试

```bash
pytest
```

## 8. 日志记录

程序运行时会生成日志文件 `pdf_viewer.log`，记录程序的运行状态和错误信息。

---

# 项目更新日志

## v1.1.0 (2026-01-29)

- 重构架构，引入依赖注入容器
- 添加服务层，封装核心业务逻辑
- 改进缩略图生成机制，提高性能
- 添加阅读模式，提供专注阅读体验
- 优化页面渲染流程，支持预加载
- 完善键盘导航功能，支持方向键滚动
- 更新依赖管理，添加ultralytics库

## v1.2.0 (2026-02-03)

- 添加ViewportManager服务类，实现集中化的视口尺寸管理
- 实现视口尺寸变化的自动监听和通知机制
- 修改现有代码，使用ViewportManager获取视口尺寸
- 添加ViewportManager单元测试
- 完善ViewportManager文档

## v1.0.0 (2026-01-19)

- 初始版本发布
- 实现基本PDF浏览功能
- 支持多种浏览模式
- 实现缩略图导航
- 实现区域选择和图形检测功能
- 采用MVC架构设计
- 支持线程安全操作
- 实现LRU缓存机制

## v0.1.0 (2026-01-16)

- 项目初始化
- 实现基本的PDF打开和浏览功能
- 实现单页和双页浏览模式
- 实现缩略图生成和显示

---

# 许可证

本项目采用MIT许可证，详见LICENSE文件。
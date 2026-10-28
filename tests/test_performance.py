#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF查看器性能测试套件 (精简版)

测试项目:
1. PDF文档加载性能
2. 页面渲染性能
3. 缩放操作性能
4. 内存使用分析
5. 综合压力测试
"""

import sys
import os
import multiprocessing

# Windows multiprocessing 必须在导入其他模块前调用 freeze_support()
multiprocessing.freeze_support()

# 关键：在导入任何Qt/项目模块之前设置离屏平台并创建QApplication
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication
# 创建 QApplication 实例（必须在使用任何 Qt 对象之前）
_app = QApplication.instance()
if _app is None:
    _app = QApplication(sys.argv)

import time
import tracemalloc
import statistics
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径 (兼容直接运行和 IDE 运行)
if '__file__' in dir():
    _script_dir = Path(__file__).resolve().parent.parent
else:
    _script_dir = Path(r'e:\script\pdfview_python')
sys.path.insert(0, str(_script_dir))


class PerformanceResult:
    """性能测试结果收集器"""

    def __init__(self):
        self.results = {}
        self.start_time = None

    def begin(self):
        self.start_time = time.perf_counter()

    def record(self, category: str, metric: str, value, unit: str = "", notes: str = ""):
        key = f"{category}.{metric}"
        self.results[key] = {
            "category": category,
            "metric": metric,
            "value": value,
            "unit": unit,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        }

    def record_timing(self, category: str, metric: str, elapsed: float, notes: str = ""):
        self.record(category, metric, round(elapsed * 1000, 2), "ms", notes)

    def get_elapsed(self) -> float:
        if self.start_time is None:
            return 0
        return time.perf_counter() - self.start_time

    def print_summary(self):
        print("\n" + "=" * 80)
        print("                    PDF查看器 - 性能测试报告")
        print("=" * 80)
        print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  总耗时:   {self.get_elapsed():.2f} 秒")
        print("=" * 80)

        current_category = None
        for key, data in self.results.items():
            if data["category"] != current_category:
                current_category = data["category"]
                print(f"\n--- {current_category} ---")

            value_str = f"{data['value']}"
            if data["unit"]:
                value_str += f" {data['unit']}"
            print(f"  {data['metric']}: {value_str}", end="")
            if data["notes"]:
                print(f"  ({data['notes']})", end="")
            print()

        print("\n" + "=" * 80)


results = PerformanceResult()


def run_multiple_times(func, times=5, *args, **kwargs):
    """多次执行函数，返回统计结果"""
    timings = []
    result = None
    for i in range(times):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        timings.append(elapsed)

    return {
        "result": result,
        "avg": statistics.mean(timings),
        "min": min(timings),
        "max": max(timings),
        "median": statistics.median(timings),
        "std_dev": statistics.stdev(timings) if len(timings) > 1 else 0,
        "all_timings": timings
    }


def measure_memory(func, *args, **kwargs):
    """测量函数执行的内存峰值"""
    tracemalloc.start()
    try:
        result = func(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        return result, peak
    finally:
        tracemalloc.stop()


def _render_single_page(doc, page_num: int, dpi: int = 96):
    """辅助函数：渲染单个页面"""
    import fitz
    import tempfile

    if page_num >= len(doc):
        return None

    page = doc.load_page(page_num)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    temp_path = temp_file.name
    temp_file.close()

    try:
        pix.save(temp_path)
        return temp_path, (pix.width, pix.height)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return None


# ============================================================
# 测试1: PDF处理器核心性能
# ============================================================

def test_pdf_processor_core(pdf_path: str):
    import fitz

    print("\n[1/5] 测试PDF处理器核心性能...")

    # 1.1 文档打开速度
    print("  1.1 文档打开速度...")
    open_stats = run_multiple_times(lambda p: fitz.open(p), 2, pdf_path)
    doc = open_stats["result"]
    page_count = len(doc)
    results.record_timing("PDF处理器", "文档打开-平均", open_stats["avg"])
    results.record("PDF处理器", "文档页数", page_count, "页", "")

    file_size = os.path.getsize(pdf_path)
    if file_size < 1024 * 1024:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size / (1024*1024):.2f} MB"
    results.record("PDF处理器", "文件大小", size_str, "", "")

    # 1.2 元数据获取
    print("  1.2 元数据获取...")
    meta_stats = run_multiple_times(lambda d: d.metadata, 2, doc)
    metadata = meta_stats["result"]
    results.record_timing("PDF处理器", "元数据获取-平均", meta_stats["avg"])

    # 1.3 单页渲染 @96DPI
    print("  1.3 单页渲染 @96DPI...")
    render_96 = run_multiple_times(lambda d: _render_single_page(d, 0, 96), 2, doc)
    results.record_timing("PDF处理器", "单页渲染@96DPI-平均", render_96["avg"])
    results.record_timing("PDF处理器", "单页渲染@96DPI-最快", render_96["min"])

    # 1.4 全文档渲染 @96DPI
    print(f"  1.4 全文档渲染 ({page_count}页)...")
    start = time.perf_counter()
    total_pixels = 0
    for i in range(page_count):
        r = _render_single_page(doc, i, 96)
        if r:
            _, (w, h) = r
            total_pixels += w * h
    full_elapsed = time.perf_counter() - start
    results.record_timing("PDF处理器", "全文档渲染@96DPI", full_elapsed)
    if page_count > 0 and full_elapsed > 0:
        per_page_ms = full_elapsed / page_count * 1000
        results.record("PDF处理器", "每页平均渲染", f"{per_page_ms:.1f}", "ms", "")
    results.record("PDF处理器", "总像素量", total_pixels // 1000000, "MP", "")

    # 1.5 文本提取
    print("  1.5 文本提取...")
    text_start = time.perf_counter()
    text = doc.load_page(0).get_text()
    text_elapsed = time.perf_counter() - text_start
    results.record_timing("PDF处理器", "首页文本提取", text_elapsed)
    results.record("PDF处理器", "首页文本长度", len(text), "字符", "")

    doc.close()
    print("  [完成] PDF处理器核心性能测试")


# ============================================================
# 测试2: PDFService 层性能
# ============================================================

def test_pdf_service_layer(pdf_path: str):
    from business.pdf_manager import PDFManager
    from business.page_renderer import PageRenderer
    from business.page_cache import PageCache
    from services.pdf_service import PDFService

    print("\n[2/5] 测试PDFService层性能...")

    pdf_manager = PDFManager()
    page_renderer = PageRenderer()
    page_cache = PageCache()
    pdf_service = PDFService(pdf_manager, page_cache)

    try:
        # 2.1 文档打开
        print("  2.1 文档打开...")
        open_stats = run_multiple_times(pdf_service.open_document, 2, pdf_path)
        success = open_stats["result"]
        results.record_timing("PDFService层", "文档打开-平均", open_stats["avg"])
        if not success:
            print("  [警告] 文档打开失败，跳过后续测试")
            return

        page_count = pdf_service.get_page_count()

        # 2.2 同步渲染 冷/热缓存
        print("  2.2 同步渲染 (冷缓存 vs 热缓存)...")
        cold_start = time.perf_counter()
        pdf_service.render_page(0, zoom_level=1.0)
        cold_elapsed = time.perf_counter() - cold_start
        results.record_timing("PDFService层", "同步渲染-冷缓存", cold_elapsed)

        hot_stats = run_multiple_times(pdf_service.render_page, 3, 0, 1.0)
        results.record_timing("PDFService层", "同步渲染-热缓存-平均", hot_stats["avg"])
        cache_speedup = cold_elapsed / hot_stats["avg"] if hot_stats["avg"] > 0 else 0
        results.record("PDFService层", "缓存加速比", f"{cache_speedup:.1f}x", "", "")

        # 2.3 多页渲染
        print("  2.3 多页渲染...")
        render_times = []
        for i in range(min(5, page_count)):
            s = time.perf_counter()
            pdf_service.render_page(i, 1.0)
            render_times.append(time.perf_counter() - s)
        avg_r = sum(render_times) / len(render_times) if render_times else 0
        results.record_timing("PDFService层", "多页渲染-平均每页", avg_r)

        # 2.4 不同缩放级别
        print("  2.4 不同缩放级别渲染...")
        for zl in [0.5, 1.0, 2.0]:
            s = time.perf_counter()
            pdf_service.render_page(0, zl)
            results.record_timing("PDFService层", f"缩放{zl}x渲染", time.perf_counter() - s)

        # 2.5 页面尺寸获取
        print("  2.5 页面尺寸获取...")
        size_stats = run_multiple_times(pdf_service.get_page_size, 3, 0, 1.0)
        results.record_timing("PDFService层", "页面尺寸获取-平均", size_stats["avg"])

        # 2.6 关闭文档
        print("  2.6 文档关闭...")
        close_stats = run_multiple_times(pdf_service.close_document, 2)
        results.record_timing("PDFService层", "文档关闭-平均", close_stats["avg"])

    finally:
        pdf_service.shutdown()

    print("  [完成] PDFService层性能测试")


# ============================================================
# 测试3: ZoomService 性能
# ============================================================

def test_zoom_service():
    from services.zoom_service import ZoomService
    from utils.constants import Constants

    print("\n[3/5] 测试ZoomService性能...")

    zoom_service = ZoomService()
    a4_size = (595, 842)
    viewport_size = (1024, 768)

    # 3.1 set_zoom_level (100次)
    print("  3.1 set_zoom_level (x100)...")
    z_stats = run_multiple_times(zoom_service.set_zoom_level, 100, 1.5)
    results.record_timing("缩放服务", "set_zoom_level x100", z_stats["avg"])
    results.record("缩放服务", "set_zoom_level QPS", int(100 / z_stats["avg"]), "ops/s", "")

    # 3.2 zoom_in (50次)
    print("  3.2 zoom_in (x50)...")
    zoom_service.reset_zoom()
    zi_stats = run_multiple_times(zoom_service.zoom_in, 50)
    results.record_timing("缩放服务", "zoom_in x50", zi_stats["avg"])

    # 3.3 zoom_out (50次)
    print("  3.3 zoom_out (x50)...")
    zoom_service.reset_zoom()
    zo_stats = run_multiple_times(zoom_service.zoom_out, 50)
    results.record_timing("缩放服务", "zoom_out x50", zo_stats["avg"])

    # 3.4 fit_page (50次)
    print("  3.4 fit_page (x50)...")
    fp_stats = run_multiple_times(zoom_service.fit_page, 50, a4_size, viewport_size)
    results.record_timing("缩放服务", "fit_page x50", fp_stats["avg"])
    results.record("缩放服务", "fit_page 结果值", f"{fp_stats['result']:.4f}", "", "")

    # 3.5 fit_width (50次)
    print("  3.5 fit_width (x50)...")
    fw_stats = run_multiple_times(zoom_service.fit_width, 50, a4_size[0], viewport_size[0])
    results.record_timing("缩放服务", "fit_width x50", fw_stats["avg"])

    # 3.6 缩放历史 undo/redo
    print("  3.6 缩放历史操作...")
    zoom_service.reset_zoom()
    for _ in range(20):
        zoom_service.zoom_in()
    undo_stats = run_multiple_times(zoom_service.zoom_undo, 10)
    redo_stats = run_multiple_times(zoom_service.zoom_redo, 10)
    results.record_timing("缩放服务", "zoom_undo x10", undo_stats["avg"])
    results.record_timing("缩放服务", "zoom_redo x10", redo_stats["avg"])

    print("  [完成] ZoomService性能测试")


# ============================================================
# 测试4: 内存使用分析
# ============================================================

def test_memory_usage(pdf_path: str):
    import fitz
    from PyQt6.QtGui import QPixmap
    import tempfile as _tf

    print("\n[4/5] 测试内存使用情况...")

    # 4.1 文档加载基础内存
    print("  4.1 文档加载内存占用...")
    _, peak_load = measure_memory(lambda: fitz.open(pdf_path))
    results.record("内存分析", "文档加载内存峰值", f"{peak_load / 1024:.1f}", "KB", "仅打开不渲染")

    # 4.2 单页渲染内存
    print("  4.2 单页渲染内存占用(96DPI)...")
    def render_single():
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        zoom = 96 / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        tf = _tf.NamedTemporaryFile(suffix='.png', delete=False)
        tp = tf.name; tf.close()
        pix.save(tp)
        pm = QPixmap(tp)
        os.remove(tp)
        doc.close()
        return pm

    _, peak_render = measure_memory(render_single)
    results.record("内存分析", "单页渲染(96DPI)内存峰值", f"{peak_render / 1024:.1f}", "KB", "含QPixmap")

    # 4.3 高分辨率渲染
    print("  4.3 高分辨率渲染内存占用(192DPI)...")
    def render_hi():
        nonlocal _hi_size_info
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        zoom = 192 / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        tf = _tf.NamedTemporaryFile(suffix='.png', delete=False)
        tp = tf.name; tf.close()
        pix.save(tp)
        pm = QPixmap(tp)
        _hi_size_info = pm.width() * pm.height() * 4 // 1024
        os.remove(tp)
        doc.close()
        return pm

    _hi_size_info = 0
    _, peak_hi = measure_memory(render_hi)
    results.record("内存分析", "高分辨率(192DPI)内存峰值", f"{peak_hi / 1024:.1f}", "KB", "含QPixmap")
    if _hi_size_info:
        results.record("内存分析", "高分辨率像素估算", f"{_hi_size_info / 1024:.1f}", "MB", "ARGB32")

    # 4.4 多页面缓存增长趋势
    print("  4.4 多页缓存内存增长(最多5页)...")
    doc = fitz.open(pdf_path)
    pc = min(len(doc), 5)
    mem_samples = []

    try:
        import psutil
        has_psutil = True
    except ImportError:
        has_psutil = False

    for i in range(pc):
        page = doc.load_page(i)
        zoom = 96 / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        tf = _tf.NamedTemporaryFile(suffix='.png', delete=False)
        tp = tf.name; tf.close()
        pix.save(tp)
        pm = QPixmap(tp)
        os.remove(tp)

        if has_psutil:
            proc = psutil.Process(os.getpid())
            mem_mb = proc.memory_info().rss / (1024 * 1024)
            mem_samples.append(mem_mb)

    doc.close()

    if len(mem_samples) >= 2:
        inc = mem_samples[-1] - mem_samples[0]
        per_page = inc / (len(mem_samples) - 1)
        results.record("内存分析", f"{pc}页缓存总内存", f"{mem_samples[-1]:.1f}", "MB", "RSS")
        results.record("内存分析", "每页平均增长", f"{per_page:.1f}", "MB/页", "")

    print("  [完成] 内存使用分析")


# ============================================================
# 测试5: 压力测试
# ============================================================

def test_stress_performance(pdf_path: str):
    from business.pdf_manager import PDFManager
    from business.page_renderer import PageRenderer
    from business.page_cache import PageCache
    from services.pdf_service import PDFService
    from services.zoom_service import ZoomService

    print("\n[5/5] 综合压力测试...")

    pdf_mgr = PDFManager()
    renderer = PageRenderer()
    cache = PageCache()
    pdf_svc = PDFService(pdf_mgr, renderer, cache)
    zoom_svc = ZoomService()

    try:
        pdf_svc.open_document(pdf_path)
        page_count = pdf_svc.get_page_count()

        # 5.1 快速翻页 (2轮)
        print(f"  5.1 快速翻页 ({page_count}页 x 2轮)...")
        flip_s = time.perf_counter()
        for _ in range(2):
            for i in range(page_count):
                pdf_svc.render_page(i, 1.0)
        flip_e = time.perf_counter() - flip_s
        total_r = page_count * 2
        results.record_timing("压力测试", f"快速翻页({total_r}次)", flip_e)
        results.record("压力测试", "翻页吞吐量", f"{total_r / flip_e:.1f}", "renders/s", "")

        # 5.2 连续缩放
        print("  5.2 连续缩放 (30次放大+30次缩小)...")
        zs = time.perf_counter()
        zoom_svc.reset_zoom()
        for _ in range(30): zoom_svc.zoom_in()
        for _ in range(30): zoom_svc.zoom_out()
        ze = time.perf_counter() - zs
        results.record_timing("压力测试", "连续缩放(60次)", ze)
        results.record("压力测试", "缩放QPS", int(60 / ze), "ops/s", "")

        # 5.3 混合场景
        print("  5.3 混合场景 (翻页+缩放交替)...")
        ms = time.perf_counter()
        zoom_svc.reset_zoom()
        ops = 0
        for _ in range(2):
            for i in range(min(3, page_count)):
                pdf_svc.render_page(i, zoom_svc.get_zoom_level()); ops += 1
            zoom_svc.zoom_in(); ops += 1
            for i in range(min(3, page_count)):
                pdf_svc.render_page(i, zoom_svc.get_zoom_level()); ops += 1
            zoom_svc.zoom_out(); ops += 1
        me = time.perf_counter() - ms
        results.record_timing("压力测试", f"混合场景({ops}次)", me)
        results.record("压力测试", "混合QPS", int(ops / me), "ops/s", "")

        pdf_svc.close_document()

    finally:
        pdf_svc.shutdown()

    print("  [完成] 综合压力测试")


# ============================================================
# 主入口
# ============================================================

def main():
    multiprocessing.freeze_support()  # Windows 必须调用
    global results
    results = PerformanceResult()
    results.begin()

    default_pdf = _script_dir / "PDF for test" / "CPA-VES-Type-AV-catalogue.pdf"
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else str(default_pdf)

    if not os.path.exists(pdf_path):
        print(f"错误: PDF文件不存在: {pdf_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"   PDF查看器性能测试套件 (精简版)")
    print(f"   测试文件: {os.path.basename(pdf_path)}")
    print(f"   文件路径: {pdf_path}")
    print(f"{'='*60}")

    import platform
    print(f"\n系统信息:")
    print(f"  OS:     {platform.system()} {platform.release()}")
    print(f"  Python: {platform.python_version()}")
    print(f"  CPU:    {os.cpu_count()} 核心")
    try:
        import psutil
        mem = psutil.virtual_memory()
        print(f"  内存:   {mem.total / (1024**3):.1f} GB (可用: {mem.available / (1024**3):.1f} GB)")
    except ImportError:
        pass
    try:
        import fitz
        print(f"  PyMuPDF: {fitz.version}")
    except ImportError:
        print("  PyMuPDF: 未安装")
    try:
        from PyQt6.QtCore import PYQT_VERSION_STR
        print(f"  PyQt6:   {PYQT_VERSION_STR}")
    except ImportError:
        print("  PyQt6:   未安装")

    try:
        test_pdf_processor_core(pdf_path)
        test_pdf_service_layer(pdf_path)
        test_zoom_service()
        test_memory_usage(pdf_path)
        test_stress_performance(pdf_path)
    except Exception as e:
        print(f"\n!!! 测试异常中断: {e}")
        import traceback
        traceback.print_exc()

    results.print_summary()

    report_path = _script_dir / "tests" / "performance_test_report.md"
    save_report(results, report_path)
    print(f"\n详细报告已保存至: {report_path}")


def save_report(rc: PerformanceResult, output_path: Path):
    lines = [
        "# PDF查看器性能测试报告",
        "",
        f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> **总耗时**: {rc.get_elapsed():.2f} 秒",
        "",
        "## 测试结果汇总",
        "",
        "| 类别 | 指标 | 数值 | 单位 | 备注 |",
        "|------|------|------|------|------|",
    ]
    for key, data in rc.results.items():
        val = f"{data['value']}"
        if data["unit"]: val += f" {data['unit']}"
        note = data["notes"].replace("|", "\\|") if data["notes"] else ""
        lines.append(f"| {data['category']} | {data['metric']} | {val} | {data['unit']} | {note} |")

    lines.extend([
        "",
        "## 结论",
        "",
        "- 以上为当前环境基准测试结果",
        "- 实际性能因硬件/PDF复杂度/系统负载而异",
        "- 建议定期运行以监控性能回归",
        ""
    ])
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    main()

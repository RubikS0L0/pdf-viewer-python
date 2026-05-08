"""逐步定位性能测试崩溃点"""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys
sys.path.insert(0, '.')
import time

PDF_PATH = r'PDF for test\CPA-VES-Type-AV-catalogue.pdf'

print("=== Step 1: import fitz ===")
import fitz
doc = fitz.open(PDF_PATH)
print(f"  OK, {len(doc)} pages")
doc.close()

print("\n=== Step 2: import business modules ===")
from business.pdf_manager import PDFManager
from business.page_renderer import PageRenderer
from business.page_cache import PageCache
print("  OK")

print("\n=== Step 3: import pdf_service ===")
from services.pdf_service import PDFService
print("  OK")

print("\n=== Step 4: open document ===")
pm = PDFManager()
pr = PageRenderer()
pc = PageCache()
ps = PDFService(pm, pr, pc)
ok = ps.open_document(PDF_PATH)
print(f"  open result: {ok}, pages: {ps.get_page_count()}")

print("\n=== Step 5: render page ===")
t0 = time.perf_counter()
r = ps.render_page(0, zoom_level=1.0)
t1 = time.perf_counter() - t0
print(f"  render result: {type(r).__name__}, time: {t1*1000:.1f}ms")

print("\n=== Step 6: import PyQt6 QPixmap ===")
from PyQt6.QtGui import QPixmap
print("  QPixmap imported")

print("\n=== Step 7: render to pixmap (96DPI) ===")
doc2 = fitz.open(PDF_PATH)
page = doc2.load_page(0)
zoom = 96/72.0
matrix = fitz.Matrix(zoom, zoom)
pix = page.get_pixmap(matrix=matrix, alpha=False)

import tempfile as _tf
tf = _tf.NamedTemporaryFile(suffix='.png', delete=False)
tp = tf.name; tf.close()
pix.save(tp)
print(f"  saved temp png: {tp}")

pm2 = QPixmap(tp)
print(f"  QPixmap loaded: {pm2.width()}x{pm2.height()}")
os.remove(tp)
doc2.close()

print("\n=== Step 8: zoom service ===")
from services.zoom_service import ZoomService
zs = ZoomService()
for i in range(10):
    zs.zoom_in()
print(f"  zoom after 10x in: {zs.get_zoom_level()}")
for i in range(10):
    zs.zoom_out()
print(f"  zoom after undo: {zs.get_zoom_level()}")

ps.close_document()
ps.shutdown()

print("\n=== ALL STEPS PASSED ===")

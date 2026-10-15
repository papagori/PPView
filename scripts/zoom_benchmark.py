"""Repeatable synthetic PDF preview benchmark (baseline v0.2.2 vs current path).

Run: python scripts/zoom_benchmark.py --output dist/zoom-benchmark.json
Fixtures are generated locally; timings are diagnostic, not a real Illustrator claim.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import random
import statistics
import tempfile
import time
import zlib
from pathlib import Path

import pypdfium2 as pdfium
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from ppview.core.document import _PDFIUM_LOCK, inspect_file, render_page_result
from ppview.ui.window import MainWindow


def fixture(path: Path, complexity: int) -> None:
    commands = [b"0.1 0.3 0.8 rg"]
    for i in range(complexity):
        x, y = (i * 37) % 550, (i * 71) % 740
        commands.append(f"{x} {y} m {x+25} {y+17} l {x+10} {y+35} l h f".encode())
    stream = b"\n".join(commands)
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> /Contents 4 0 R >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    out = bytearray(b"%PDF-1.4\n"); offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out)); out.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(out); out.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: out.extend(f"{offset:010} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(out)


def raster_fixture(path: Path) -> None:
    width, height = 3000, 3200
    pixels = random.Random(1042).randbytes(width * height * 3)
    compressed = zlib.compress(pixels, 1)
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /XObject << /Im 5 0 R >> >> /Contents 4 0 R >>",
               b"<< /Length 29 >>\nstream\nq 612 0 0 792 0 0 cm /Im Do Q\nendstream",
               b"<< /Type /XObject /Subtype /Image /Width 3000 /Height 3200 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length " + str(len(compressed)).encode() + b" >>\nstream\n" + compressed + b"\nendstream"]
    out = bytearray(b"%PDF-1.4\n"); offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out)); out.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(out); out.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: out.extend(f"{offset:010} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(out)


def baseline_v022(path: Path, scale: float):
    data = path.read_bytes()
    with _PDFIUM_LOCK:
        document = pdfium.PdfDocument(data)
        try:
            page = document[0]
            bitmap = page.render(scale=scale, rotation=0, rev_byteorder=True)
            raw = ctypes.string_at(bitmap.buffer, bitmap.stride * bitmap.height)
            image = QImage(raw, bitmap.width, bitmap.height, bitmap.stride, QImage.Format.Format_RGB888).copy()
            bitmap.close(); page.close()
            return image
        finally:
            document.close()


def median_ms(fn, repetitions=7):
    values = []
    for _ in range(repetitions):
        start = time.perf_counter(); fn(); values.append((time.perf_counter() - start) * 1000)
    return round(statistics.median(values), 2)


def working_set_mb():
    if hasattr(ctypes, "windll"):
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        c = Counters(); c.cb = ctypes.sizeof(c)
        ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        get_info.restype = wintypes.BOOL
        if not get_info(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            return None, None
        return round(c.WorkingSetSize / 1048576, 1), round(c.PeakWorkingSetSize / 1048576, 1)
    return None, None


def run(output: Path | None):
    app = QApplication.instance() or QApplication([])
    records = {}
    with tempfile.TemporaryDirectory(prefix="ppview-zoom-bench-") as temp:
        for label, complexity in (("small", 1), ("complex", 12000)):
            path = Path(temp) / f"{label}.pdf"; fixture(path, complexity)
            scale = 1.7
            base = median_ms(lambda: baseline_v022(path, scale))
            # Warm the bounded byte cache before reporting its steady render latency.
            render_page_result(path, 0, scale)
            current = median_ms(lambda: render_page_result(path, 0, scale))
            baseline_open = median_ms(lambda: (inspect_file(path), baseline_v022(path, scale)))
            current_open = median_ms(lambda: (inspect_file(path), render_page_result(path, 0, scale)))
            info = inspect_file(path)
            window = MainWindow(); window.info = info; window.path = path.resolve(); window.preview.show()
            window._debounce_ms = 150; window._zoom_timer.setInterval(150)
            event_latency = []
            for _ in range(12):
                start = time.perf_counter(); window._zoom_at(120, 200, 160)
                event_latency.append((time.perf_counter() - start) * 1000)
            start = time.perf_counter(); deadline = time.monotonic() + 20
            while time.monotonic() < deadline and window._render_completed < 1:
                app.processEvents(); time.sleep(0.003)
            app.processEvents()
            zoom_result = {"events": len(event_latency), "pdfium_renders_started": window._pdfium_render_started,
                           "renders_eliminated_vs_v0.2.2": 12 - window._pdfium_render_started,
                           "median_input_handler_ms": round(statistics.median(event_latency), 3),
                           "last_input_to_final_render_ms": round((time.perf_counter()-start)*1000, 2),
                           "completed": window._render_completed > 0}
            window.clear_all(); window.pool.waitForDone(5000); window.close(); app.processEvents()
            records[label] = {"bytes": path.stat().st_size, "baseline_v0.2.2_render_ms": base,
                              "current_cached_render_ms": current,
                              "baseline_initial_inspect_plus_render_ms": baseline_open,
                              "current_initial_inspect_plus_render_ms": current_open,
                              "rapid_zoom": zoom_result}
        path = Path(temp) / "large-raster.pdf"; raster_fixture(path)
        base = median_ms(lambda: baseline_v022(path, 0.7), repetitions=5)
        render_page_result(path, 0, 0.7)
        current = median_ms(lambda: render_page_result(path, 0, 0.7), repetitions=5)
        baseline_open = median_ms(lambda: (inspect_file(path), baseline_v022(path, 0.7)), repetitions=5)
        current_open = median_ms(lambda: (inspect_file(path), render_page_result(path, 0, 0.7)), repetitions=5)
        records["large_raster"] = {"bytes": path.stat().st_size,
                                    "baseline_v0.2.2_render_ms": base,
                                    "current_cached_render_ms": current,
                                    "baseline_initial_inspect_plus_render_ms": baseline_open,
                                    "current_initial_inspect_plus_render_ms": current_open,
                                    "render_pixel_limit": 16_000_000}
        memory = working_set_mb()
        report = {"fixture": "synthetic PDF; locally generated; not a genuine Illustrator file",
                  "repetitions": 7, "statistic": "median", "zoom_event_sequence": 12,
                  "v0.2.2_pdfium_renders_for_event_sequence": 12,
                  "working_set_mb": memory[0], "peak_working_set_mb": memory[1],
                  "measurements": records}
        if output:
            output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    app.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path)
    run(parser.parse_args().output)

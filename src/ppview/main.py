from __future__ import annotations

import ctypes
import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from ppview.i18n.strings import initial_language, strings
from ppview.ui.splash import StartupSplash


def _write_startup_diagnostics(started: float, phases: dict[str, float], status: str = "ready") -> None:
    """Write opt-in timings/markers for reproducible packaging smoke tests."""
    timing_path = os.environ.get("PPVIEW_STARTUP_TIMING_FILE")
    if timing_path:
        payload = {"status": status, **{key: round((value - started) * 1000, 1) for key, value in phases.items()}}
        Path(timing_path).write_text(json.dumps(payload), encoding="utf-8")
    marker = os.environ.get("PPVIEW_SMOKE_SPLASH_READY") if "splash_visible" in phases else None
    if marker:
        Path(marker).write_text("visible", encoding="ascii")
    marker = os.environ.get("PPVIEW_SMOKE_WINDOW_READY") if "window_shown" in phases else None
    if marker:
        Path(marker).write_text("ready", encoding="ascii")


def _construct_main_window(splash, factory, initial_file):
    """Ensure a failed window initialization cannot leave the splash visible."""
    try:
        return factory(initial_file)
    except Exception:
        splash.close()
        raise


def main():
    started = time.perf_counter()
    phases: dict[str, float] = {}
    app = QApplication(sys.argv)
    phases["qt_application_created"] = time.perf_counter()
    app.setOrganizationName("papagori")
    app.setApplicationName("PPView")
    language = initial_language()
    t = strings(language)
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("papagori.PPView")
    resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    app.setWindowIcon(QIcon(str(resource_root / "assets" / "logo" / "ppview.ico")))

    splash = StartupSplash(language)
    phases["splash_constructed"] = time.perf_counter()
    splash.show()
    phases["splash_show_called"] = time.perf_counter()
    app.processEvents()
    phases["splash_visible"] = time.perf_counter()
    _write_startup_diagnostics(started, phases, "starting")
    splash.complete_branding()
    phases["splash_branding_ready"] = time.perf_counter()
    splash_capture = os.environ.get("PPVIEW_SMOKE_SPLASH_CAPTURE")
    if splash_capture and not splash.grab().save(splash_capture):
        splash.close()
        raise RuntimeError(f"Could not capture startup splash at {splash_capture}")

    try:
        from ppview.ui.window import MainWindow
        phases["main_window_import_done"] = time.perf_counter()
        window = _construct_main_window(splash, MainWindow, sys.argv[1] if len(sys.argv) > 1 else None)
        phases["main_window_constructed"] = time.perf_counter()
        window.show()
        phases["window_show_called"] = time.perf_counter()
        splash.finish(window)
        phases["window_shown"] = time.perf_counter()
        _write_startup_diagnostics(started, phases)
    except Exception as exc:
        splash.close()
        _write_startup_diagnostics(started, phases, "failed")
        QMessageBox.critical(None, t["app"], t["startup_failed"].format(error=str(exc)))
        return 1

    menu_capture = os.environ.get("PPVIEW_SMOKE_MENU_CAPTURE")
    window_capture = os.environ.get("PPVIEW_SMOKE_WINDOW_CAPTURE")
    preflight_capture = os.environ.get("PPVIEW_SMOKE_PREFLIGHT_CAPTURE")
    image_capture = os.environ.get("PPVIEW_SMOKE_IMAGE_CAPTURE")
    if preflight_capture:
        highlight_capture_scheduled = False

        def save_preflight_report():
            nonlocal highlight_capture_scheduled
            active_key = window._canonical(window.path) if window.path else None
            matches = [(settings, report) for (key, settings), report in window.preflight_reports.items()
                       if key == active_key]
            if matches:
                settings, report = matches[-1]
                ppview = __import__("ppview")
                payload = {"version": ppview.__version__, "display_version": ppview.__display_version__,
                           "page_count": report.page_count, "image_count": report.image_count,
                           "image_placement_count": report.image_placement_count,
                           "font_count": report.font_count,
                           "results": [{"check_id": result.check_id, "category": result.category,
                                        "status": result.status.value, "message_id": result.message_id}
                                       for result in report.results]}
                Path(preflight_capture).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                if image_capture and not highlight_capture_scheduled:
                    image_group = window.check_tree.topLevelItem(1)
                    for index in range(image_group.childCount() if image_group else 0):
                        item = image_group.child(index)
                        result = item.data(0, Qt.ItemDataRole.UserRole)
                        if getattr(result, "check_id", "").startswith("image.placement."):
                            window._activate_check_item(item, 0)
                            highlight_capture_scheduled = True

                            def save_image_highlight():
                                if not window.grab().save(image_capture):
                                    raise RuntimeError(f"Could not capture image placement highlight at {image_capture}")

                            QTimer.singleShot(1100, save_image_highlight)
                            break
                return
            QTimer.singleShot(200, save_preflight_report)

        QTimer.singleShot(300, save_preflight_report)
    if window_capture:
        def capture_window():
            if not window.grab().save(window_capture):
                raise RuntimeError(f"Could not capture the packaged window at {window_capture}")
        QTimer.singleShot(2500, capture_window)
    if menu_capture and window_capture:
        def show_and_capture_menu():
            anchor = window.file_menu_button.mapToGlobal(QPoint(0, window.file_menu_button.height()))
            window.file_menu.popup(anchor)
            QTimer.singleShot(450, capture_menu)

        def capture_menu():
            menu = window.file_menu
            if not menu.isVisible():
                anchor = window.file_menu_button.mapToGlobal(QPoint(0, window.file_menu_button.height()))
                window.file_menu.popup(anchor)
            pixmap = menu.grab()
            if not pixmap.save(menu_capture):
                raise RuntimeError(f"Could not capture the French File menu at {menu_capture}")
            origin = menu.mapToGlobal(QPoint(0, 0))
            client_origin = window.mapToGlobal(QPoint(0, 0))
            metadata = {"x": round((origin.x() - client_origin.x()) * window.devicePixelRatioF()),
                        "y": round((origin.y() - client_origin.y()) * window.devicePixelRatioF()),
                        "device_pixel_ratio": window.devicePixelRatioF()}
            Path(menu_capture).with_suffix(".json").write_text(json.dumps(metadata), encoding="utf-8")

        QTimer.singleShot(3000, show_and_capture_menu)
        QTimer.singleShot(10000, window.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

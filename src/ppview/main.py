import sys
import ctypes
import json
import os
from pathlib import Path
from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication
from ppview.ui.window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("papagori"); app.setApplicationName("PPView")
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("papagori.PPView")
    app.setWindowIcon(MainWindow._app_icon())
    window = MainWindow(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    menu_capture = os.environ.get("PPVIEW_SMOKE_MENU_CAPTURE")
    window_capture = os.environ.get("PPVIEW_SMOKE_WINDOW_CAPTURE")
    preflight_capture = os.environ.get("PPVIEW_SMOKE_PREFLIGHT_CAPTURE")
    if preflight_capture:
        def save_preflight_report():
            active_key = window._canonical(window.path) if window.path else None
            matches = [(settings, report) for (key, settings), report in window.preflight_reports.items()
                       if key == active_key]
            if matches:
                settings, report = matches[-1]
                payload = {"version": __import__("ppview").__version__,
                           "page_count": report.page_count, "image_count": report.image_count,
                           "font_count": report.font_count,
                           "results": [{"check_id": result.check_id, "category": result.category,
                                        "status": result.status.value, "message_id": result.message_id}
                                       for result in report.results]}
                Path(preflight_capture).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
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

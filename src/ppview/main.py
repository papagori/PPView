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
    if menu_capture and window_capture:
        def show_and_capture_menu():
            if not window.grab().save(window_capture):
                raise RuntimeError(f"Could not capture the packaged window at {window_capture}")
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

        QTimer.singleShot(2500, show_and_capture_menu)
        QTimer.singleShot(10000, window.close)
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())

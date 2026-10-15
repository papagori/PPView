"""Capture localized activity UI while synthetic long-running work is held active."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from ppview import __display_version__  # noqa: E402
from ppview.ui.window import MainWindow  # noqa: E402
from conftest import make_pdf  # noqa: E402


def wait_until(app, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def main():
    app = QApplication.instance() or QApplication([])
    # The offscreen Qt plugin on some Windows hosts starts without enumerating
    # system fonts. Load the host UI fonts for legible, faithful QA screenshots.
    for font_path in (Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
                      Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "YuGothR.ttc"):
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    if "Segoe UI" in QFontDatabase.families():
        app.setFont(QFont("Segoe UI", 9))
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ppview-activity-visual-") as folder:
        pdf = Path(folder) / "activity-visual.pdf"
        pdf.write_bytes(make_pdf())
        for language in ("en", "ja", "fr"):
            window = MainWindow()
            window.language = language
            from ppview.i18n.strings import strings
            window.t = strings(language)
            window._translate()
            window.resize(1360, 820)
            window.open_file(str(pdf))
            window.show()
            if not wait_until(app, lambda: window.info is not None and window._render_completed > 0):
                raise RuntimeError(f"Could not prepare PDF preview for {language} activity capture")
            if not wait_until(app, lambda: not window._render_busy and not window._zoom_timer.isActive()):
                raise RuntimeError(f"PDFium render did not settle for {language} activity capture")
            time.sleep(0.35)
            app.processEvents()

            token = f"visual-{language}"
            window.open_activity.begin(token, window.t["activity_opening"])
            window.render_activity.begin(token, window.t["activity_rendering"])
            window.preflight_activity.begin(token, window.t["activity_analyzing"])
            # Hold three synthetic tasks for 1.2 seconds to verify delayed visibility.
            if not wait_until(app, lambda: all(not item.widget.isHidden() for item in
                    (window.open_activity, window.render_activity, window.preflight_activity)), timeout=2):
                raise RuntimeError(f"Activity labels did not appear after their delay in {language}")
            hold_deadline = time.monotonic() + 0.95
            while time.monotonic() < hold_deadline:
                app.processEvents()
                time.sleep(0.02)
            app.processEvents()
            target = output / f"PPView-v{__display_version__}-activity-{language}.png"
            if not window.grab().save(str(target)):
                raise RuntimeError(f"Could not save activity screenshot: {target}")
            for activity in (window.open_activity, window.render_activity, window.preflight_activity):
                activity.finish(token)
            window.clear_all()
            window.close()
            window.pool.waitForDone(5000)
            app.processEvents()
            print(f"Localized activity screenshot ({language}): {target}")


if __name__ == "__main__":
    main()

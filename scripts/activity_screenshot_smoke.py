"""Capture localized activity UI while worker operations are deliberately delayed."""
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
from ppview.ui import window as window_module  # noqa: E402
from ppview.ui.window import MainWindow  # noqa: E402
from ppview.validation import PreflightSettings  # noqa: E402
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
    original_functions = (window_module.inspect_file, window_module.render_page_result,
                          window_module.run_preflight)

    def delayed(function):
        def run(*args, **kwargs):
            time.sleep(1.2)
            return function(*args, **kwargs)
        return run

    with tempfile.TemporaryDirectory(prefix="ppview-activity-visual-") as folder:
        pdf = Path(folder) / "activity-visual.pdf"
        pdf.write_bytes(make_pdf())
        for language in ("en", "ja", "fr"):
            window_module.inspect_file = delayed(original_functions[0])
            window_module.render_page_result = original_functions[1]
            window_module.run_preflight = original_functions[2]
            window = MainWindow()
            try:
                window.language = language
                from ppview.i18n.strings import strings
                window.t = strings(language)
                window._translate()
                window.resize(1360, 820)
                window.open_file(str(pdf))
                window.show()
                if not wait_until(app, lambda: not window.open_activity.widget.isHidden()):
                    raise RuntimeError(f"Opening indicator did not appear for {language}")
                opening = output / f"PPView-v{__display_version__}-activity-opening-{language}.png"
                if not window.grab().save(str(opening)):
                    raise RuntimeError(f"Could not save opening screenshot: {opening}")

                if not wait_until(app, lambda: window.info is not None and window._render_completed > 0
                                  and (window._canonical(window.path), window._preflight_settings)
                                  in window.preflight_reports, timeout=20):
                    raise RuntimeError(f"Normal preview/preflight did not complete for {language}")

                # Trigger a second render and settings-specific preflight while
                # keeping the already visible page preview in place.
                window_module.render_page_result = delayed(original_functions[1])
                window_module.run_preflight = delayed(original_functions[2])
                window._render()
                target_ppi = 200 if window._preflight_settings.target_image_ppi != 200 else 300
                window._preflight_settings = PreflightSettings(target_ppi, window._preflight_settings.minimum_bleed_mm)
                window._validate_selected()
                if not wait_until(app, lambda: not window.render_activity.widget.isHidden()
                                  and not window.preflight_activity.widget.isHidden()):
                    raise RuntimeError(f"Rendering and analysis indicators did not appear for {language}")
                working = output / f"PPView-v{__display_version__}-activity-render-analysis-{language}.png"
                if not window.grab().save(str(working)):
                    raise RuntimeError(f"Could not save render/analysis screenshot: {working}")

                if not wait_until(app, lambda: window.info is not None and not window._render_busy
                                  and window.preflight_activity.token is None, timeout=20):
                    raise RuntimeError(f"Delayed worker tasks did not finish for {language}")
                print(f"Localized delayed-operation screenshots ({language}): {opening}, {working}")
            finally:
                window_module.inspect_file, window_module.render_page_result, window_module.run_preflight = original_functions
                window.clear_all()
                window.close()
                window.pool.waitForDone(5000)
                app.processEvents()


if __name__ == "__main__":
    main()

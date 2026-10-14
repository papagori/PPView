"""Open a two-page PDF through the real Qt window and verify visible page images."""
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from conftest import make_pdf  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from ppview.ui.window import MainWindow  # noqa: E402

def has_blue_content(pixmap):
    image = pixmap.toImage()
    return any(
        (lambda color: color.blue() > 180 and color.red() < 40 and color.green() < 40)(image.pixelColor(x, y))
        for y in range(image.height()) for x in range(image.width())
    )

app = QApplication([])
with tempfile.TemporaryDirectory(prefix="ppview-ui-") as folder:
    pdf = Path(folder) / "two-pages.pdf"
    pdf.write_bytes(make_pdf(2))
    window = MainWindow(str(pdf))
    window.show()
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        app.processEvents()
        pixmap = window.preview.pixmap()
        if window.info and pixmap and not pixmap.isNull():
            break
        time.sleep(0.02)
    else:
        raise RuntimeError("The first page did not render in the UI")
    if not has_blue_content(pixmap):
        raise RuntimeError("The first page image did not contain the fixture's blue vector shape")
    first_size = (pixmap.width(), pixmap.height())
    window.change_page(1)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        app.processEvents()
        pixmap = window.preview.pixmap()
        if window.page == 1 and pixmap and not pixmap.isNull():
            break
        time.sleep(0.02)
    else:
        raise RuntimeError("The second page did not render in the UI")
    if not has_blue_content(pixmap):
        raise RuntimeError("The second page image did not contain the fixture's blue vector shape")
    print(f"Qt UI rendered page 1 {first_size[0]}x{first_size[1]} and page 2 {pixmap.width()}x{pixmap.height()}")
    window.close()
    window.pool.waitForDone(5000)

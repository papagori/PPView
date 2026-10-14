"""Exercise import, page rendering, cleanup, and clean process shutdown."""
from pathlib import Path
import gc
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from conftest import make_pdf  # noqa: E402
from ppview.core.document import inspect_file, render_page  # noqa: E402

with tempfile.TemporaryDirectory(prefix="ppview-pdfium-") as folder:
    pdf = Path(folder) / "smoke.pdf"
    pdf.write_bytes(make_pdf(2))
    for _ in range(25):
        info = inspect_file(pdf)
        assert len(info.pages) == 2
        for index in range(2):
            image = render_page(pdf, index, 0.5)
            assert image.width() > 0 and image.height() > 0
            image = None
        info = None
        gc.collect()

print("PDFium import, 50 page renders, document cleanup, and process exit passed")

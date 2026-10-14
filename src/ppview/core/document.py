"""Safe PDFium-backed access to PDF content in PDF and .ai files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import ctypes

import pypdfium2 as pdfium

_PDFIUM_LOCK = threading.RLock()


class DocumentError(Exception):
    """A user-displayable document error."""


@dataclass(frozen=True)
class PageInfo:
    width_pt: float
    height_pt: float

    @property
    def width_mm(self) -> float:
        return self.width_pt * 25.4 / 72

    @property
    def height_mm(self) -> float:
        return self.height_pt * 25.4 / 72


@dataclass(frozen=True)
class DocumentInfo:
    path: Path
    kind: str
    size: int
    pages: tuple[PageInfo, ...]


def _open(data: bytes):
    """Open from immutable bytes; callers must hold _PDFIUM_LOCK."""
    if not data:
        raise DocumentError("empty")
    try:
        return pdfium.PdfDocument(data)
    except Exception as exc:
        raise DocumentError("invalid") from exc


def inspect_file(path: str | Path) -> DocumentInfo:
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise DocumentError("unreadable") from exc
    with _PDFIUM_LOCK:
        document = _open(data)
        try:
            count = len(document)
            if count < 1:
                raise DocumentError("no_pages")
            pages = []
            for index in range(count):
                page = document[index]
                width, height = page.get_size()
                page.close()
                if width <= 0 or height <= 0:
                    raise DocumentError("dimensions")
                pages.append(PageInfo(float(width), float(height)))
            kind = "ai" if path.suffix.lower() == ".ai" else "pdf"
            return DocumentInfo(path, kind, len(data), tuple(pages))
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("invalid") from exc
        finally:
            document.close()


def render_page(path: str | Path, index: int, scale: float):
    """Render a page to a detached QImage, serializing PDFium operations."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise DocumentError("unreadable") from exc
    with _PDFIUM_LOCK:
        document = _open(data)
        try:
            if index < 0 or index >= len(document):
                raise DocumentError("invalid")
            from PySide6.QtGui import QImage
            page = document[index]
            bitmap = page.render(scale=max(0.1, min(scale, 8.0)), rotation=0, rev_byteorder=True)
            # PDFium returns packed RGB bytes. Copy into Qt-owned storage before
            # releasing its bitmap; this avoids an optional Pillow dependency.
            raw = ctypes.string_at(bitmap.buffer, bitmap.stride * bitmap.height)
            image = QImage(raw, bitmap.width, bitmap.height, bitmap.stride,
                           QImage.Format.Format_RGB888).copy()
            bitmap.close()
            page.close()
            return image
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("render") from exc
        finally:
            document.close()


def validate_rendering(path: str | Path, page_count: int) -> None:
    """Verify that every page can render at a modest diagnostic resolution."""
    for index in range(page_count):
        render_page(path, index, 0.25)

"""Safe PDFium-backed access to PDF content in PDF and .ai files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import ctypes
from collections import OrderedDict

import pypdfium2 as pdfium

_PDFIUM_LOCK = threading.RLock()
_BYTES_LOCK = threading.RLock()
_BYTE_CACHE: OrderedDict[str, tuple[int, int, int, bytes]] = OrderedDict()
_BYTE_CACHE_LIMIT = 96 * 1024 * 1024
_BYTE_CACHE_SIZE = 0
MAX_RENDER_PIXELS = 16_000_000
MAX_RENDER_DIMENSION = 16_384


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


@dataclass(frozen=True)
class RenderResult:
    image: object
    requested_scale: float
    actual_scale: float
    limited: bool


def _read_cached(path: Path) -> bytes:
    """Read a stable snapshot, retaining only a bounded amount of document data."""
    global _BYTE_CACHE_SIZE
    try:
        stat = path.stat()
        key = str(path.resolve()).casefold()
        stamp = (stat.st_mtime_ns, stat.st_size, stat.st_ctime_ns)
        with _BYTES_LOCK:
            item = _BYTE_CACHE.get(key)
            if item and item[:3] == stamp:
                _BYTE_CACHE.move_to_end(key)
                return item[3]
            if item:
                _BYTE_CACHE_SIZE -= len(item[3])
                del _BYTE_CACHE[key]
        data = path.read_bytes()
        # A second stat avoids caching a file that changed while it was read.
        after = path.stat()
        if (after.st_mtime_ns, after.st_size, after.st_ctime_ns) == stamp and len(data) <= _BYTE_CACHE_LIMIT:
            with _BYTES_LOCK:
                existing = _BYTE_CACHE.get(key)
                if existing and existing[:3] == stamp:
                    _BYTE_CACHE.move_to_end(key)
                    return existing[3]
                if existing:
                    _BYTE_CACHE_SIZE -= len(existing[3])
                    del _BYTE_CACHE[key]
                while _BYTE_CACHE and _BYTE_CACHE_SIZE + len(data) > _BYTE_CACHE_LIMIT:
                    _, old = _BYTE_CACHE.popitem(last=False)
                    _BYTE_CACHE_SIZE -= len(old[3])
                _BYTE_CACHE[key] = (stamp[0], stamp[1], stamp[2], data)
                _BYTE_CACHE_SIZE += len(data)
        return data
    except OSError as exc:
        raise DocumentError("unreadable") from exc


def release_document(path: str | Path) -> None:
    """Drop cached source bytes when the last UI document reference is closed."""
    global _BYTE_CACHE_SIZE
    key = str(Path(path).resolve()).casefold()
    with _BYTES_LOCK:
        item = _BYTE_CACHE.pop(key, None)
        if item:
            _BYTE_CACHE_SIZE -= len(item[3])


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
    data = _read_cached(path)
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


def render_page_result(path: str | Path, index: int, scale: float) -> RenderResult:
    """Render a detached QImage, bounding allocations before entering PDFium."""
    data = _read_cached(Path(path))
    requested = max(0.1, min(float(scale), 8.0))
    with _PDFIUM_LOCK:
        document = _open(data)
        try:
            if index < 0 or index >= len(document):
                raise DocumentError("invalid")
            from PySide6.QtGui import QImage
            page = document[index]
            bitmap = None
            try:
                width_pt, height_pt = page.get_size()
                actual = requested
                estimated_width = max(1, round(width_pt * actual))
                estimated_height = max(1, round(height_pt * actual))
                ratio = min(1.0, (MAX_RENDER_PIXELS / (estimated_width * estimated_height)) ** 0.5,
                            MAX_RENDER_DIMENSION / estimated_width, MAX_RENDER_DIMENSION / estimated_height)
                actual *= ratio
                bitmap = page.render(scale=actual, rotation=0, rev_byteorder=True)
                # PDFium returns packed RGB bytes. Copy into Qt-owned storage before
                # releasing its bitmap; this avoids an optional Pillow dependency.
                raw = ctypes.string_at(bitmap.buffer, bitmap.stride * bitmap.height)
                image = QImage(raw, bitmap.width, bitmap.height, bitmap.stride,
                               QImage.Format.Format_RGB888).copy()
                return RenderResult(image, requested, actual, ratio < 0.999999)
            finally:
                if bitmap is not None:
                    bitmap.close()
                page.close()
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("render") from exc
        finally:
            document.close()


def render_page(path: str | Path, index: int, scale: float):
    """Compatibility API returning the rendered QImage."""
    return render_page_result(path, index, scale).image


def validate_rendering(path: str | Path, page_count: int) -> None:
    """Verify that every page can render at a modest diagnostic resolution."""
    for index in range(page_count):
        render_page(path, index, 0.25)

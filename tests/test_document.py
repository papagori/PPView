from ppview.core import document
from ppview.core.document import DocumentError, inspect_file, render_page, render_page_result, validate_rendering
from conftest import make_pdf
import pytest

def test_valid_pdf_and_render(pdf_file):
    info = inspect_file(pdf_file)
    assert info.kind == "pdf" and len(info.pages) == 1
    image = render_page(pdf_file, 0, 1)
    assert image.width() > 0 and image.height() > 0
    color = image.pixelColor(100, 150)
    assert color.blue() > 200 and color.red() < 30
    validate_rendering(pdf_file, 1)

def test_pdf_content_with_ai_extension(tmp_path):
    path = tmp_path / "compat.ai"; path.write_bytes(make_pdf())
    info = inspect_file(path)
    assert info.kind == "ai" and len(info.pages) == 1

@pytest.mark.parametrize("content", [b"not an Illustrator file", b"%PDF-1.7\n%%EOF\n", b""])
def test_unsupported_or_corrupt_file(tmp_path, content):
    path = tmp_path / "bad.ai"; path.write_bytes(content)
    with pytest.raises(DocumentError): inspect_file(path)

def test_corrupted_pdf_and_empty_pdf(tmp_path):
    for name, data in (("corrupt.pdf", b"%PDF gibberish"), ("empty.pdf", b"")):
        path = tmp_path / name; path.write_bytes(data)
        with pytest.raises(DocumentError): inspect_file(path)

def test_multipage_and_dimensions(multi_pdf):
    info = inspect_file(multi_pdf)
    assert len(info.pages) == 3
    assert info.pages[0].width_mm == pytest.approx(215.9)
    assert info.pages[0].height_mm == pytest.approx(279.4)
    assert info.pages[1].width_mm > info.pages[0].width_mm

def test_pdf_content_detected_regardless_of_pdf_extension(tmp_path):
    path = tmp_path / "renamed.bin"; path.write_bytes(make_pdf())
    assert len(inspect_file(path).pages) == 1

def test_bad_page_index_is_handled(pdf_file):
    with pytest.raises(DocumentError): render_page(pdf_file, 99, 1)


def test_document_byte_cache_reuses_snapshot_and_invalidates_changed_file(pdf_file, monkeypatch):
    first = document._read_cached(pdf_file)
    assert document._read_cached(pdf_file) is first
    pdf_file.write_bytes(make_pdf(2))
    second = document._read_cached(pdf_file)
    assert second != first
    document.release_document(pdf_file)
    assert str(pdf_file.resolve()).casefold() not in document._BYTE_CACHE


def test_render_result_reports_safe_resolution_fallback(pdf_file, monkeypatch):
    monkeypatch.setattr(document, "MAX_RENDER_PIXELS", 100_000)
    result = render_page_result(pdf_file, 0, 4.0)
    assert result.limited
    assert result.actual_scale < result.requested_scale
    assert result.image.width() * result.image.height() <= document.MAX_RENDER_PIXELS * 1.01

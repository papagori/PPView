import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QSignalSpy, QTest

from ppview.core.document import inspect_file
from ppview.ui.window import MainWindow, PreviewLabel
from conftest import make_pdf


@pytest.fixture
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


@pytest.fixture
def window(app):
    result = MainWindow()
    yield result
    result.clear_all()
    result.close()
    app.processEvents()


def test_fit_page_and_width_are_bounded_and_use_viewport(window, pdf_file):
    window.show()
    window.info = inspect_file(pdf_file)
    window.path = pdf_file.resolve()
    window._render()
    page_fit = window._fit_zoom("page")
    width_fit = window._fit_zoom("width")
    assert 0.05 <= page_fit <= 8
    assert width_fit >= page_fit
    window.resize(1450, 900)
    QApplication.processEvents()
    assert window._fit_zoom("page") >= page_fit


def test_zoom_limits(window):
    window.zoom = 7.9
    window.set_view("zoom_in")
    assert window.zoom == 8
    window.zoom = 0.051
    window.set_view("zoom_out")
    assert window.zoom == 0.05


def test_multiple_file_drop_deduplicates_and_selects_last(window, tmp_path):
    paths = []
    for name in ("one.pdf", "two.ai"):
        path = tmp_path / name
        path.write_bytes(make_pdf())
        paths.append(str(path))
    window._drop_files(paths + [paths[0]])
    assert len(window.documents) == 2
    assert window.path == (tmp_path / "two.ai").resolve()
    assert window.document_combo.count() == 2


def test_switch_close_and_clear_isolate_document_state(window, pdf_file, tmp_path):
    second = tmp_path / "second.pdf"
    second.write_bytes(make_pdf(2))
    first_info, second_info = inspect_file(pdf_file), inspect_file(second)
    first_key, second_key = window._canonical(pdf_file), window._canonical(second)
    window.documents = {first_key: first_info, second_key: second_info}
    window._refresh_document_combo()
    window._select_path(first_key)
    assert window.info.path == first_info.path and len(window.info.pages) == 1
    window._select_path(second_key)
    assert window.info.path == second_info.path and len(window.info.pages) == 2
    window.close_selected_document()
    assert len(window.documents) == 1
    assert window.info.path == first_info.path
    window.clear_all()
    assert not window.documents and window.info is None and window.path is None
    assert window.document_combo.count() == 0


def test_document_list_switches_from_selector(window, pdf_file, tmp_path):
    second = tmp_path / "second.pdf"
    second.write_bytes(make_pdf(2))
    window.documents = {window._canonical(pdf_file): inspect_file(pdf_file),
                        window._canonical(second): inspect_file(second)}
    window._refresh_document_combo()
    window.document_combo.setCurrentIndex(1)
    assert window.info.path == second.resolve()


@pytest.mark.parametrize("button", [Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton])
def test_preview_drag_emits_pan_delta(app, button):
    preview = PreviewLabel()
    preview.resize(160, 120)
    preview.show()
    spy = QSignalSpy(preview.pan)
    QTest.mousePress(preview, button, pos=preview.rect().center())
    end = preview.rect().center() + QPoint(18, 9)
    QTest.mouseMove(preview, end)
    QTest.mouseRelease(preview, button, pos=end)
    assert spy.count() >= 1


def test_ctrl_wheel_zoom_updates_scale(window, pdf_file):
    window.info = inspect_file(pdf_file)
    window.path = pdf_file.resolve()
    window.zoom = 1.0
    window.fit_mode = "manual"
    window._zoom_at(120, 60, 60)
    assert window.zoom == pytest.approx(1.2)

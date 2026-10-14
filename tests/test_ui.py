import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QWheelEvent
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


def test_drop_on_preview_adds_multiple_files_and_preserves_collection(window, tmp_path):
    paths = []
    for filename in ("existing.pdf", "新しい資料.ai"):
        path = tmp_path / filename
        path.write_bytes(make_pdf())
        paths.append(path)
    first = window._canonical(paths[0])
    window._drop_files([str(paths[0])])
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(paths[1])), QUrl.fromLocalFile(str(paths[1]))])
    enter = QDragEnterEvent(QPoint(20, 20), Qt.DropAction.CopyAction, mime,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(window.preview, enter)
    assert enter.isAccepted()
    drop = QDropEvent(QPoint(20, 20), Qt.DropAction.CopyAction, mime,
                      Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(window.preview, drop)
    assert drop.isAccepted()
    assert len(window.documents) == 2
    assert window._canonical(paths[0]) == first
    assert window.path == paths[1].resolve()
    assert window.document_combo.count() == 2


def test_unsupported_drop_shows_feedback_without_clearing_documents(window, pdf_file, tmp_path):
    window.open_files([str(pdf_file)])
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("not a preview document", encoding="utf-8")
    window._drop_files([str(unsupported)])
    assert len(window.documents) == 1
    assert window.statusBar().currentMessage()


def test_file_browser_navigation_restores_unicode_directory(window, tmp_path):
    folder = tmp_path / "印刷資料"
    folder.mkdir()
    (folder / "写真.pdf").write_bytes(make_pdf())
    assert window.browse_directory(folder)
    assert Path(window.file_model.filePath(window.file_tree.currentIndex())) == folder
    assert window.settings.value("last_browsed_directory") == str(folder.resolve())
    window.show()
    window.browser_action.setChecked(True)
    assert window.file_browser.isVisible()
    window.browser_action.setChecked(False)


def test_browser_opens_selected_unicode_file(window, tmp_path):
    path = tmp_path / "表紙.pdf"
    path.write_bytes(make_pdf())
    index = window.file_model.index(str(path))
    window._browser_double_click(index)
    assert window._canonical(path) in window.documents
    assert window.path == path.resolve()


def test_browser_opens_multiple_selected_files(window, tmp_path):
    paths = [tmp_path / "a.pdf", tmp_path / "b.ai"]
    for path in paths: path.write_bytes(make_pdf())
    indexes = [window.file_model.index(str(path)) for path in paths]
    for index in indexes:
        window.file_tree.selectionModel().select(
            index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    window.open_selected_from_browser()
    assert len(window.documents) == 2
    assert window.path == paths[-1].resolve()


def test_sidebar_changes_preview_viewport_and_footer_links(monkeypatch, window):
    from ppview.ui.window import QDesktopServices
    window.show()
    QApplication.processEvents()
    before = window.scroll.viewport().width()
    window.browser_action.setChecked(True)
    QApplication.processEvents()
    after = window.scroll.viewport().width()
    assert window.file_browser.isVisible()
    assert after < before
    assert window.copyright_prefix.text() == "© 2026"
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
    QTest.mouseClick(window.author_link, Qt.MouseButton.LeftButton)
    QTest.mouseClick(window.github_link, Qt.MouseButton.LeftButton)
    QTest.mouseClick(window.license_link, Qt.MouseButton.LeftButton)
    assert opened == ["https://www.matthieutuffet.com/", "https://github.com/papagori/PPView",
                      "https://github.com/papagori/PPView/blob/main/LICENSE"]


def test_browser_opens_at_useful_width_and_remembers_width(window):
    window.show()
    window.browser_action.setChecked(True)
    QApplication.processEvents()
    assert window.file_browser.width() >= 220
    sizes = window.splitter.sizes()
    sizes[0] = 340
    window.splitter.setSizes(sizes)
    window._splitter_moved(window.splitter.sizes()[0], 1)
    QApplication.processEvents()
    remembered = int(window.settings.value("browser_width"))
    assert remembered >= 220
    window.browser_action.setChecked(False)
    assert not window.file_browser.isVisible()
    window.browser_action.setChecked(True)
    QApplication.processEvents()
    assert window.file_browser.width() >= 220
    assert abs(window.file_browser.width() - min(remembered, window.width() - 520)) < 8


def test_drive_root_model_starts_collapsed_and_scrolls(window):
    window.show()
    QApplication.processEvents()
    assert not window.file_tree.rootIndex().isValid()
    assert window.file_tree.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert window.file_tree.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


def test_zoom_control_manual_entry_slider_and_clamping(window):
    requested = []
    window.zoom_control.zoom_requested.connect(requested.append)
    window.zoom_control.edit.setText("175%")
    window.zoom_control._commit()
    assert requested[-1] == pytest.approx(1.75)
    window._set_zoom_factor(1.75)
    assert window.zoom_control.edit.text() == "175%"
    assert window.zoom_control.slider.value() == 175
    window._set_zoom_factor(20)
    assert window.zoom == 8
    assert window.zoom_control.edit.text() == "800%"
    window.zoom_control.set_zoom(1.0)
    wheel = QWheelEvent(QPointF(10, 10), QPointF(window.zoom_control.edit.mapToGlobal(QPoint(10, 10))),
                        QPoint(0, 120), QPoint(0, 120), Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(window.zoom_control.edit, wheel)
    assert requested[-1] == pytest.approx(1.1)


def test_language_switching_translates_and_persists(window):
    window.lang_combo.setCurrentIndex(2)
    assert window.language == "fr"
    assert window.file_menu.title() == "Fichier"
    assert window.browser_heading.text() == "Explorateur de fichiers"
    assert window.settings.value("language") == "fr"
    window.lang_combo.setCurrentIndex(1)
    assert window.file_menu.title() == "ファイル"
    window.lang_combo.setCurrentIndex(0)
    assert window.file_menu.title() == "File"


def test_preview_wheel_zoom_and_other_controls_keep_wheel_behavior(window, pdf_file):
    window.info = inspect_file(pdf_file)
    window.path = pdf_file.resolve()
    window.zoom = 1.0
    window.fit_mode = "manual"
    wheel = QWheelEvent(QPointF(40, 40), QPointF(window.preview.mapToGlobal(QPoint(40, 40))),
                        QPoint(0, 120), QPoint(0, 120), Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(window.preview, wheel)
    assert window.zoom == pytest.approx(1.2)
    window.zoom = 1.0
    window.fit_mode = "manual"
    wheel = QWheelEvent(QPointF(10, 10), QPointF(window.document_combo.mapToGlobal(QPoint(10, 10))),
                        QPoint(0, 120), QPoint(0, 120), Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(window.document_combo, wheel)
    assert window.zoom == pytest.approx(1.0)
    # Only the preview handles wheel events as zoom gestures.
    assert not hasattr(window.document_combo, "zoom_at")


def test_toolbar_groups_language_is_last_and_branding_present(window):
    actions = window.toolbar.actions()
    widgets = [window.toolbar.widgetForAction(action) for action in actions]
    assert widgets[-1] is window.lang_combo
    assert window.brand_name.text() == "PPView"
    assert window.brand_slogan.text()
    window.show()
    QApplication.processEvents()
    assert window.brand_header.isVisible()
    assert window.footer.isVisible()
    assert window.footer.geometry().width() > 500


def test_all_languages_have_complete_translation_keys():
    from ppview.i18n.strings import strings
    english = strings("en")
    assert strings("ja").keys() == english.keys()
    assert strings("fr").keys() == english.keys()

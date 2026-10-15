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
    window.fit_mode = "manual"
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


def test_preview_image_highlight_scales_with_the_rendered_page(app):
    preview = PreviewLabel()
    preview.resize(200, 100)
    preview.set_image_highlight((0.1, 0.2, 0.4, 0.6), "Approximate")
    assert preview.image_highlight_rect() == pytest.approx((20, 20, 80, 60))
    preview.resize(400, 200)
    assert preview.image_highlight_rect() == pytest.approx((40, 40, 160, 120))
    preview.set_image_highlight()
    assert preview.image_highlight_rect() is None


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


def test_toolbar_zoom_in_starts_from_current_fit_value(window, monkeypatch):
    monkeypatch.setattr(window, "_fit_zoom", lambda mode=None: 2.0)
    monkeypatch.setattr(window._zoom_timer, "start", lambda interval=None: None)
    window.fit_mode = "page"; window.zoom = 1.0
    window.set_view("zoom_in")
    assert window.zoom == pytest.approx(2.4)
    assert window.fit_mode == "manual"


def test_language_switching_translates_and_persists(window):
    window.lang_combo.setCurrentIndex(2)
    assert window.language == "fr"
    assert window.file_menu.title() == "Fichier"
    assert window.browser_heading.text() == "Navigateur"
    assert window.settings.value("language") == "fr"
    window.lang_combo.setCurrentIndex(1)
    assert window.file_menu.title() == "ファイル"
    window.lang_combo.setCurrentIndex(0)
    assert window.file_menu.title() == "File"


def test_browser_labels_native_shortcut_and_menus_all_languages(window):
    from PySide6.QtGui import QKeySequence
    expected = (("en", "Browser", "File", "Help"),
                ("ja", "ブラウザー", "ファイル", "ヘルプ"),
                ("fr", "Navigateur", "Fichier", "Aide"))
    for language, browser, file_label, help_label in expected:
        window.language = language
        window.t = __import__("ppview.i18n.strings", fromlist=["strings"]).strings(language)
        window._translate()
        assert window.browser_action.text() == browser
        assert window.browser_action.toolTip()
        assert window.file_menu_button.text() == file_label
        assert window.help_menu_button.text() == help_label
        assert window.open_action.text() == window.t["open"]
        assert window.open_action.shortcut() == QKeySequence(QKeySequence.StandardKey.Open)
        assert "Ctrl+O" not in window.open_action.text()
        assert window.file_menu.actions()[0] is window.open_action
        assert window.about_action in window.help_menu.actions()
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(window.file_menu.font())
        label = metrics.horizontalAdvance(window.open_action.text())
        shortcut = metrics.horizontalAdvance(window.open_action.shortcut().toString())
        assert window.file_menu.sizeHint().width() >= label + shortcut + 40
    window.show(); window.preview.show(); QApplication.processEvents()
    assert window.file_menu_button.menu() is window.file_menu
    window.file_menu.popup(window.file_menu_button.mapToGlobal(window.file_menu_button.rect().bottomLeft())); QApplication.processEvents()
    assert window.file_menu.isVisible()
    window.file_menu.close()
    assert window.help_menu_button.menu() is window.help_menu
    window.help_menu.popup(window.help_menu_button.mapToGlobal(window.help_menu_button.rect().bottomLeft())); QApplication.processEvents()
    assert window.help_menu.isVisible()
    window.help_menu.close()


def test_toolbar_order_and_right_controls(window):
    from PySide6.QtWidgets import QToolButton
    window.resize(1920, 900)
    window.show()
    QApplication.processEvents()
    menus = [window.palette_a_layout.itemAt(i).widget() for i in range(window.palette_a_layout.count())]
    menu_buttons = [w for w in menus if isinstance(w, QToolButton)]
    assert menu_buttons[0] is window.file_menu_button
    assert menu_buttons[1].defaultAction() is window.browser_action
    assert menu_buttons[2].defaultAction() is window.panel_action
    assert menu_buttons[3] is window.help_menu_button
    preview = [window.preview_toolbar_layout.itemAt(i).widget() for i in range(window.preview_toolbar_layout.count())]
    documents = [window.document_toolbar_layout.itemAt(i).widget() for i in range(window.document_toolbar_layout.count())]
    assert preview.index(window.zoom_control) < preview.index(window.prev) < preview.index(window.page_label) < preview.index(window.next)
    assert documents[0].defaultAction() is window.close_document_action
    assert documents[1].defaultAction() is window.clear_action
    assert documents[2] is window.document_combo
    assert window.palette_a.property("paletteName") == "menus"
    assert window.palette_b.property("paletteName") == "preview"
    assert window.palette_c.property("paletteName") == "documents"
    assert window.language_palette.property("paletteName") == "language"
    assert window.group_toolbar_layout.indexOf(window.palette_a) < window.group_toolbar_layout.indexOf(window.palette_b) < window.group_toolbar_layout.indexOf(window.palette_c)
    outer_widgets = [window.toolbar_layout.itemAt(i).widget() for i in range(window.toolbar_layout.count())]
    assert outer_widgets == [window.groups_scroll, window.language_palette]
    right = window.language_palette.mapTo(window.toolbar_contents, window.language_palette.rect().bottomRight()).x()
    assert right == window.toolbar_contents.contentsRect().right()
    assert window.groups_scroll.horizontalScrollBar().maximum() == 0
    assert window.file_menu_button.height() > 0
    assert window.brand_header.geometry().left() == window.menuWidget().contentsRect().left()
    assert window.brand_name.mapTo(window.brand_header, window.brand_name.rect().topLeft()).x() < 100


def test_toolbar_overflow_keeps_help_and_language_available(window):
    window.resize(1920, 900)
    window.show(); QApplication.processEvents()
    assert window.groups_scroll.horizontalScrollBar().maximum() == 0
    window.resize(780, 600); QApplication.processEvents()
    assert window.groups_scroll.horizontalScrollBar().maximum() > 0
    assert window.help_menu_button.isVisible() and window.lang_combo.isVisible()
    assert window.language_palette.mapTo(window.toolbar_contents, window.language_palette.rect().bottomRight()).x() == window.toolbar_contents.contentsRect().right()


def test_app_icon_has_multiple_sizes_and_runtime_icon(window):
    from pathlib import Path
    import struct
    icon_path = Path(__file__).resolve().parents[1] / "assets" / "logo" / "ppview.ico"
    data = icon_path.read_bytes()
    assert data[:6] == b"\x00\x00\x01\x00\x07\x00"
    dimensions = {(w or 256, h or 256) for w, h in
                  (struct.unpack_from("<BB", data, 6 + index * 16) for index in range(7))}
    assert dimensions == {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}
    assert (Path(__file__).resolve().parents[1] / "assets" / "logo" / "ppview-icon.svg").is_file()
    assert window.windowIcon().isNull() is False


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
    assert window.toolbar_layout.itemAt(window.toolbar_layout.count() - 1).widget() is window.language_palette
    assert window.brand_name.text() == "PPView"
    assert window.brand_slogan.text()
    window.show()
    QApplication.processEvents()
    assert window.brand_header.isVisible()
    assert window.footer.isVisible()
    assert window.footer.geometry().width() > 500
    assert not window.statusBar().isSizeGripEnabled()
    assert "qlineargradient" in window.styleSheet()
    assert window.author_link.isFlat()
    assert window.github_link.isFlat()
    assert window.license_link.isFlat()
    from ppview import __version__
    assert window.version_label.text() == f"PPView v{__version__}"


def test_application_version_and_about_diagnostics_are_dynamic(window, monkeypatch):
    from ppview import __version__
    from ppview.ui.help_dialogs import AboutDialog
    from ppview.build_info import build_commit
    opened = []
    monkeypatch.setattr(AboutDialog, "exec", lambda dialog: opened.append(dialog) or 0)
    window.about()
    assert window.version_label.text() == f"PPView v{__version__}"
    dialog = opened[0]
    labels = [item.text() for item in dialog.findChildren(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel)]
    assert any(f"Version: {__version__}" in label for label in labels)
    assert any("Build commit:" in label for label in labels)
    assert any("independent of Adobe" in label for label in labels)
    dialog.close()


def test_zoom_immediate_feedback_and_debounce_coalesces_latest_request(window, pdf_file, monkeypatch):
    from PySide6.QtGui import QPixmap
    window.info = inspect_file(pdf_file); window.path = pdf_file.resolve()
    window._final_pixmap = QPixmap(800, 1000); window._final_zoom = 1.0
    starts = []
    monkeypatch.setattr(window._zoom_timer, "start", lambda interval=None: starts.append(interval))
    window._set_zoom_factor(1.5)
    window._set_zoom_factor(2.0)
    assert window.zoom == 2.0
    assert window.zoom_control.edit.text() == "200%"
    assert window.preview.pixmap().width() == 1600
    assert starts == [150, 150]
    assert window._zoom_timer.interval() == 150


def test_zoom_anchor_is_preserved_for_scaled_preview(window, pdf_file):
    from PySide6.QtGui import QPixmap
    window.info = inspect_file(pdf_file); window.path = pdf_file.resolve()
    window.show(); window.preview.show(); QApplication.processEvents()
    window._final_pixmap = QPixmap(800, 1000); window._final_zoom = 1.0
    window._scale_preview_immediately(1.0, 2.0, 500, 400, 120, 80)
    assert window.preview.pixmap().width() == 1600
    assert window.scroll.horizontalScrollBar().maximum() > 0
    assert window.scroll.verticalScrollBar().maximum() > 0
    assert window.scroll.horizontalScrollBar().value() == min(880, window.scroll.horizontalScrollBar().maximum())
    assert window.scroll.verticalScrollBar().value() == min(720, window.scroll.verticalScrollBar().maximum())


def test_temporary_preview_bitmap_is_bounded_at_extreme_zoom(window):
    from PySide6.QtGui import QPixmap
    from ppview.core.document import MAX_RENDER_PIXELS
    window.show(); window.preview.show(); QApplication.processEvents()
    window._final_pixmap = QPixmap(800, 1000); window._final_zoom = 1.0
    window._scale_preview_immediately(1.0, 8.0, 0, 0, 0, 0)
    pixmap = window.preview.pixmap()
    assert pixmap.width() * pixmap.height() <= MAX_RENDER_PIXELS + 20_000
    assert window.preview.width() >= pixmap.width()


def test_limited_pdfium_render_is_never_shown_as_passed(window):
    from PySide6.QtGui import QImage
    from ppview.core.document import RenderResult
    info = type("Info", (), {"path": Path("bounded.pdf"), "pages": (object(),)})()
    window.info = info; window.path = info.path; window.page = 0
    window.token = 4; window.render_serial = 9
    limited = RenderResult(QImage(40, 40, QImage.Format.Format_RGB888), 4.0, 1.0, True)
    window._image_ready(4, (9, 0, 1.0, 4.0, limited))
    window._validation_display("passed")
    assert window.t["render_limited"] in window.details["render"].text()
    assert window.t["render_limited"] in window.preview.toolTip()


def test_zoom_pending_result_waits_for_debounce_and_document_switch_cancels_timer(window, pdf_file, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(window, "_render", lambda: calls.append(window.path))
    first_info = inspect_file(pdf_file)
    second = tmp_path / "second.pdf"; second.write_bytes(make_pdf(2)); second_info = inspect_file(second)
    first_key, second_key = window._canonical(pdf_file), window._canonical(second)
    window.documents.update({first_key: first_info, second_key: second_info})
    window.document_paths.update({first_key: pdf_file.resolve(), second_key: second.resolve()})
    window._validate_selected = lambda: None
    window._select_path(first_key)
    calls.clear(); window._render_busy = True; window._render_pending = True
    window._zoom_timer.start(1000)
    window._render_finished(window.token)
    assert calls == []  # pending latest state remains behind the active debounce
    window._select_path(second_key)
    assert not window._zoom_timer.isActive()
    assert window.path == second.resolve()
    assert calls == [second.resolve()]


def test_closing_document_while_rendering_cannot_restart_stale_work(window):
    calls = []
    window._render_pending = True; window._render_busy = True
    window.clear_all()
    window._render = lambda: calls.append(True)
    window._render_finished(window.token)
    assert calls == []
    assert window.info is None


def test_help_menu_and_about_guide_translate_all_languages(window):
    from ppview.ui.help_dialogs import GUIDE, AboutDialog, UserGuideDialog, URLS
    from ppview.i18n.strings import strings
    from PySide6.QtWidgets import QLabel, QDialogButtonBox
    from ppview.build_info import build_commit
    from ppview import __version__
    assert set(GUIDE) == {"en", "ja", "fr"}
    expected = {"en": "Opening documents", "ja": "ドキュメントを開く", "fr": "Ouvrir des documents"}
    for language in ("en", "ja", "fr"):
        window.language = language; window.t = strings(language); window._translate()
        assert window.guide_action.text() == window.t["guide"]
        guide = UserGuideDialog(window, language)
        content = " ".join(label.text() for label in guide.findChildren(QLabel))
        assert expected[language] in content
        close_text = {"en": "Close", "ja": "閉じる", "fr": "Fermer"}[language]
        assert guide.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Close).text() == close_text
        about = AboutDialog(window, language, build_commit(), Path("assets/logo/ppview.ico"))
        about_content = " ".join(label.text() for label in about.findChildren(QLabel))
        assert f"{__version__}" in about_content and "Matthieu Tuffet" in about_content
        assert "Adobe" in about_content
        for _label, url in URLS:
            assert url in about_content
        about.close()
        guide.close()


def test_all_languages_have_complete_translation_keys():
    from ppview.i18n.strings import strings
    english = strings("en")
    assert strings("ja").keys() == english.keys()
    assert strings("fr").keys() == english.keys()


def test_preflight_results_render_by_category_and_retranslate_without_reanalysis(window, multi_pdf):
    from ppview.validation import CheckResult, PreflightReport, Status
    from ppview.i18n.strings import strings
    report = PreflightReport((
        CheckResult("document.pages", "document", Status.PASSED, "document.page_count",
                    measurements={"count": 3}),
        CheckResult("image.low", "images", Status.WARNING, "image.resolution_low", page=2,
                    measurements={"effective_ppi": 120, "width_px": 100, "height_px": 100,
                                  "target_ppi": 300}, severity="high"),
        CheckResult("font.missing", "fonts", Status.WARNING, "fonts.not_embedded", page=1,
                    measurements={"name": "TestFont", "subtype": "Type0"}),
        CheckResult("bleed.unknown", "geometry", Status.UNKNOWN, "geometry.bleed_boxes_missing", page=1),
        CheckResult("color.rgb", "colors", Status.PASSED, "colors.detected",
                    measurements={"color_space": "DeviceRGB"}),
    ), page_count=3, image_count=1, font_count=1)
    window.info = inspect_file(multi_pdf); window.path = multi_pdf.resolve()
    window._preflight_display(report)
    assert window.check_tree.topLevelItemCount() == 5
    assert "1" in window.check_tree.topLevelItem(1).text(0)
    warning = window.check_tree.topLevelItem(1).child(0)
    assert "120 PPI" in warning.text(0)
    assert warning.foreground(0).color().name() == "#ffad66"
    before = window.check_tree.topLevelItem(1).child(0).text(0)
    window.language = "ja"; window.t = strings("ja"); window._preflight_display(report)
    assert window.check_tree.topLevelItem(1).text(0).startswith("画像")
    assert window.check_tree.topLevelItem(1).child(0).text(0) != before


def test_stale_preflight_result_after_close_and_reopen_is_ignored(window, pdf_file):
    from ppview.validation import PreflightReport, PreflightSettings, CheckResult, Status
    key = window._canonical(pdf_file); info = inspect_file(pdf_file)
    window.documents[key] = info; window.document_paths[key] = pdf_file.resolve()
    window.document_generations[key] = 3; window.path = pdf_file.resolve(); window.info = info
    report = PreflightReport((CheckResult("document.test", "document", Status.PASSED,
                                          "document.page_count", measurements={"count": 1}),), 1, 0, 0)
    settings = PreflightSettings()
    window._preflight_done_for(key, 2, settings, report)
    assert (key, settings) not in window.preflight_reports
    window._preflight_done_for(key, 3, settings, report)
    assert window.preflight_reports[(key, settings)] is report


def test_preflight_issue_selects_its_page_without_modifying_pdf(window, multi_pdf, monkeypatch):
    from PySide6.QtWidgets import QTreeWidgetItem
    from ppview.validation import CheckResult, Status
    info = inspect_file(multi_pdf); window.info = info; window.path = multi_pdf.resolve()
    rendered = []; monkeypatch.setattr(window, "_render", lambda: rendered.append(window.page))
    result = CheckResult("image.issue", "images", Status.WARNING, "image.resolution_low", page=3,
                         bounding_box_pt=(10, 20, 30, 40),
                         details={"preview_box": (0.1, 0.2, 0.3, 0.4)})
    item = QTreeWidgetItem(); item.setData(0, Qt.ItemDataRole.UserRole, result)
    original = multi_pdf.read_bytes()
    window._activate_check_item(item, 0)
    assert window.page == 2 and rendered == [2]
    assert window.preview._image_highlight == (0.1, 0.2, 0.3, 0.4)
    window.change_page(-1)
    assert window.preview._image_highlight is None
    assert multi_pdf.read_bytes() == original


def test_image_placements_are_grouped_and_retranslated_without_reanalysis(window, multi_pdf):
    from ppview.validation import CheckResult, PreflightReport, Status
    from ppview.i18n.strings import strings

    parent_id = "image.placement.2.1"
    result = CheckResult(
        parent_id, "images", Status.PASSED, "image.resolution_meets", page=2,
        object_ref="18 0 R", measurements={
            "placement_index": 1, "width_px": 600, "height_px": 600,
            "ppi_x": 300, "ppi_y": 300, "effective_ppi": 300,
            "placement_width_mm": 50.8, "placement_height_mm": 50.8,
            "target_ppi": 300,
        }, details={"placement_index": 1, "reuse_status": "reused", "reuse_count": 2,
                    "preview_box": (0.1, 0.2, 0.4, 0.6),
                    "preview_quality": "approximate"})
    children = (
        CheckResult("image.presence.2.1", "images", Status.PASSED, "image.present", page=2,
                    details={"parent_id": parent_id, "preview_box": (0.1, 0.2, 0.4, 0.6)}),
        CheckResult("image.data.2.1", "images", Status.PASSED, "image.data_available", page=2,
                    details={"parent_id": parent_id, "preview_box": (0.1, 0.2, 0.4, 0.6)}),
        CheckResult("image.decode.2.1", "images", Status.PASSED, "image.decode_success", page=2,
                    details={"parent_id": parent_id, "preview_box": (0.1, 0.2, 0.4, 0.6)}),
    )
    report = PreflightReport((result, *children), 3, 1, 0, 1)
    window.info = inspect_file(multi_pdf); window.path = multi_pdf.resolve()
    window._preflight_display(report)
    placement = window.check_tree.topLevelItem(1).child(0)
    assert placement.text(0).startswith("Image #1 — Page 2")
    assert placement.childCount() == 4  # details plus presence, data, and decode
    window._activate_check_item(placement, 0)
    assert window.page == 1
    assert window.preview._image_highlight == (0.1, 0.2, 0.4, 0.6)
    window.language = "ja"; window.t = strings("ja")
    window._preflight_display(report)
    assert "画像 #1" in window.check_tree.topLevelItem(1).child(0).text(0)

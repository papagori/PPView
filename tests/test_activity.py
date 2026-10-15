import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from ppview.i18n.strings import strings
from ppview.ui.activity import DelayedActivity
from ppview.ui.window import MainWindow


@pytest.fixture
def app():
    instance = QApplication.instance() or QApplication([])
    return instance


@pytest.fixture
def window(app):
    result = MainWindow()
    yield result
    result.clear_all()
    result.close()
    app.processEvents()


def test_activity_is_delayed_and_finishes_only_for_its_current_task(app):
    parent = QWidget()
    activity = DelayedActivity(parent, delay_ms=60_000)
    activity.begin("old", "Opening document…")
    assert activity.widget.isHidden()

    activity.begin("new", "Rendering page…")
    activity._timer.timeout.emit()  # deterministically model the delayed timeout
    assert not activity.widget.isHidden()
    assert activity.label.text() == "Rendering page…"
    assert activity.finish("old") is False
    assert not activity.widget.isHidden()
    assert activity.finish("new") is True
    assert activity.widget.isHidden()
    parent.deleteLater()


def test_activity_messages_are_translated():
    expected = {
        "en": ("Opening document…", "Rendering page…", "Analyzing document…"),
        "ja": ("ドキュメントを開いています…", "ページを描画しています…", "ドキュメントを解析しています…"),
        "fr": ("Ouverture du document…", "Rendu de la page…", "Analyse du document…"),
    }
    for language, messages in expected.items():
        t = strings(language)
        assert (t["activity_opening"], t["activity_rendering"], t["activity_analyzing"]) == messages


def test_main_window_keeps_render_and_preflight_indicators_independent(window):
    window.render_activity.begin(12, window.t["activity_rendering"])
    window.preflight_activity.begin(("file.pdf", 1, object()), window.t["activity_analyzing"])
    window.render_activity._timer.timeout.emit()
    window.preflight_activity._timer.timeout.emit()
    assert not window.render_activity.widget.isHidden()
    assert not window.preflight_activity.widget.isHidden()
    window.render_activity.finish(12)
    assert window.render_activity.widget.isHidden()
    assert not window.preflight_activity.widget.isHidden()
    window.preflight_activity.cancel()


def test_closing_document_while_opening_clears_its_indicator(window, tmp_path):
    path = tmp_path / "still-opening.pdf"
    key = window._canonical(path)
    window.documents[key] = None
    window.document_paths[key] = path
    window.document_generations[key] = 42
    window._refresh_document_combo()
    window._select_path(key)
    assert window.open_activity.token == 42
    window.close_selected_document()
    assert window.open_activity.token is None
    assert window.open_activity.widget.isHidden()


def test_indicator_does_not_intercept_mouse_events(app):
    parent = QWidget()
    activity = DelayedActivity(parent)
    assert activity.widget.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    parent.deleteLater()

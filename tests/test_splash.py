import ast
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from ppview.i18n.strings import strings
from ppview.ui.splash import StartupSplash
from ppview.main import _construct_main_window


def test_startup_splash_uses_localized_identity_and_closes_cleanly():
    app = QApplication.instance() or QApplication([])
    expected = {
        "en": "Starting PPView…",
        "ja": "PPView を起動しています…",
        "fr": "Démarrage de PPView…",
    }
    for language, status in expected.items():
        splash = StartupSplash(language)
        assert splash._t["startup_status"] == status
        assert splash._t["title_suffix"]
        assert splash.pixmap().width() > 0
        splash.show()
        app.processEvents()
        assert splash._timer.isActive()
        splash.complete_branding()
        app.processEvents()
        splash.close()
        app.processEvents()
        assert not splash._timer.isActive()


def test_main_window_import_is_deferred_until_after_splash():
    main_path = Path(__file__).resolve().parents[1] / "src" / "ppview" / "main.py"
    tree = ast.parse(main_path.read_text(encoding="utf-8-sig"))
    top_level_imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]
    assert not any(node.module == "ppview.ui.window" for node in top_level_imports)
    main_func = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    statements = main_func.body
    splash_show_index = next(i for i, node in enumerate(statements)
                             if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                             and isinstance(node.value.func, ast.Attribute)
                             and node.value.func.attr == "show")
    deferred_import = next(node for node in ast.walk(main_func)
                           if isinstance(node, ast.ImportFrom) and node.module == "ppview.ui.window")
    assert statements[splash_show_index].lineno < deferred_import.lineno
    assert strings("en")["startup_status"] != strings("ja")["startup_status"]
    assert strings("fr")["startup_failed"].format(error="x")


def test_failed_window_construction_closes_splash():
    app = QApplication.instance() or QApplication([])
    splash = StartupSplash("en")
    splash.show()
    app.processEvents()

    def fail(_path):
        raise RuntimeError("simulated startup failure")

    try:
        _construct_main_window(splash, fail, None)
    except RuntimeError as error:
        assert str(error) == "simulated startup failure"
    else:
        raise AssertionError("the simulated window failure should propagate")
    app.processEvents()
    assert not splash.isVisible()
    assert not splash._timer.isActive()

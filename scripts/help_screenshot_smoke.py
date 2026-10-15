"""Capture the offline guide/About dialogs for each supported UI language."""
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from ppview import __version__
from ppview.build_info import build_commit
from ppview.ui.help_dialogs import AboutDialog, UserGuideDialog

root = Path(__file__).resolve().parents[1]
out = root / "dist"; out.mkdir(exist_ok=True)
app = QApplication.instance() or QApplication([])
# Qt's offscreen platform does not always enumerate Windows fonts. Register the
# installed OS fonts for accurate visual QA; these font files are not packaged.
font_dir = Path(__import__("os").environ.get("WINDIR", r"C:\Windows")) / "Fonts"
for candidate in (font_dir / "arial.ttf", font_dir / "meiryo.ttc"):
    if candidate.is_file(): QFontDatabase.addApplicationFont(str(candidate))
families = QFontDatabase.families()
logo = root / "assets" / "logo" / "ppview.ico"
for language in ("en", "ja", "fr"):
    for kind, dialog in (
        ("about", AboutDialog(None, language, build_commit(), logo)),
        ("guide", UserGuideDialog(None, language)),
    ):
        family = "Meiryo" if language == "ja" and "Meiryo" in families else ("Arial" if "Arial" in families else "Sans Serif")
        dialog.setFont(QFont(family, 10))
        dialog.resize(620, 520); dialog.show(); app.processEvents()
        path = out / f"PPView-v{__version__}-help-{language}-{kind}.png"
        if not dialog.grab().save(str(path), "PNG"):
            raise RuntimeError(f"Could not save {path}")
        print(path)
        dialog.close(); app.processEvents()
app.quit()

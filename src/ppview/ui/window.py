from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QObject, QRunnable, QSettings, Qt, QThreadPool, Signal
from PySide6.QtGui import QAction, QKeySequence, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QToolBar, QVBoxLayout, QWidget)

from ppview.core.document import DocumentError, DocumentInfo, inspect_file, render_page, validate_rendering
from ppview.i18n.strings import initial_language, strings


class WorkerSignals(QObject):
    result = Signal(int, object)
    failed = Signal(int, str)
    finished = Signal(int)

class Task(QRunnable):
    def __init__(self, token: int, fn):
        super().__init__(); self.token = token; self.fn = fn; self.signals = WorkerSignals()
    def run(self):
        try: self.signals.result.emit(self.token, self.fn())
        except DocumentError as e: self.signals.failed.emit(self.token, e.args[0])
        except Exception: self.signals.failed.emit(self.token, "invalid")
        finally: self.signals.finished.emit(self.token)

class DropArea(QFrame):
    files_dropped = Signal(list)
    def __init__(self):
        super().__init__(); self.setAcceptDrops(True); self.setObjectName("dropArea")
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()
    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths: self.files_dropped.emit(paths)
        event.acceptProposedAction()

class MainWindow(QMainWindow):
    def __init__(self, initial_file: str | None = None):
        super().__init__(); self.language = initial_language(); self.t = strings(self.language)
        self.info: DocumentInfo | None = None; self.path: Path | None = None; self.page = 0
        self.zoom = 1.0; self.fit_mode = "page"; self.token = 0; self.render_serial = 0
        self.pool = QThreadPool.globalInstance(); self.pool.setMaxThreadCount(2)
        self._build(); self._translate()
        if initial_file: self.open_file(initial_file)

    def _build(self):
        self.setMinimumSize(900, 600); self.resize(1280, 820)
        toolbar = QToolBar(); toolbar.setMovable(False); self.addToolBar(toolbar); self.toolbar = toolbar
        self.actions = {}
        for key in ("fit_page", "fit_width", "zoom_out", "actual", "zoom_in"):
            action = QAction(self); action.triggered.connect(lambda checked=False, k=key: self.set_view(k)); toolbar.addAction(action); self.actions[key] = action
        self.panel_action = QAction(self); self.panel_action.setCheckable(True); self.panel_action.setChecked(True)
        self.panel_action.toggled.connect(self._toggle_panel); toolbar.addSeparator(); toolbar.addAction(self.panel_action)
        toolbar.addSeparator()
        self.prev = QPushButton(); self.prev.clicked.connect(lambda: self.change_page(-1)); toolbar.addWidget(self.prev)
        self.page_label = QLabel(); toolbar.addWidget(self.page_label)
        self.next = QPushButton(); self.next.clicked.connect(lambda: self.change_page(1)); toolbar.addWidget(self.next)
        self.splitter = QSplitter(); self.setCentralWidget(self.splitter)
        self.drop = DropArea(); self.drop.files_dropped.connect(self._drop_files)
        self.drop_layout = QVBoxLayout(self.drop); self.drop_layout.addStretch()
        self.drop_label = QLabel(); self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.drop_label.setWordWrap(True)
        self.drop_layout.addWidget(self.drop_label); self.hint_label = QLabel(); self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.drop_layout.addWidget(self.hint_label); self.drop_layout.addStretch()
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter); self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.preview = QLabel(); self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed); self.scroll.setWidget(self.preview)
        self.preview.hide(); self.splitter.addWidget(self.drop); self.splitter.addWidget(self.scroll); self.splitter.setStretchFactor(0, 1)
        self.panel = QWidget(); self.panel.setMinimumWidth(280); self.panel_layout = QVBoxLayout(self.panel); self.splitter.addWidget(self.panel); self.splitter.setStretchFactor(1, 4)
        self.details = {}
        for key in ("filename", "type", "size", "pages", "dimensions", "status", "render", "diagnostics"):
            label = QLabel(); label.setWordWrap(True); self.details[key] = label; self.panel_layout.addWidget(label)
        self.panel_layout.addStretch(); self.lang_combo = QComboBox(); self.panel_layout.addWidget(self.lang_combo)
        self.lang_combo.currentIndexChanged.connect(self._language_changed)
        menu = self.menuBar().addMenu(""); self.file_menu = menu
        self.open_action = QAction(self); self.open_action.setShortcut(QKeySequence.StandardKey.Open); self.open_action.triggered.connect(self.choose_file); menu.addAction(self.open_action)
        self.exit_action = QAction(self); self.exit_action.triggered.connect(self.close); menu.addAction(self.exit_action)
        self.help_menu = self.menuBar().addMenu(""); self.about_action = QAction(self); self.about_action.triggered.connect(self.about); self.help_menu.addAction(self.about_action)
        self.setStyleSheet("QMainWindow { background:#f4f6f8 } QToolBar { spacing:8px; padding:6px } QFrame#dropArea { background:white; border:2px dashed #aeb9c5; border-radius:12px; margin:14px } QLabel { color:#263445 } QPushButton { padding:5px 10px }")
        self._document_state(None)

    def _translate(self):
        t = self.t; self.setWindowTitle(t["app"]); self.toolbar.setWindowTitle(t["app"])
        for k, a in self.actions.items(): a.setText(t[k])
        self.panel_action.setText(t["information"])
        self.prev.setText("‹"); self.prev.setToolTip(t["previous"]); self.next.setText("›"); self.next.setToolTip(t["next"])
        self.drop_label.setText(t["drop"]); self.hint_label.setText(t["open_hint"])
        self.file_menu.setTitle(t["file"]); self.open_action.setText(t["open"] + "\t" + t["shortcut"]); self.exit_action.setText(t["exit"])
        self.help_menu.setTitle(t["help"]); self.about_action.setText(t["about"])
        old = self.lang_combo.blockSignals(True); self.lang_combo.clear(); self.lang_combo.addItem(t["english"], "en"); self.lang_combo.addItem(t["japanese"], "ja"); self.lang_combo.setCurrentIndex(0 if self.language == "en" else 1); self.lang_combo.blockSignals(old)
        for key in self.details: self.details[key].setText(f"{t[key]}: {t['not_open']}")
        self._update_page_label()

    def _language_changed(self, index):
        if index < 0: return
        language = self.lang_combo.itemData(index)
        if language and language != self.language:
            self.language = language; QSettings("papagori", "PPView").setValue("language", language); self.t = strings(language); self._translate(); self._document_state(self.info)

    def _toggle_panel(self, visible): self.panel.setVisible(visible)

    def _drop_files(self, paths): self.open_file(paths[0])
    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t["open_title"], "", self.t["filter"])
        if path: self.open_file(path)

    def open_file(self, path: str):
        self.token += 1; token = self.token; self.path = Path(path); self.info = None; self.page = 0; self.zoom = 1.0
        self.preview.hide(); self.drop.show(); self._document_state(None, loading=True)
        task = Task(token, lambda: inspect_file(path)); task.signals.result.connect(self._loaded); task.signals.failed.connect(self._failed); self.pool.start(task)

    def _loaded(self, token, info):
        if token != self.token: return
        self.info = info; self.drop.hide(); self.preview.show(); self.fit_mode = "page"; self._document_state(info); self._render()
        task = Task(token, lambda: validate_rendering(info.path, len(info.pages)))
        task.signals.result.connect(self._validation_done); task.signals.failed.connect(self._validation_failed); self.pool.start(task)

    def _failed(self, token, reason):
        if token != self.token: return
        self.info = None; self.preview.clear(); self.drop.show(); self._document_state(None, error=reason)

    def _validation_done(self, token, _result):
        if token != self.token: return
        self.details["render"].setText(f"{self.t['render']}: {self.t['passed']}")
        self.details["diagnostics"].setText(f"{self.t['diagnostics']}: {self.t['done']}")

    def _validation_failed(self, token, _reason):
        if token != self.token: return
        self.details["render"].setText(f"{self.t['render']}: {self.t['error']}")
        self.details["diagnostics"].setText(f"{self.t['diagnostics']}: {self.t['failed']}")

    def _document_state(self, info, loading=False, error=None):
        t = self.t
        if not info:
            if error:
                message = t.get(error, t["invalid"]); status = t["error"]
                QMessageBox.warning(self, t["app"], message)
            else: status = t["loading"] if loading else t["not_open"]
            for key in self.details: self.details[key].setText(f"{t[key]}: {status}")
            return
        self.details["filename"].setText(f"{t['filename']}: {info.path.name}")
        self.details["type"].setText(f"{t['type']}: {t[info.kind]}")
        self.details["size"].setText(f"{t['size']}: {info.size / 1048576:.2f} {t['mb']}")
        self.details["pages"].setText(f"{t['pages']}: {len(info.pages)}")
        self.details["dimensions"].setText(""); self._update_dimensions()
        self.details["status"].setText(f"{t['status']}: {t['ready']}")
        self.details["render"].setText(f"{t['render']}: {t['checking']}")
        self.details["diagnostics"].setText(f"{t['diagnostics']}: {t['pages_ok']}")
        self.setWindowTitle(f"{info.path.name} — PPView")

    def _update_dimensions(self):
        if self.info:
            p = self.info.pages[self.page]
            self.details["dimensions"].setText(f"{self.t['dimensions']}: {p.width_mm:.1f} × {p.height_mm:.1f} mm")
    def _update_page_label(self):
        self.page_label.setText(f"{self.t['page']} {self.page + 1} {self.t['of']} {len(self.info.pages) if self.info else 0}")
        self.prev.setEnabled(bool(self.info and self.page > 0)); self.next.setEnabled(bool(self.info and self.page + 1 < len(self.info.pages)))
    def change_page(self, delta):
        if not self.info: return
        self.page = max(0, min(len(self.info.pages)-1, self.page+delta)); self._update_page_label(); self._update_dimensions(); self._render()
    def set_view(self, key):
        if key == "zoom_in": self.fit_mode = "manual"; self.zoom *= 1.2
        elif key == "zoom_out": self.fit_mode = "manual"; self.zoom /= 1.2
        elif key == "actual": self.fit_mode = "manual"; self.zoom = 1.0
        else: self.fit_mode = "page" if key == "fit_page" else "width"
        self._render()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.info and self.fit_mode in ("page", "width"): self._render()
    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.set_view("zoom_in" if event.angleDelta().y() > 0 else "zoom_out"); event.accept()
        else: super().wheelEvent(event)
    def _render(self):
        if not self.info: self._update_page_label(); return
        page = self.info.pages[self.page]; available_w = max(100, self.scroll.viewport().width()-24); available_h = max(100, self.scroll.viewport().height()-24)
        if self.fit_mode == "page": pixel_scale = min(available_w/page.width_pt, available_h/page.height_pt)
        elif self.fit_mode == "width": pixel_scale = available_w/page.width_pt
        else: pixel_scale = self.zoom * 96 / 72
        self.render_serial += 1
        token = self.token; serial = self.render_serial; index = self.page; path = self.info.path
        task = Task(token, lambda: (serial, index, render_page(path, index, pixel_scale))); task.signals.result.connect(self._image_ready); task.signals.failed.connect(self._render_failed); self.pool.start(task)
        self._update_page_label()
    def _image_ready(self, token, result):
        if token != self.token: return
        serial, index, image = result
        if serial != self.render_serial or index != self.page: return
        self.preview.setPixmap(QPixmap.fromImage(image)); self.preview.resize(image.size())
    def _render_failed(self, token, _reason):
        if token == self.token: self.details["render"].setText(f"{self.t['render']}: {self.t['error']}")
    def about(self): QMessageBox.about(self, self.t["about"], self.t["about_text"])

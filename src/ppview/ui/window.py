from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSettings, Qt, QThreadPool, Signal, QPoint, QEvent
from PySide6.QtGui import QAction, QKeySequence, QPixmap, QCursor
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QToolBar, QVBoxLayout, QWidget, QToolButton)

from ppview.core.document import DocumentError, DocumentInfo, inspect_file, render_page, validate_rendering
from ppview.i18n.strings import initial_language, strings


class WorkerSignals(QObject):
    result = Signal(int, object)
    failed = Signal(int, str)
    finished = Signal(int)


class Task(QRunnable):
    def __init__(self, token: int, fn):
        super().__init__()
        self.token, self.fn, self.signals = token, fn, WorkerSignals()

    def run(self):
        try:
            self.signals.result.emit(self.token, self.fn())
        except DocumentError as exc:
            self.signals.failed.emit(self.token, exc.args[0])
        except Exception:
            self.signals.failed.emit(self.token, "invalid")
        finally:
            self.signals.finished.emit(self.token)


class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths: self.files_dropped.emit(paths)
        event.acceptProposedAction()


class PreviewLabel(QLabel):
    pan = Signal(int, int)
    zoom_at = Signal(int, int, int)
    fit_page = Signal()

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_pos: QPoint | None = None
        self._drag_button = Qt.MouseButton.NoButton
        self._space_down = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space_down = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space_down = False
            if self._drag_pos is None: self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        allowed = event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton)
        if allowed:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self._drag_pos = event.globalPosition().toPoint()
            self._drag_button = event.button()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            now = event.globalPosition().toPoint()
            delta = now - self._drag_pos
            self._drag_pos = now
            self.pan.emit(delta.x(), delta.y())
            event.accept()
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_pos is not None and event.button() == self._drag_button:
            self._drag_pos = None
            self._drag_button = Qt.MouseButton.NoButton
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.fit_page.emit()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            pos = self.mapToParent(event.position().toPoint())
            self.zoom_at.emit(event.angleDelta().y(), pos.x(), pos.y())
            event.accept()
        else:
            super().wheelEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, initial_file: str | None = None):
        super().__init__()
        self.language = initial_language()
        self.t = strings(self.language)
        self.documents: dict[str, DocumentInfo | None] = {}
        self.document_paths: dict[str, Path] = {}
        self.validation: dict[str, str] = {}
        self.info: DocumentInfo | None = None
        self.path: Path | None = None
        self.page = 0
        self.zoom = 1.0
        self.fit_mode = "page"
        self.token = 0
        self.render_serial = 0
        self._pending_zoom_anchor = None
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(2)
        self._tasks = set()
        self._build()
        self._translate()
        if initial_file: self.open_files([initial_file])

    @staticmethod
    def _canonical(path: str | Path) -> str:
        return str(Path(path).expanduser().resolve()).casefold()

    def _build(self):
        self.setMinimumSize(900, 600)
        self.resize(1280, 820)
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)
        self.toolbar = toolbar
        self.actions = {}
        for key in ("fit_page", "fit_width", "zoom_out", "actual", "zoom_in"):
            action = QAction(self)
            action.triggered.connect(lambda checked=False, k=key: self.set_view(k))
            toolbar.addAction(action)
            self.actions[key] = action
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(48)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.zoom_label)
        toolbar.addSeparator()
        self.panel_action = QAction(self)
        self.panel_action.setCheckable(True)
        self.panel_action.setChecked(True)
        self.panel_action.toggled.connect(self._toggle_panel)
        toolbar.addAction(self.panel_action)
        toolbar.addSeparator()
        self.prev = QPushButton(); self.prev.clicked.connect(lambda: self.change_page(-1)); toolbar.addWidget(self.prev)
        self.page_label = QLabel(); toolbar.addWidget(self.page_label)
        self.next = QPushButton(); self.next.clicked.connect(lambda: self.change_page(1)); toolbar.addWidget(self.next)
        toolbar.addSeparator()
        self.document_combo = QComboBox(); self.document_combo.setMinimumWidth(160); self.document_combo.setMaximumWidth(260)
        self.document_combo.currentIndexChanged.connect(self._select_document)
        toolbar.addWidget(self.document_combo)
        self.close_document_action = QAction(self); self.close_document_action.triggered.connect(self.close_selected_document); toolbar.addAction(self.close_document_action)
        self.clear_action = QAction(self); self.clear_action.triggered.connect(self.clear_all); toolbar.addAction(self.clear_action)

        self.splitter = QSplitter()
        self.setCentralWidget(self.splitter)
        self.drop = DropArea(); self.drop.files_dropped.connect(self._drop_files)
        self.drop_layout = QVBoxLayout(self.drop); self.drop_layout.addStretch()
        self.drop_label = QLabel(); self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.drop_label.setWordWrap(True)
        self.drop_layout.addWidget(self.drop_label)
        self.hint_label = QLabel(); self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.drop_layout.addWidget(self.hint_label); self.drop_layout.addStretch()
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(False); self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter); self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.preview = PreviewLabel()
        self.preview.pan.connect(self._pan)
        self.preview.zoom_at.connect(self._zoom_at)
        self.preview.fit_page.connect(lambda: self.set_view("fit_page"))
        self.scroll.setWidget(self.preview)
        self.preview.hide()
        self.splitter.addWidget(self.drop); self.splitter.addWidget(self.scroll); self.splitter.setStretchFactor(0, 1); self.splitter.setStretchFactor(1, 4)
        self.panel = QWidget(); self.panel.setMinimumWidth(280); self.panel_layout = QVBoxLayout(self.panel)
        self.info_heading = QLabel(); self.info_heading.setObjectName("panelHeading"); self.panel_layout.addWidget(self.info_heading)
        self.details = {}
        for key in ("filename", "type", "size", "pages", "dimensions", "status"):
            label = QLabel(); label.setWordWrap(True); self.details[key] = label; self.panel_layout.addWidget(label)
        self.check_heading = QLabel(); self.check_heading.setObjectName("panelHeading"); self.panel_layout.addWidget(self.check_heading)
        for key in ("render", "diagnostics"):
            label = QLabel(); label.setWordWrap(True); self.details[key] = label; self.panel_layout.addWidget(label)
        self.panel_layout.addStretch(); self.lang_combo = QComboBox(); self.panel_layout.addWidget(self.lang_combo)
        self.lang_combo.currentIndexChanged.connect(self._language_changed)
        self.splitter.addWidget(self.panel); self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([190, 820, 280])
        self.scroll.viewport().installEventFilter(self)
        menu = self.menuBar().addMenu(""); self.file_menu = menu
        self.open_action = QAction(self); self.open_action.setShortcut(QKeySequence.StandardKey.Open); self.open_action.triggered.connect(self.choose_files); menu.addAction(self.open_action)
        self.exit_action = QAction(self); self.exit_action.triggered.connect(self.close); menu.addAction(self.exit_action)
        self.help_menu = self.menuBar().addMenu(""); self.about_action = QAction(self); self.about_action.triggered.connect(self.about); self.help_menu.addAction(self.about_action)
        self.setStyleSheet("""
            QMainWindow { background: palette(window); }
            QToolBar { spacing: 5px; padding: 6px; background: palette(window); border-bottom: 1px solid palette(mid); }
            QToolBar QToolButton, QToolBar QPushButton { color: palette(button-text); background: palette(button); border: 1px solid palette(mid); border-radius: 4px; padding: 5px 8px; }
            QToolBar QToolButton:hover, QToolBar QPushButton:hover { background: palette(highlight); color: palette(highlighted-text); }
            QToolBar QToolButton:disabled, QToolBar QPushButton:disabled { color: palette(mid); background: palette(window); }
            QFrame#dropArea { background: palette(base); border: 2px dashed palette(mid); border-radius: 12px; margin: 14px; }
            QLabel#panelHeading { font-weight: 700; padding-top: 8px; }
        """)
        self._document_state(None)
        self._update_document_controls()

    def _translate(self):
        t = self.t
        self.setWindowTitle(t["app"]); self.toolbar.setWindowTitle(t["app"])
        for key, action in self.actions.items():
            action.setText(t[key]); action.setToolTip(t[f"tip_{key}"])
        self.panel_action.setText(t["information"]); self.panel_action.setToolTip(t["tip_information"])
        self.close_document_action.setText(t["close_document"]); self.clear_action.setText(t["clear_all"])
        self.close_document_action.setToolTip(t["tip_close"]); self.clear_action.setToolTip(t["tip_clear"])
        self.prev.setText("‹"); self.prev.setToolTip(t["previous"]); self.next.setText("›"); self.next.setToolTip(t["next"])
        self.drop_label.setText(t["drop"]); self.hint_label.setText(t["open_hint"])
        self.info_heading.setText(t["document_information"]); self.check_heading.setText(t["preflight_checks"])
        self.file_menu.setTitle(t["file"]); self.open_action.setText(t["open"] + "\t" + t["shortcut"]); self.exit_action.setText(t["exit"])
        self.help_menu.setTitle(t["help"]); self.about_action.setText(t["about"])
        previous = self.lang_combo.blockSignals(True); self.lang_combo.clear(); self.lang_combo.addItem(t["english"], "en"); self.lang_combo.addItem(t["japanese"], "ja")
        self.lang_combo.setCurrentIndex(0 if self.language == "en" else 1); self.lang_combo.blockSignals(previous)
        self._document_state(self.info); self._update_document_controls()

    def _language_changed(self, index):
        if index < 0: return
        language = self.lang_combo.itemData(index)
        if language and language != self.language:
            self.language = language; QSettings("papagori", "PPView").setValue("language", language)
            self.t = strings(language); self._translate()

    def _toggle_panel(self, visible):
        self.panel.setVisible(visible)
        if self.info and self.fit_mode in ("page", "width"): self._render()

    def _drop_files(self, paths): self.open_files(paths)

    def choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.t["open_title"], "", self.t["filter"])
        if paths: self.open_files(paths)

    def open_file(self, path: str):
        self.open_files([path])

    def open_files(self, paths):
        added = []
        for path in paths:
            p = Path(path).expanduser().resolve()
            if not p.is_file(): continue
            key = self._canonical(p)
            if key not in self.documents:
                self.documents[key] = None
                self.document_paths[key] = p
                added.append((key, p))
        self._refresh_document_combo()
        if added:
            self._select_path(added[-1][0])
            for key, p in added: self._inspect_document(key, p)

    def _refresh_document_combo(self):
        current = self._canonical(self.path) if self.path else None
        self.document_combo.blockSignals(True); self.document_combo.clear()
        for key, info in self.documents.items():
            label = info.path.name if info else self.document_paths.get(key, Path(key)).name + " …"
            self.document_combo.addItem(label, key)
        if current:
            idx = self.document_combo.findData(current)
            if idx >= 0: self.document_combo.setCurrentIndex(idx)
        self.document_combo.blockSignals(False)

    def _select_path(self, key):
        self.token += 1; self.render_serial += 1
        self.path = self.document_paths.get(key, Path(key)); self.info = self.documents.get(key); self.page = 0
        self.zoom = 1.0; self.fit_mode = "page"
        self.preview.clear(); self.preview.hide()
        self.drop.setVisible(self.info is None)
        if self.info:
            self.drop.hide(); self.preview.show(); self._document_state(self.info); self._render(); self._validate_selected()
        else:
            self._document_state(None, loading=True)
        self._refresh_document_combo(); self._update_document_controls()

    def _select_document(self, index):
        key = self.document_combo.itemData(index) if index >= 0 else None
        if key and key != (self._canonical(self.path) if self.path else None): self._select_path(key)

    def _inspect_document(self, key, path):
        token = self.token if key == (self._canonical(self.path) if self.path else None) else -1
        task = Task(token, lambda p=path: inspect_file(p))
        task.signals.result.connect(lambda _token, info, k=key: self._loaded_document(k, info))
        task.signals.failed.connect(lambda _token, error, k=key: self._failed_document(k, error))
        self._start_task(task)

    def _loaded_document(self, key, info):
        if key not in self.documents: return
        self.documents[key] = info; self._refresh_document_combo()
        if key != (self._canonical(self.path) if self.path else None): return
        self.info = info; self.drop.hide(); self.preview.show(); self.fit_mode = "page"
        self._document_state(info); self._render(); self._update_document_controls()
        token = self.token
        self._validate_selected()

    def _failed_document(self, key, reason):
        if key not in self.documents: return
        self.documents.pop(key); self._refresh_document_combo()
        self.document_paths.pop(key, None)
        self.validation.pop(key, None)
        if key != (self._canonical(self.path) if self.path else None): return
        self.info = None; self.preview.clear(); self.drop.show(); self._document_state(None, error=reason)
        self.path = None; self._update_document_controls()

    def close_selected_document(self):
        if not self.path: return
        key = self._canonical(self.path); keys = list(self.documents)
        index = keys.index(key); self.documents.pop(key, None); self.document_paths.pop(key, None); self.validation.pop(key, None)
        if self.documents:
            remaining = list(self.documents)
            target = remaining[min(index, len(remaining) - 1)]
            self._select_path(target)
        else:
            self.token += 1; self.render_serial += 1; self.path = None; self.info = None; self.page = 0
            self.preview.clear(); self.preview.hide(); self.drop.show(); self._document_state(None)
            self._refresh_document_combo(); self._update_document_controls()

    def clear_all(self):
        self.token += 1; self.render_serial += 1
        self.documents.clear(); self.document_paths.clear(); self.validation.clear(); self.path = None; self.info = None; self.page = 0
        self.preview.clear(); self.preview.hide(); self.drop.show(); self._document_state(None)
        self._refresh_document_combo(); self._update_document_controls()

    def _update_document_controls(self):
        has = self.info is not None
        for action in self.actions.values(): action.setEnabled(has)
        self.close_document_action.setEnabled(bool(self.path)); self.clear_action.setEnabled(bool(self.documents))
        self.document_combo.setEnabled(bool(self.documents)); self._update_page_label()

    def _validate_selected(self):
        if not self.info or not self.path: return
        key = self._canonical(self.path)
        if key in self.validation:
            self._validation_display(self.validation[key])
            return
        self.validation[key] = "checking"
        self._validation_display("checking")
        token = self.token
        info = self.info
        task = Task(token, lambda: validate_rendering(info.path, len(info.pages)))
        task.signals.result.connect(lambda tok, _result, k=key: self._validation_done_for(k, tok))
        task.signals.failed.connect(lambda tok, _err, k=key: self._validation_failed_for(k, tok))
        self._start_task(task)

    def _start_task(self, task):
        # Keep the Python QRunnable wrapper alive until its queued signals have
        # reached the GUI thread. This matters for short-lived inspect tasks.
        self._tasks.add(task)
        task.signals.finished.connect(lambda _token, current=task: self._tasks.discard(current))
        self.pool.start(task)

    def _validation_display(self, status):
        if not self.info: return
        self.details["render"].setText(f"{self.t['render']}: {self.t[status]}")
        self.details["diagnostics"].setText(f"{self.t['diagnostics']}: {self.t['basic_only']}")

    def _validation_done_for(self, key, token):
        if key not in self.documents: return
        self.validation[key] = "passed"
        if token == self.token and key == (self._canonical(self.path) if self.path else None): self._validation_display("passed")

    def _validation_failed_for(self, key, token):
        if key not in self.documents: return
        self.validation[key] = "failed"
        if token == self.token and key == (self._canonical(self.path) if self.path else None): self._validation_display("failed")

    def _document_state(self, info, loading=False, error=None):
        t = self.t
        if not info:
            status = t.get(error, t["invalid"]) if error else (t["loading"] if loading else t["not_open"])
            for key in self.details: self.details[key].setText(f"{t[key]}: {status}")
            if error: QMessageBox.warning(self, t["app"], status)
            self.zoom_label.setText("—")
            return
        self.details["filename"].setText(f"{t['filename']}: {info.path.name}")
        self.details["type"].setText(f"{t['type']}: {t[info.kind]}")
        self.details["size"].setText(f"{t['size']}: {info.size / 1048576:.2f} {t['mb']}")
        self.details["pages"].setText(f"{t['pages']}: {len(info.pages)}")
        self.details["status"].setText(f"{t['status']}: {t['ready']}")
        self.details["render"].setText(f"{t['render']}: {t['checking']}")
        self.details["diagnostics"].setText(f"{t['diagnostics']}: {t['basic_only']}")
        self._update_dimensions(); self.setWindowTitle(f"{info.path.name} — PPView")

    def _update_dimensions(self):
        if self.info:
            page = self.info.pages[self.page]
            self.details["dimensions"].setText(f"{self.t['dimensions']}: {page.width_mm:.1f} × {page.height_mm:.1f} mm")

    def _update_page_label(self):
        self.page_label.setText(f"{self.t['page']} {self.page + 1} {self.t['of']} {len(self.info.pages) if self.info else 0}")
        self.prev.setEnabled(bool(self.info and self.page > 0)); self.next.setEnabled(bool(self.info and self.page + 1 < len(self.info.pages)))

    def change_page(self, delta):
        if not self.info: return
        self.page = max(0, min(len(self.info.pages) - 1, self.page + delta))
        self._update_page_label(); self._update_dimensions(); self._render()

    def _fit_zoom(self, mode=None):
        if not self.info: return 1.0
        mode = mode or self.fit_mode
        page = self.info.pages[self.page]
        viewport = self.scroll.viewport().size()
        dpr = max(1.0, self.devicePixelRatioF())
        available_w = max(1, viewport.width() - 24) * dpr
        available_h = max(1, viewport.height() - 24) * dpr
        base = 96.0 / 72.0 * dpr
        width = available_w / (page.width_pt * base)
        height = available_h / (page.height_pt * base)
        # This is a vector re-render, so fitting may enlarge small pages. The zoom
        # factor remains bounded; raster content is never retained between pages.
        return max(0.05, min(8.0, min(width, height) if mode == "page" else width))

    def set_view(self, key):
        if key == "zoom_in": self.fit_mode = "manual"; self.zoom = min(8.0, self.zoom * 1.2)
        elif key == "zoom_out": self.fit_mode = "manual"; self.zoom = max(0.05, self.zoom / 1.2)
        elif key == "actual": self.fit_mode = "manual"; self.zoom = 1.0
        elif key == "fit_width": self.fit_mode = "width"
        else: self.fit_mode = "page"
        self._render()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.info and self.fit_mode in ("page", "width"): self._render()

    def eventFilter(self, watched, event):
        if watched is self.scroll.viewport() and event.type() == QEvent.Type.Resize:
            if self.info and self.fit_mode in ("page", "width"): self._render()
        return super().eventFilter(watched, event)

    def _pan(self, dx, dy):
        bars = (self.scroll.horizontalScrollBar(), self.scroll.verticalScrollBar())
        for bar, delta in zip(bars, (dx, dy)):
            bar.setValue(max(bar.minimum(), min(bar.maximum(), bar.value() - delta)))

    def _zoom_at(self, delta, x, y):
        if not self.info or not delta: return
        old = self.zoom if self.fit_mode == "manual" else self._fit_zoom()
        new = max(0.05, min(8.0, old * (1.2 ** (delta / 120))))
        if abs(new - old) < 1e-7: return
        bar_x, bar_y = self.scroll.horizontalScrollBar(), self.scroll.verticalScrollBar()
        anchor_x = bar_x.value() + x; anchor_y = bar_y.value() + y
        self.fit_mode = "manual"; self.zoom = new; self._render()
        self._pending_zoom_anchor = (int(anchor_x), int(anchor_y), x, y, new / old)

    def _render(self):
        if not self.info:
            self._update_page_label(); return
        page = self.info.pages[self.page]
        zoom = self._fit_zoom() if self.fit_mode in ("page", "width") else self.zoom
        self.zoom_label.setText(f"{zoom * 100:.0f}%")
        dpr = max(1.0, self.devicePixelRatioF())
        pixel_scale = 96.0 / 72.0 * zoom * dpr
        self.render_serial += 1
        token, serial, index, path = self.token, self.render_serial, self.page, self.info.path
        task = Task(token, lambda: (serial, index, dpr, render_page(path, index, pixel_scale)))
        task.signals.result.connect(self._image_ready); task.signals.failed.connect(self._render_failed); self._start_task(task)
        self._update_page_label()

    def _image_ready(self, token, result):
        if token != self.token: return
        serial, index, dpr, image = result
        if serial != self.render_serial or index != self.page: return
        pixmap = QPixmap.fromImage(image); pixmap.setDevicePixelRatio(dpr)
        self.preview.setPixmap(pixmap); self.preview.resize(pixmap.deviceIndependentSize().toSize())
        if self._pending_zoom_anchor:
            ax, ay, x, y, factor = self._pending_zoom_anchor
            self._pending_zoom_anchor = None
            self.scroll.horizontalScrollBar().setValue(int(ax * factor - x))
            self.scroll.verticalScrollBar().setValue(int(ay * factor - y))

    def _render_failed(self, token, _reason):
        if token == self.token: self.details["render"].setText(f"{self.t['render']}: {self.t['error']}")

    def _validation_done(self, token, _result):
        if token != self.token: return
        self._validation_display("passed")

    def _validation_failed(self, token, _reason):
        if token != self.token: return
        self._validation_display("failed")

    def about(self): QMessageBox.about(self, self.t["about"], self.t["about_text"])

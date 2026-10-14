from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (QObject, QRunnable, QSettings, Qt, QThreadPool, Signal,
    QPoint, QEvent, QDir, QUrl, QModelIndex, QSize)
from PySide6.QtGui import QAction, QKeySequence, QPixmap, QDesktopServices, QIcon, QPalette, QColor
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QToolBar, QVBoxLayout, QWidget, QToolButton, QFileSystemModel, QTreeView,
    QAbstractItemView, QLineEdit, QSlider, QMenu, QWidgetAction, QStyle, QHeaderView)
from PySide6.QtSvg import QSvgRenderer

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


class WindowDropFilter(QObject):
    """Route supported file drops from any nested window widget."""
    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def eventFilter(self, watched, event):
        if event.type() not in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop):
            return False
        widget = watched if isinstance(watched, QWidget) else None
        if widget is None or (widget is not self.window and not self.window.isAncestorOf(widget)):
            return False
        urls = [url for url in event.mimeData().urls() if url.isLocalFile()] if event.mimeData().hasUrls() else []
        if not urls:
            return False
        if event.type() == QEvent.Type.Drop:
            self.window._drop_files([url.toLocalFile() for url in urls])
        event.acceptProposedAction()
        return True


class LinkLabel(QLabel):
    activated = Signal(str)

    def __init__(self, text: str, url: str, parent=None):
        super().__init__(text, parent)
        self.url = url
        self.setObjectName("footerLink")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(url)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_link()
            event.accept()
        else:
            super().mousePressEvent(event)

    def open_link(self):
        self.activated.emit(self.url)
        QDesktopServices.openUrl(QUrl(self.url))


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
        pos = self.mapToParent(event.position().toPoint())
        self.zoom_at.emit(event.angleDelta().y(), pos.x(), pos.y())
        event.accept()

    def enterEvent(self, event):
        if self._drag_pos is None:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._drag_pos is None:
            self.unsetCursor()
        super().leaveEvent(event)


class ZoomControl(QWidget):
    zoom_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("zoomControl")
        self.setFixedWidth(88)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 0, 3, 0)
        layout.setSpacing(3)
        self.edit = QLineEdit("100%")
        self.edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit.setFixedWidth(58)
        self.edit.setToolTip("")
        self.edit.editingFinished.connect(self._commit)
        layout.addWidget(self.edit)
        self.popup = QToolButton()
        self.popup.setText("▾")
        self.popup.setFixedWidth(20)
        self.menu = QMenu(self)
        container = QWidget()
        popup_layout = QVBoxLayout(container)
        popup_layout.setContentsMargins(10, 8, 10, 8)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(5, 800)
        self.slider.setFixedWidth(200)
        self.slider.valueChanged.connect(self._slider_changed)
        self.slider.sliderReleased.connect(lambda: self.zoom_requested.emit(self.slider.value() / 100))
        popup_layout.addWidget(self.slider)
        action = QWidgetAction(self.menu)
        action.setDefaultWidget(container)
        self.menu.addAction(action)
        self.popup.setMenu(self.menu)
        self.popup.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.popup.installEventFilter(self)
        self.slider.installEventFilter(self)
        self.edit.installEventFilter(self)
        layout.addWidget(self.popup)
        self._zoom = 1.0

    def _commit(self):
        try:
            value = float(self.edit.text().replace("%", "").strip()) / 100
        except ValueError:
            self.set_zoom(self._zoom)
            return
        self.zoom_requested.emit(max(0.05, min(8.0, value)))

    def _slider_changed(self, value):
        self.edit.setText(f"{value}%")

    def set_zoom(self, zoom):
        self._zoom = max(0.05, min(8.0, float(zoom)))
        self.edit.setText(f"{self._zoom * 100:.0f}%")
        self.slider.blockSignals(True)
        self.slider.setValue(round(self._zoom * 100))
        self.slider.blockSignals(False)

    def wheelEvent(self, event):
        self._zoom_from_wheel(event)

    def eventFilter(self, watched, event):
        if watched in (self.edit, self.popup, self.slider) and event.type() == QEvent.Type.Wheel:
            self._zoom_from_wheel(event)
            return True
        return super().eventFilter(watched, event)

    def _zoom_from_wheel(self, event):
        delta = event.angleDelta().y()
        if delta:
            self.zoom_requested.emit(max(0.05, min(8.0, self._zoom * (1.1 ** (delta / 120)))))
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
        self.settings = QSettings("papagori", "PPView")
        self._preferred_browser_width = int(self.settings.value("browser_width", 300))
        self._build()
        self._drop_filter = WindowDropFilter(self)
        QApplication.instance().installEventFilter(self._drop_filter)
        self._translate()
        if initial_file: self.open_files([initial_file])

    @staticmethod
    def _canonical(path: str | Path) -> str:
        return str(Path(path).expanduser().resolve()).casefold()

    def _install_theme(self):
        app = QApplication.instance()
        palette = QPalette()
        for role, color in ((QPalette.ColorRole.Window,"#0b1424"),(QPalette.ColorRole.WindowText,"#e6eef8"),(QPalette.ColorRole.Base,"#101e32"),(QPalette.ColorRole.AlternateBase,"#162741"),(QPalette.ColorRole.Text,"#e6eef8"),(QPalette.ColorRole.Button,"#1a2e4b"),(QPalette.ColorRole.ButtonText,"#e6eef8"),(QPalette.ColorRole.Highlight,"#1688e8"),(QPalette.ColorRole.HighlightedText,"#ffffff"),(QPalette.ColorRole.Link,"#55baff")):
            palette.setColor(role, QColor(color))
        app.setPalette(palette)
        self.setStyleSheet("""
            QWidget { color:#e6eef8; background:#0b1424; }
            QMenuBar,QMenu,QToolBar { background:#101e32; border:0; }
            QMenuBar::item { padding:5px 9px; } QMenuBar::item:selected,QMenu::item:selected { background:#1d385c; }
            QToolBar { spacing:2px; padding:3px 5px; border-bottom:1px solid #263c59; }
            QToolBar::separator { width:1px; margin:4px 5px; background:#344d6b; }
            QToolButton,QToolBar QPushButton,QPushButton { color:#e6eef8; background:#1a2e4b; border:1px solid #355273; border-radius:5px; padding:3px 5px; }
            QToolButton:hover,QToolBar QPushButton:hover,QPushButton:hover { background:#24517d; border-color:#48a9f5; }
            QToolButton:checked { background:#135c9c; border-color:#38aaff; }
            QToolButton:disabled,QPushButton:disabled { color:#71839b; background:#111c2c; border-color:#26364c; }
            QComboBox,QLineEdit { color:#e6eef8; background:#101e32; border:1px solid #355273; border-radius:4px; padding:4px 6px; }
            QComboBox QAbstractItemView { color:#e6eef8; background:#101e32; selection-background-color:#1688e8; }
            QSlider::groove:horizontal { height:4px; background:#344d6b; border-radius:2px; }
            QSlider::sub-page:horizontal { background:#1688e8; } QSlider::handle:horizontal { width:12px; margin:-5px 0; border-radius:6px; background:#56bdff; }
            QSplitter::handle { background:#263c59; width:2px; }
            QScrollArea,QTreeView,QAbstractItemView { background:#0e1a2b; alternate-background-color:#14243a; border:0; }
            QTreeView::item { padding:3px 2px; } QTreeView::item:selected { background:#155a91; }
            QScrollBar:vertical,QScrollBar:horizontal { background:#101e32; width:12px; height:12px; }
            QScrollBar::handle:vertical,QScrollBar::handle:horizontal { background:#355273; min-height:24px; min-width:24px; border-radius:5px; }
            QScrollBar::handle:hover { background:#4b7198; } QScrollBar::add-line,QScrollBar::sub-line { width:0; height:0; }
            QFrame#dropArea { background:#101e32; border:2px dashed #355273; border-radius:10px; margin:14px; }
            QLabel#panelHeading { color:#67c5ff; font-weight:700; padding-top:8px; }
            QToolBar#branding { border-bottom:1px solid #263c59; padding:2px 12px; }
            QLabel#brandName { color:#eff7ff; font-size:15pt; font-weight:700; }
            QLabel#brandSlogan { color:#91a9c3; font-size:8pt; }
            QWidget#branding { background:#101e32; }
            QStatusBar { background:#101e32; border-top:1px solid #263c59; color:#bdcadd; }
            QWidget#footer { background:#101e32; border-top:1px solid #263c59; color:#bdcadd; font-size:9pt; }
            QLabel#footerLink { color:#67c5ff; } QLabel#footerLink:hover { color:#a5e1ff; text-decoration:underline; }
            QToolTip { color:#f2f7fc; background:#1a2e4b; border:1px solid #4b7198; }
        """)

    def _build_header(self):
        brand = QWidget(); brand.setObjectName("branding")
        row = QHBoxLayout(brand); row.setContentsMargins(8,1,12,1); row.setSpacing(7)
        icon = QLabel(); icon.setPixmap(self._app_icon().pixmap(34,34)); row.addWidget(icon)
        labels = QVBoxLayout(); labels.setSpacing(0)
        self.brand_name = QLabel("PPView"); self.brand_name.setObjectName("brandName")
        self.brand_slogan = QLabel(); self.brand_slogan.setObjectName("brandSlogan")
        labels.addWidget(self.brand_name); labels.addWidget(self.brand_slogan); row.addLayout(labels)
        self.brand_header = brand
        bar = self.menuBar(); bar.setNativeMenuBar(False); self.menu_bar = bar
        top = QWidget(); top_layout = QHBoxLayout(top); top_layout.setContentsMargins(0,0,0,0); top_layout.setSpacing(4)
        top_layout.addWidget(bar, 1); top_layout.addWidget(self.brand_header)
        self.setMenuWidget(top)

    @staticmethod
    def _app_icon():
        import sys
        svg = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3])) / "assets" / "ppview.svg"
        renderer = QSvgRenderer(str(svg)); pixmap = QPixmap(64,64); pixmap.fill(Qt.GlobalColor.transparent)
        from PySide6.QtGui import QPainter
        painter = QPainter(pixmap); renderer.render(painter); painter.end()
        return QIcon(pixmap)

    def _build(self):
        self.setMinimumSize(1000, 540)
        self.resize(1200, 600)
        self._install_theme()
        self._build_header()
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)
        self.toolbar = toolbar
        self.actions = {}
        self.browser_action = QAction(self); self.browser_action.setCheckable(True); self.browser_action.toggled.connect(self._toggle_browser); toolbar.addAction(self.browser_action)
        self.panel_action = QAction(self); self.panel_action.setCheckable(True); self.panel_action.setChecked(True); self.panel_action.toggled.connect(self._toggle_panel); toolbar.addAction(self.panel_action)
        toolbar.addSeparator()
        for key in ("fit_page", "fit_width", "zoom_out"):
            action = QAction(self)
            action.triggered.connect(lambda checked=False, k=key: self.set_view(k))
            toolbar.addAction(action)
            self.actions[key] = action
        self.zoom_control = ZoomControl(); self.zoom_control.zoom_requested.connect(self._set_zoom_factor); toolbar.addWidget(self.zoom_control)
        self.zoom_label = self.zoom_control.edit
        action = QAction(self); action.triggered.connect(lambda: self.set_view("zoom_in")); toolbar.addAction(action); self.actions["zoom_in"] = action
        self.prev = QPushButton(); self.prev.clicked.connect(lambda: self.change_page(-1)); toolbar.addWidget(self.prev)
        self.page_label = QLabel(); toolbar.addWidget(self.page_label)
        self.next = QPushButton(); self.next.clicked.connect(lambda: self.change_page(1)); toolbar.addWidget(self.next)
        toolbar.addSeparator()
        self.close_document_action = QAction(self); self.close_document_action.triggered.connect(self.close_selected_document); toolbar.addAction(self.close_document_action)
        self.clear_action = QAction(self); self.clear_action.triggered.connect(self.clear_all); toolbar.addAction(self.clear_action)
        self.document_combo = QComboBox(); self.document_combo.setMinimumWidth(140); self.document_combo.setMaximumWidth(230)
        self.document_combo.currentIndexChanged.connect(self._select_document); toolbar.addWidget(self.document_combo)
        toolbar.addSeparator()
        self.lang_combo = QComboBox(); self.lang_combo.setMinimumWidth(105); self.lang_combo.setMaximumWidth(145)
        self.lang_combo.currentIndexChanged.connect(self._language_changed); toolbar.addWidget(self.lang_combo)

        central = QWidget()
        central_layout = QVBoxLayout(central); central_layout.setContentsMargins(0, 0, 0, 0); central_layout.setSpacing(0)
        self.splitter = QSplitter()
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
        self.file_model = QFileSystemModel(self)
        self.file_model.setReadOnly(True)
        self.file_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.Drives | QDir.Filter.NoDotAndDotDot)
        self.file_model.setNameFilters(["*.pdf", "*.ai"])
        self.file_model.setNameFilterDisables(False)
        self.file_model.setRootPath("")
        self.file_browser = QWidget(); self.file_browser.setMinimumWidth(220)
        browser_layout = QVBoxLayout(self.file_browser); browser_layout.setContentsMargins(6, 6, 6, 6)
        self.browser_heading = QLabel(); self.browser_heading.setObjectName("panelHeading"); browser_layout.addWidget(self.browser_heading)
        self.file_tree = QTreeView(); self.file_tree.setModel(self.file_model); self.file_tree.setRootIndex(QModelIndex())
        self.file_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_tree.setUniformRowHeights(True); self.file_tree.setAnimated(False)
        self.file_tree.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.file_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.file_tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.file_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.file_tree.setColumnWidth(0, 380)
        for column in (1, 2, 3): self.file_tree.hideColumn(column)
        self.file_tree.doubleClicked.connect(self._browser_double_click)
        self.file_tree.selectionModel().currentChanged.connect(self._browser_current_changed)
        browser_layout.addWidget(self.file_tree, 1)
        self.open_selected_button = QPushButton(); self.open_selected_button.clicked.connect(self.open_selected_from_browser); browser_layout.addWidget(self.open_selected_button)
        self.file_browser.hide()
        self.splitter.addWidget(self.file_browser); self.splitter.addWidget(self.drop); self.splitter.addWidget(self.scroll)
        self.splitter.setStretchFactor(0, 0); self.splitter.setStretchFactor(1, 1); self.splitter.setStretchFactor(2, 4)
        self.panel = QWidget(); self.panel.setMinimumWidth(280); self.panel_layout = QVBoxLayout(self.panel)
        self.info_heading = QLabel(); self.info_heading.setObjectName("panelHeading"); self.panel_layout.addWidget(self.info_heading)
        self.details = {}
        for key in ("filename", "type", "size", "pages", "dimensions", "status"):
            label = QLabel(); label.setWordWrap(True); self.details[key] = label; self.panel_layout.addWidget(label)
        self.check_heading = QLabel(); self.check_heading.setObjectName("panelHeading"); self.panel_layout.addWidget(self.check_heading)
        for key in ("render", "diagnostics"):
            label = QLabel(); label.setWordWrap(True); self.details[key] = label; self.panel_layout.addWidget(label)
        self.panel_layout.addStretch()
        self.splitter.addWidget(self.panel); self.splitter.setStretchFactor(3, 0)
        self.splitter.setSizes([0, 190, 820, 280])
        self.scroll.viewport().installEventFilter(self)
        central_layout.addWidget(self.splitter, 1)
        footer = QWidget(); footer.setObjectName("footer"); footer.setFixedHeight(30); self.footer = footer
        footer_layout = QHBoxLayout(footer); footer_layout.setContentsMargins(12, 5, 12, 5); footer_layout.setSpacing(8)
        self.copyright_prefix = QLabel(); footer_layout.addWidget(self.copyright_prefix)
        self.author_link = LinkLabel("Matthieu Tuffet", "https://www.matthieutuffet.com/")
        footer_layout.addWidget(self.author_link); footer_layout.addStretch(1)
        self.github_link = LinkLabel("GitHub", "https://github.com/papagori/PPView")
        footer_layout.addWidget(self.github_link)
        self.footer_separator = QLabel("·"); footer_layout.addWidget(self.footer_separator)
        self.license_link = LinkLabel("GPLv3", "https://github.com/papagori/PPView/blob/main/LICENSE")
        footer_layout.addWidget(self.license_link)
        footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.statusBar().addWidget(footer, 1)
        self.statusBar().setMinimumHeight(36)
        self.statusBar().show()
        self.setCentralWidget(central)
        for widget in (self, central, self.splitter, self.drop, self.scroll, self.scroll.viewport(),
                       self.preview, self.file_browser, self.file_tree, self.panel):
            widget.setAcceptDrops(True)
        menu = self.menu_bar.addMenu(""); self.file_menu = menu
        self.open_action = QAction(self); self.open_action.setShortcut(QKeySequence.StandardKey.Open); self.open_action.triggered.connect(self.choose_files); menu.addAction(self.open_action)
        self.open_folder_action = QAction(self); self.open_folder_action.triggered.connect(self.choose_folder); menu.addAction(self.open_folder_action)
        menu.addSeparator(); menu.addAction(self.close_document_action); menu.addAction(self.clear_action)
        self.exit_action = QAction(self); self.exit_action.triggered.connect(self.close); menu.addAction(self.exit_action)
        self.help_menu = self.menu_bar.addMenu(""); self.about_action = QAction(self); self.about_action.triggered.connect(self.about); self.help_menu.addAction(self.about_action)
        self.setWindowIcon(self._app_icon())
        self._document_state(None)
        self._update_document_controls()

    def _translate(self):
        t = self.t
        self.setWindowTitle(t["app"]); self.toolbar.setWindowTitle(t["app"])
        for key, action in self.actions.items():
            action.setText(t[key]); action.setToolTip(t[f"tip_{key}"])
        self.browser_action.setText(t["file_browser_short"]); self.browser_action.setToolTip(t["tip_file_browser"])
        self.panel_action.setText(t["information_short"]); self.panel_action.setToolTip(t["tip_information"])
        self.actions["fit_page"].setText(t["fit_page_short"]); self.actions["fit_width"].setText(t["fit_width_short"])
        self.close_document_action.setText(t["close_short"]); self.clear_action.setText(t["clear_short"])
        self.close_document_action.setToolTip(t["tip_close"]); self.clear_action.setToolTip(t["tip_clear"])
        self.prev.setText("‹"); self.prev.setToolTip(t["previous"]); self.next.setText("›"); self.next.setToolTip(t["next"])
        self.drop_label.setText(t["drop"]); self.hint_label.setText(t["open_hint"])
        self.browser_heading.setText(t["file_browser"]); self.open_selected_button.setText(t["open_selected"])
        self.brand_slogan.setText(t["title_suffix"])
        self.zoom_control.setToolTip(t["tip_zoom"]); self.zoom_control.edit.setToolTip(t["tip_zoom"])
        self.zoom_control.popup.setToolTip(t["tip_zoom"])
        self.copyright_prefix.setText(t["copyright"])
        self.info_heading.setText(t["document_information"]); self.check_heading.setText(t["preflight_checks"])
        self.file_menu.setTitle(t["file"]); self.open_action.setText(t["open"] + "\t" + t["shortcut"])
        self.open_folder_action.setText(t["open_folder"]); self.exit_action.setText(t["exit"])
        self.open_action.setToolTip(t["open"] + " (" + t["shortcut"] + ")")
        self.open_folder_action.setToolTip(t["open_folder"]); self.exit_action.setToolTip(t["exit"])
        self.document_combo.setToolTip(t["file_browser"])
        self.help_menu.setTitle(t["help"]); self.about_action.setText(t["about"])
        previous = self.lang_combo.blockSignals(True); self.lang_combo.clear()
        for label, code in ((t["english"], "en"), (t["japanese"], "ja"), (t["french"], "fr")): self.lang_combo.addItem(label, code)
        self.lang_combo.setCurrentIndex({"en": 0, "ja": 1, "fr": 2}[self.language]); self.lang_combo.setToolTip(t["tip_language"]); self.lang_combo.blockSignals(previous)
        self._document_state(self.info); self._update_document_controls()

    def _language_changed(self, index):
        if index < 0: return
        language = self.lang_combo.itemData(index)
        if language and language != self.language:
            self.language = language; self.settings.setValue("language", language)
            self.t = strings(language); self.statusBar().clearMessage(); self._translate()

    def _toggle_panel(self, visible):
        self.panel.setVisible(visible)
        if self.info and self.fit_mode in ("page", "width"): self._render()

    def _toggle_browser(self, visible):
        if visible:
            width = max(220, min(self._preferred_browser_width, max(220, self.splitter.width() - 520)))
            sizes = self.splitter.sizes()
            if sizes and sizes[0] < 220:
                remaining = max(1, sum(sizes) - width)
                right = sizes[3] if len(sizes) > 3 else 0
                preview = max(1, remaining - right - 120)
                drop = max(1, remaining - right - preview)
                self.splitter.setSizes([width, drop, preview, right])
        self.file_browser.setVisible(visible)
        if self.info and self.fit_mode in ("page", "width"): self._render()

    def _splitter_moved(self, _position, _index):
        if self.file_browser.isVisible():
            width = self.splitter.sizes()[0]
            if width >= 180:
                self._preferred_browser_width = width
                self.settings.setValue("browser_width", width)

    def _drop_files(self, paths):
        accepted = [p for p in paths if Path(p).suffix.lower() in (".pdf", ".ai")]
        unsupported = [p for p in paths if p not in accepted]
        if accepted: self.open_files(accepted)
        if unsupported:
            self.statusBar().showMessage(self.t["unsupported_drop"].format(count=len(unsupported)), 8000)

    def _browser_current_changed(self, current, _previous):
        if not current.isValid(): return
        path = Path(self.file_model.filePath(current))
        directory = path if self.file_model.isDir(current) else path.parent
        if directory.is_dir(): self.settings.setValue("last_browsed_directory", str(directory))

    def _restore_browser_directory(self):
        remembered = self.settings.value("last_browsed_directory", "")
        path = Path(remembered) if remembered else None
        if path and path.is_dir(): self.browse_directory(path)

    def browse_directory(self, path):
        directory = Path(path).expanduser().resolve()
        if not directory.is_dir(): return False
        index = self.file_model.index(str(directory))
        if not index.isValid(): return False
        ancestors = []
        current = index.parent()
        while current.isValid():
            ancestors.append(current)
            current = current.parent()
        for ancestor in reversed(ancestors): self.file_tree.expand(ancestor)
        self.file_tree.expand(index)
        self.file_tree.setCurrentIndex(index)
        self.file_tree.scrollTo(index)
        self.settings.setValue("last_browsed_directory", str(directory))
        return True

    def _browser_double_click(self, index):
        path = Path(self.file_model.filePath(index))
        if self.file_model.isDir(index):
            self.settings.setValue("last_browsed_directory", str(path))
        elif path.suffix.lower() in (".pdf", ".ai"):
            self.open_file(str(path))

    def open_selected_from_browser(self):
        paths = [self.file_model.filePath(index) for index in self.file_tree.selectionModel().selectedRows(0)
                 if not self.file_model.isDir(index)]
        supported = [p for p in paths if Path(p).suffix.lower() in (".pdf", ".ai")]
        if supported: self.open_files(supported)
        if len(supported) < len(paths):
            self.statusBar().showMessage(self.t["unsupported_selected"], 8000)

    def choose_folder(self):
        start = self.settings.value("last_browsed_directory", str(Path.home()))
        directory = QFileDialog.getExistingDirectory(self, self.t["choose_folder"], start)
        if directory:
            self.browse_directory(directory)
            self.browser_action.setChecked(True)

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
        if self.file_browser.isVisible(): self._highlight_browser_path(self.path)
        self._refresh_document_combo(); self._update_document_controls()

    def _highlight_browser_path(self, path):
        if not path: return
        index = self.file_model.index(str(path))
        if not index.isValid(): return
        ancestors = []
        parent = index.parent()
        while parent.isValid():
            ancestors.append(parent); parent = parent.parent()
        for ancestor in reversed(ancestors): self.file_tree.expand(ancestor)
        self.file_tree.setCurrentIndex(index)
        self.file_tree.scrollTo(index)

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
        if self.file_browser.isVisible(): self._highlight_browser_path(info.path)
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
        elif key == "fit_width": self.fit_mode = "width"
        else: self.fit_mode = "page"
        self._render()

    def _set_zoom_factor(self, zoom):
        self.fit_mode = "manual"
        self.zoom = max(0.05, min(8.0, float(zoom)))
        self._pending_zoom_anchor = None
        self.zoom_control.set_zoom(self.zoom)
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
        self.zoom_control.set_zoom(zoom)
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

    def closeEvent(self, event):
        app = QApplication.instance()
        if app and hasattr(self, "_drop_filter"):
            app.removeEventFilter(self._drop_filter)
        super().closeEvent(event)

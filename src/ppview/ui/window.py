from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (QObject, QRunnable, QSettings, Qt, QThreadPool, Signal,
    QPoint, QEvent, QDir, QUrl, QModelIndex, QSize, QTimer)
from PySide6.QtGui import (QAction, QKeySequence, QPixmap, QDesktopServices, QIcon,
                           QPalette, QColor, QPainter, QPen)
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QToolBar, QVBoxLayout, QWidget, QToolButton, QFileSystemModel, QTreeView,
    QAbstractItemView, QLineEdit, QSlider, QMenu, QWidgetAction, QStyle, QHeaderView,
    QTreeWidget, QTreeWidgetItem, QDialog, QDialogButtonBox, QFormLayout)
from PySide6.QtSvg import QSvgRenderer

from ppview.core.document import (DocumentError, DocumentInfo, MAX_RENDER_DIMENSION,
    MAX_RENDER_PIXELS, inspect_file, render_page_result, release_document, validate_rendering)
from ppview.i18n.strings import initial_language, strings
from ppview import __version__
from ppview.build_info import build_commit
from ppview.validation import CheckResult, PreflightReport, PreflightSettings, Status, run_preflight
from ppview.ui.help_dialogs import AboutDialog, UserGuideDialog


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


class LinkLabel(QPushButton):
    activated = Signal(str)

    def __init__(self, text: str, url: str, parent=None):
        super().__init__(text, parent)
        self.url = url
        self.setObjectName("footerLink")
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(url)
        self.clicked.connect(self.open_link)

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
        self._image_highlight = None
        self._image_highlight_tooltip = ""

    def set_image_highlight(self, normalized_box=None, tooltip=""):
        self._image_highlight = tuple(normalized_box) if normalized_box else None
        self._image_highlight_tooltip = tooltip or ""
        self.setToolTip(self._image_highlight_tooltip)
        self.update()

    def image_highlight_rect(self):
        if not self._image_highlight:
            return None
        left, top, right, bottom = self._image_highlight
        bounds = self.contentsRect()
        left, right = max(0.0, min(1.0, left)), max(0.0, min(1.0, right))
        top, bottom = max(0.0, min(1.0, top)), max(0.0, min(1.0, bottom))
        if right <= left or bottom <= top:
            return None
        return (bounds.left() + left * bounds.width(),
                bounds.top() + top * bounds.height(),
                bounds.left() + right * bounds.width(),
                bounds.top() + bottom * bounds.height())

    def paintEvent(self, event):
        super().paintEvent(event)
        rect = self.image_highlight_rect()
        if rect is None:
            return
        left, top, right, bottom = rect
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(self.contentsRect())
        painter.setPen(QPen(QColor(255, 174, 66), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(QColor(255, 174, 66, 35))
        painter.drawRect(left + 1, top + 1, max(0, right - left - 2),
                         max(0, bottom - top - 2))
        painter.end()

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
        self.preflight_reports: dict[tuple[str, PreflightSettings], PreflightReport] = {}
        self.preflight_in_flight: set[tuple[str, int | None, PreflightSettings]] = set()
        self.document_generations: dict[str, int] = {}
        self._next_document_generation = 0
        self.info: DocumentInfo | None = None
        self.path: Path | None = None
        self.page = 0
        self.zoom = 1.0
        self.fit_mode = "page"
        self.token = 0
        self.render_serial = 0
        self._pending_zoom_anchor = None
        self._render_busy = False
        self._render_pending = False
        self._render_active_serial = None
        self._render_requests = 0
        self._pdfium_render_started = 0
        self._render_completed = 0
        self._render_limited = False
        self._final_pixmap = None
        self._final_zoom = 1.0
        self._debounce_ms = 150
        self._zoom_timer = QTimer(self); self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(self._debounce_ms); self._zoom_timer.timeout.connect(self._render)
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(2)
        self._tasks = set()
        self.settings = QSettings("papagori", "PPView")
        self._preferred_browser_width = int(self.settings.value("browser_width", 300))
        self._preflight_settings = self._read_preflight_settings()
        self._build()
        self._drop_filter = WindowDropFilter(self)
        QApplication.instance().installEventFilter(self._drop_filter)
        self._translate()
        if initial_file: self.open_files([initial_file])

    @staticmethod
    def _canonical(path: str | Path) -> str:
        return str(Path(path).expanduser().resolve()).casefold()

    def _read_preflight_settings(self) -> PreflightSettings:
        try:
            resolution = int(self.settings.value("preflight/target_image_ppi", 300))
            bleed = float(self.settings.value("preflight/minimum_bleed_mm", 3))
            return PreflightSettings(resolution, bleed)
        except (TypeError, ValueError):
            return PreflightSettings()

    def _install_theme(self):
        app = QApplication.instance()
        palette = QPalette()
        for role, color in ((QPalette.ColorRole.Window,"#0b1424"),(QPalette.ColorRole.WindowText,"#e6eef8"),(QPalette.ColorRole.Base,"#101e32"),(QPalette.ColorRole.AlternateBase,"#162741"),(QPalette.ColorRole.Text,"#e6eef8"),(QPalette.ColorRole.Button,"#1a2e4b"),(QPalette.ColorRole.ButtonText,"#e6eef8"),(QPalette.ColorRole.Highlight,"#1688e8"),(QPalette.ColorRole.HighlightedText,"#ffffff"),(QPalette.ColorRole.Link,"#55baff")):
            palette.setColor(role, QColor(color))
        app.setPalette(palette)
        self.setStyleSheet("""
            QWidget { color:#e6eef8; background:#0b1424; }
            QMenuBar,QMenu,QToolBar { background:#101e32; border:0; }
            QMenu { background:#101e32; border:1px solid #355273; padding:5px; }
            QMenu::item { padding:7px 14px; }
            QMenuBar::item { padding:5px 9px; } QMenuBar::item:selected,QMenu::item:selected { background:#1d385c; }
            QToolBar { spacing:2px; padding:3px 5px; border-bottom:1px solid #263c59; }
            QToolBar#mainToolbar QToolButton { padding:2px 3px; }
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
            QToolBar#mainToolbar { border-bottom:1px solid #263c59; padding:3px 9px; }
            QFrame#toolbarPalette { background:#152943; border:1px solid #294867; border-radius:7px; }
            QFrame#toolbarPalette QWidget { background:transparent; }
            QFrame#toolbarPalette QToolButton,QFrame#toolbarPalette QPushButton { background:#1a2e4b; }
            QWidget#zoomControl { background:transparent; }
            QLabel#brandName { color:#eff7ff; font-size:15pt; font-weight:700; background:transparent; }
            QLabel#brandSlogan { color:#a8c0d9; font-size:8pt; background:transparent; }
            QWidget#branding { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #101e32,stop:0.58 #173453,stop:1 #20517b); border-bottom:1px solid #294867; }
            QStatusBar { background:#101e32; border:0; color:#bdcadd; }
            QStatusBar::item { border:0; }
            QWidget#footer { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #101e32,stop:0.55 #142943,stop:1 #1b4267); color:#bdcadd; font-size:9pt; }
            QPushButton#footerLink { color:#d7efff; background:rgba(86,189,255,0.10); border:1px solid rgba(103,197,255,0.28); border-radius:8px; padding:2px 9px; }
            QPushButton#footerLink:hover { color:#ffffff; background:rgba(86,189,255,0.20); border-color:#67c5ff; }
            QPushButton#footerLink:pressed { color:#ffffff; background:#155a91; border-color:#38aaff; }
            QToolTip { color:#f2f7fc; background:#1a2e4b; border:1px solid #4b7198; }
        """)

    def _build_header(self):
        brand = QWidget(); brand.setObjectName("branding")
        row = QHBoxLayout(brand); row.setContentsMargins(14,2,14,2); row.setSpacing(9)
        icon = QLabel(); icon.setPixmap(self._app_icon().pixmap(34,34)); icon.setFixedSize(34,34); row.addWidget(icon)
        label_box = QWidget(); label_box.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        labels = QVBoxLayout(label_box); labels.setContentsMargins(0,0,0,0); labels.setSpacing(0)
        self.brand_name = QLabel("PPView"); self.brand_name.setObjectName("brandName")
        self.brand_slogan = QLabel(); self.brand_slogan.setObjectName("brandSlogan")
        labels.addWidget(self.brand_name); labels.addWidget(self.brand_slogan); row.addWidget(label_box); row.addStretch(1)
        self.brand_labels = label_box
        self.brand_header = brand
        self.setMenuWidget(self.brand_header)

    def _action_button(self, action):
        button = QToolButton(); button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setDefaultAction(action)
        return button

    @staticmethod
    def _toolbar_palette(name: str):
        palette = QFrame()
        palette.setObjectName("toolbarPalette")
        palette.setProperty("paletteName", name)
        layout = QHBoxLayout(palette)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(3)
        return palette, layout

    @staticmethod
    def _app_icon():
        import sys
        svg = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3])) / "assets" / "logo" / "ppview-icon.svg"
        return QIcon(str(svg))

    def _build(self):
        self.setMinimumSize(760, 540)
        self.resize(1200, 600)
        self._install_theme()
        self._build_header()
        toolbar = QToolBar()
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.addToolBar(toolbar)
        self.toolbar = toolbar
        self.toolbar_contents = QWidget(); self.toolbar_contents.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.toolbar_layout = QHBoxLayout(self.toolbar_contents); self.toolbar_layout.setContentsMargins(0,0,0,0); self.toolbar_layout.setSpacing(2)
        self.groups_scroll = QScrollArea(); self.groups_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.groups_scroll.setWidgetResizable(False); self.groups_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.groups_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.groups_widget = QWidget(); self.group_toolbar_layout = QHBoxLayout(self.groups_widget)
        self.group_toolbar_layout.setContentsMargins(0,0,0,0); self.group_toolbar_layout.setSpacing(8)
        self.palette_a, self.palette_a_layout = self._toolbar_palette("menus")
        self.palette_b, self.preview_toolbar_layout = self._toolbar_palette("preview")
        self.palette_c, self.document_toolbar_layout = self._toolbar_palette("documents")
        for palette in (self.palette_a, self.palette_b, self.palette_c):
            self.group_toolbar_layout.addWidget(palette)
        self.group_toolbar_layout.addStretch(1)
        self.groups_scroll.setWidget(self.groups_widget); self.toolbar_layout.addWidget(self.groups_scroll, 1)
        toolbar.addWidget(self.toolbar_contents)
        self.actions = {}
        self.file_menu = QMenu(self)
        self.file_menu_button = QToolButton(); self.file_menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.file_menu_button.setMenu(self.file_menu); self.palette_a_layout.addWidget(self.file_menu_button)
        self.open_action = QAction(self); self.open_action.setShortcut(QKeySequence.StandardKey.Open); self.open_action.triggered.connect(self.choose_files); self.file_menu.addAction(self.open_action)
        self.open_folder_action = QAction(self); self.open_folder_action.triggered.connect(self.choose_folder); self.file_menu.addAction(self.open_folder_action)
        self.settings_action = QAction(self); self.settings_action.triggered.connect(self.open_preflight_settings); self.file_menu.addAction(self.settings_action)
        self.file_menu.addSeparator()
        self.browser_action = QAction(self); self.browser_action.setCheckable(True); self.browser_action.toggled.connect(self._toggle_browser); self.palette_a_layout.addWidget(self._action_button(self.browser_action))
        self.panel_action = QAction(self); self.panel_action.setCheckable(True); self.panel_action.setChecked(True); self.panel_action.toggled.connect(self._toggle_panel); self.palette_a_layout.addWidget(self._action_button(self.panel_action))
        self.help_menu = QMenu(self)
        self.help_menu_button = QToolButton(); self.help_menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup); self.help_menu_button.setMenu(self.help_menu); self.palette_a_layout.addWidget(self.help_menu_button)
        self.guide_action = QAction(self); self.guide_action.triggered.connect(self.user_guide); self.help_menu.addAction(self.guide_action)
        self.about_action = QAction(self); self.about_action.triggered.connect(self.about); self.help_menu.addAction(self.about_action)
        for key in ("fit_page", "fit_width", "zoom_out"):
            action = QAction(self)
            action.triggered.connect(lambda checked=False, k=key: self.set_view(k))
            self.preview_toolbar_layout.addWidget(self._action_button(action))
            self.actions[key] = action
        self.zoom_control = ZoomControl(); self.zoom_control.zoom_requested.connect(self._set_zoom_factor); self.preview_toolbar_layout.addWidget(self.zoom_control)
        self.zoom_label = self.zoom_control.edit
        action = QAction(self); action.triggered.connect(lambda: self.set_view("zoom_in")); self.preview_toolbar_layout.addWidget(self._action_button(action)); self.actions["zoom_in"] = action
        self.prev = QPushButton(); self.prev.clicked.connect(lambda: self.change_page(-1)); self.preview_toolbar_layout.addWidget(self.prev)
        self.page_label = QLabel(); self.preview_toolbar_layout.addWidget(self.page_label)
        self.next = QPushButton(); self.next.clicked.connect(lambda: self.change_page(1)); self.preview_toolbar_layout.addWidget(self.next)
        self.close_document_action = QAction(self); self.close_document_action.triggered.connect(self.close_selected_document); self.document_toolbar_layout.addWidget(self._action_button(self.close_document_action))
        self.clear_action = QAction(self); self.clear_action.triggered.connect(self.clear_all); self.document_toolbar_layout.addWidget(self._action_button(self.clear_action))
        self.document_combo = QComboBox(); self.document_combo.setMinimumWidth(110); self.document_combo.setMaximumWidth(160)
        self.document_combo.currentIndexChanged.connect(self._select_document); self.document_toolbar_layout.addWidget(self.document_combo)
        self.language_palette, language_layout = self._toolbar_palette("language")
        self.language_palette.setObjectName("languagePalette")
        self.language_palette.setStyleSheet("QFrame#languagePalette { background:#152943; border:1px solid #294867; border-radius:7px; }")
        self.lang_combo = QComboBox(); self.lang_combo.setMinimumWidth(95); self.lang_combo.setMaximumWidth(120)
        self.lang_combo.currentIndexChanged.connect(self._language_changed); language_layout.addWidget(self.lang_combo)
        self.toolbar_layout.addWidget(self.language_palette)
        self.toolbar_spacer = self.toolbar_layout

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
        self.check_tree = QTreeWidget(); self.check_tree.setHeaderHidden(True)
        self.check_tree.setRootIsDecorated(True); self.check_tree.setUniformRowHeights(True)
        self.check_tree.setMinimumHeight(150); self.check_tree.itemClicked.connect(self._activate_check_item)
        self.panel_layout.addWidget(self.check_tree, 1)
        self.panel_layout.addStretch()
        self.splitter.addWidget(self.panel); self.splitter.setStretchFactor(3, 0)
        self.splitter.setSizes([0, 190, 820, 280])
        self.scroll.viewport().installEventFilter(self)
        central_layout.addWidget(self.splitter, 1)
        self.statusBar().setSizeGripEnabled(False)
        footer = QWidget(); footer.setObjectName("footer"); footer.setFixedHeight(34); self.footer = footer
        footer_layout = QHBoxLayout(footer); footer_layout.setContentsMargins(14, 3, 14, 3); footer_layout.setSpacing(7)
        self.copyright_prefix = QLabel(); footer_layout.addWidget(self.copyright_prefix)
        self.author_link = LinkLabel("Matthieu Tuffet", "https://www.matthieutuffet.com/")
        footer_layout.addWidget(self.author_link)
        self.version_label = QLabel(); footer_layout.addWidget(self.version_label)
        footer_layout.addStretch(1)
        self.github_link = LinkLabel("GitHub", "https://github.com/papagori/PPView")
        footer_layout.addWidget(self.github_link)
        self.license_link = LinkLabel("GPLv3", "https://github.com/papagori/PPView/blob/main/LICENSE")
        footer_layout.addWidget(self.license_link)
        footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.statusBar().addWidget(footer, 1)
        self.statusBar().setMinimumHeight(34)
        self.statusBar().show()
        self.setCentralWidget(central)
        for widget in (self, central, self.splitter, self.drop, self.scroll, self.scroll.viewport(),
                       self.preview, self.file_browser, self.file_tree, self.panel):
            widget.setAcceptDrops(True)
        self.file_menu.addAction(self.close_document_action); self.file_menu.addAction(self.clear_action)
        self.exit_action = QAction(self); self.exit_action.triggered.connect(self.close); self.file_menu.addAction(self.exit_action)
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
        self.brand_name.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.brand_slogan.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.brand_name.adjustSize(); self.brand_slogan.adjustSize()
        self.brand_labels.setFixedWidth(max(self.brand_name.sizeHint().width(), self.brand_slogan.sizeHint().width()))
        self.zoom_control.setToolTip(t["tip_zoom"]); self.zoom_control.edit.setToolTip(t["tip_zoom"])
        self.zoom_control.popup.setToolTip(t["tip_zoom"])
        self.copyright_prefix.setText(t["copyright"])
        self.version_label.setText(f"PPView v{__version__}")
        self.info_heading.setText(t["document_information"]); self.check_heading.setText(t["preflight_checks"])
        self.file_menu_button.setText(t["file"]); self.file_menu_button.setToolTip(t["file"])
        self.help_menu_button.setText(t["help"]); self.help_menu_button.setToolTip(t["help"])
        self.file_menu.setTitle(t["file"]); self.open_action.setText(t["open"])
        self.open_folder_action.setText(t["open_folder"]); self.exit_action.setText(t["exit"])
        self.settings_action.setText(t["settings_menu"]); self.settings_action.setToolTip(t["settings_menu"])
        self.open_action.setToolTip(t["open"])
        self.open_folder_action.setToolTip(t["open_folder"]); self.exit_action.setToolTip(t["exit"])
        self._size_file_menu_for_actions()
        self.document_combo.setToolTip(t["tip_file_browser"])
        self.help_menu.setTitle(t["help"]); self.about_action.setText(t["about"]); self.guide_action.setText(t["guide"])
        previous = self.lang_combo.blockSignals(True); self.lang_combo.clear()
        for label, code in ((t["english"], "en"), (t["japanese"], "ja"), (t["french"], "fr")): self.lang_combo.addItem(label, code)
        self.lang_combo.setCurrentIndex({"en": 0, "ja": 1, "fr": 2}[self.language]); self.lang_combo.setToolTip(t["tip_language"]); self.lang_combo.blockSignals(previous)
        if self.isVisible(): self._update_toolbar_group_width()
        self._document_state(self.info); self._update_document_controls()
        self._refresh_preflight_language()

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
                self._next_document_generation += 1
                self.document_generations[key] = self._next_document_generation
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
        self._zoom_timer.stop(); self._render_pending = False
        self.token += 1; self.render_serial += 1
        self._highlight_page = None
        self.preview.set_image_highlight()
        self.path = self.document_paths.get(key, Path(key)); self.info = self.documents.get(key); self.page = 0
        self.zoom = 1.0; self.fit_mode = "page"
        self._final_pixmap = None
        self._render_limited = False
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
        release_document(self.document_paths.get(key, Path(key)))
        self.documents.pop(key); self._refresh_document_combo()
        self.document_paths.pop(key, None)
        self.document_generations.pop(key, None)
        self.validation.pop(key, None)
        self.preflight_reports = {entry: report for entry, report in self.preflight_reports.items() if entry[0] != key}
        if key != (self._canonical(self.path) if self.path else None): return
        self.info = None; self.preview.clear(); self.drop.show(); self._document_state(None, error=reason)
        self.preview.set_image_highlight()
        self.path = None; self._update_document_controls()

    def close_selected_document(self):
        if not self.path: return
        key = self._canonical(self.path); keys = list(self.documents)
        index = keys.index(key); self.documents.pop(key, None); closed_path = self.document_paths.pop(key, Path(key)); self.validation.pop(key, None)
        self.document_generations.pop(key, None)
        release_document(closed_path)
        self.preflight_reports = {entry: report for entry, report in self.preflight_reports.items() if entry[0] != key}
        if self.documents:
            remaining = list(self.documents)
            target = remaining[min(index, len(remaining) - 1)]
            self._select_path(target)
        else:
            self.token += 1; self.render_serial += 1; self.path = None; self.info = None; self.page = 0
            self.preview.set_image_highlight()
            self._final_pixmap = None; self._render_limited = False
            self.preview.clear(); self.preview.hide(); self.drop.show(); self._document_state(None)
            self._refresh_document_combo(); self._update_document_controls()

    def clear_all(self):
        self._zoom_timer.stop(); self._render_pending = False
        self.token += 1; self.render_serial += 1
        self.preview.set_image_highlight()
        for path in tuple(self.document_paths.values()): release_document(path)
        self.documents.clear(); self.document_paths.clear(); self.document_generations.clear(); self.validation.clear(); self.preflight_reports.clear(); self.path = None; self.info = None; self.page = 0
        self._final_pixmap = None
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
        selected = self._canonical(self.path)
        settings = self._preflight_settings
        report = self.preflight_reports.get((key, settings))
        if report is not None:
            self._preflight_display(report)
            render = next((r for r in report.results if r.check_id == "document.render"), None)
            self.validation[key] = "passed" if render and render.status is Status.PASSED else "failed"
            self._validation_display(self.validation[key])
        else:
            self.details["diagnostics"].setText(f"{self.t['diagnostics']}: {self.t['analysis_running']}")
            self.check_tree.clear()
            generation = self.document_generations.get(key)
            task_key = (key, generation, settings)
            if task_key not in self.preflight_in_flight:
                self.preflight_in_flight.add(task_key)
                task = Task(self.token, lambda p=self.info.path, s=settings: run_preflight(p, s))
                task.signals.result.connect(lambda _tok, result, k=key, g=generation, s=settings:
                                            self._preflight_done_for(k, g, s, result))
                task.signals.failed.connect(lambda _tok, err, k=key, g=generation, s=settings:
                                            self._preflight_failed_for(k, g, s, err))
                self._start_task(task)
            self.validation[key] = "checking"
            self._validation_display("checking")

    def _start_task(self, task, priority=0):
        # Keep the Python QRunnable wrapper alive until its queued signals have
        # reached the GUI thread. This matters for short-lived inspect tasks.
        self._tasks.add(task)
        task.signals.finished.connect(lambda _token, current=task: self._tasks.discard(current))
        self.pool.start(task, priority)

    def _validation_display(self, status):
        if not self.info: return
        if self._render_limited:
            self.details["render"].setText(f"{self.t['render']}: {self.t.get('render_limited', 'Resolution limited')}")
            return
        self.details["render"].setText(f"{self.t['render']}: {self.t[status]}")

    def _validation_done_for(self, key, token):
        if key not in self.documents: return
        self.validation[key] = "passed"
        if token == self.token and key == (self._canonical(self.path) if self.path else None): self._validation_display("passed")

    def _validation_failed_for(self, key, token):
        if key not in self.documents: return
        self.validation[key] = "failed"
        if token == self.token and key == (self._canonical(self.path) if self.path else None): self._validation_display("failed")

    def _preflight_done_for(self, key, generation, settings, report):
        self.preflight_in_flight.discard((key, generation, settings))
        if key not in self.documents or self.document_generations.get(key) != generation:
            return
        self.preflight_reports[(key, settings)] = report
        render = next((r for r in report.results if r.check_id == "document.render"), None)
        self.validation[key] = "passed" if render and render.status is Status.PASSED else "failed"
        if (key == (self._canonical(self.path) if self.path else None)
                and settings == self._preflight_settings):
            self._preflight_display(report)
            self._validation_display(self.validation[key])

    def _preflight_failed_for(self, key, generation, settings, _error):
        self.preflight_in_flight.discard((key, generation, settings))
        if key not in self.documents or self.document_generations.get(key) != generation:
            return
        failure = tuple(CheckResult(f"{category}.failure", category, Status.UNKNOWN,
                                    f"{category}.unavailable", severity="unknown")
                        for category in ("document", "images", "fonts", "geometry", "colors"))
        report = PreflightReport(failure, None, None, None)
        self.preflight_reports[(key, settings)] = report
        if key == (self._canonical(self.path) if self.path else None) and settings == self._preflight_settings:
            self._preflight_display(report)
            self.details["render"].setText(f"{self.t['render']}: {self.t['status_unknown']}")

    def _preflight_display(self, report: PreflightReport):
        self.check_tree.clear()
        rendering = next((item for item in report.results if item.check_id == "document.render"), None)
        render_label = self.t["status_unknown"]
        if rendering is not None:
            render_label = {Status.PASSED: self.t["passed"], Status.WARNING: self.t["status_warning"],
                            Status.ERROR: self.t["failed"], Status.UNKNOWN: self.t["status_unknown"]}[rendering.status]
        self.details["render"].setText(f"{self.t['render']}: {render_label}")
        categories = ("document", "images", "fonts", "geometry", "colors")
        status_keys = {Status.PASSED: "status_passed", Status.WARNING: "status_warning",
                       Status.ERROR: "status_error", Status.UNKNOWN: "status_unknown"}
        colors = {Status.PASSED: "#66d68a", Status.WARNING: "#ffd166",
                  Status.ERROR: "#ff7272", Status.UNKNOWN: "#a8b6c8"}
        category_keys = {"document": "check_document", "images": "check_images",
                         "fonts": "check_fonts", "geometry": "check_geometry", "colors": "check_colors"}
        for category in categories:
            findings = [result for result in report.results if result.category == category]
            counts = {status: sum(item.status is status for item in findings) for status in Status}
            group = QTreeWidgetItem(self.check_tree)
            group.setText(0, f"{self.t[category_keys[category]]}  ·  "
                          f"{counts[Status.PASSED]} ✓  {counts[Status.WARNING]} !  "
                          f"{counts[Status.ERROR]} ×  {counts[Status.UNKNOWN]} ?")
            group.setForeground(0, QColor("#91a9c3"))
            group.setExpanded(True)
            image_rows = {}
            for result in findings:
                message = self._preflight_message(result)
                status_text = self.t[status_keys[result.status]]
                if result.severity == "high": status_text = f"{self.t['priority_high']} · {status_text}"
                row_color = "#ffad66" if result.severity == "high" else colors[result.status]
                parent_id = result.details.get("parent_id")
                if category == "images" and parent_id:
                    row = image_rows.get(parent_id)
                    if row is None:
                        row = QTreeWidgetItem(group)
                        row.setText(0, message)
                        row.setExpanded(True)
                        image_rows[parent_id] = row
                    child = QTreeWidgetItem(row)
                    child.setText(0, f"{status_text} — {message}")
                    child.setForeground(0, QColor(row_color))
                    child.setToolTip(0, message)
                    child.setData(0, Qt.ItemDataRole.UserRole, result)
                    continue
                if category == "images" and result.check_id.startswith("image.placement."):
                    label = self.t["image.placement_label"].format(
                        placement_index=result.details["placement_index"], page=result.page or 0)
                    row = QTreeWidgetItem(group)
                    row.setText(0, f"{label} · {status_text} — {message}")
                    row.setForeground(0, QColor(row_color))
                    row.setData(0, Qt.ItemDataRole.UserRole, result)
                    image_rows[result.check_id] = row
                    summary = self._preflight_details(result)
                    tooltip = message + ("\n" + summary if summary else "")
                    row.setToolTip(0, tooltip)
                    if summary:
                        detail_item = QTreeWidgetItem(row)
                        detail_item.setText(0, f"{self.t['details']}: {summary}")
                        detail_item.setToolTip(0, summary)
                        detail_item.setForeground(0, QColor("#a8b6c8"))
                    row.setExpanded(False)
                    continue
                row = QTreeWidgetItem(group)
                row.setText(0, f"{status_text} — {message}")
                row.setForeground(0, QColor(row_color))
                row.setToolTip(0, message)
                row.setData(0, Qt.ItemDataRole.UserRole, result)
                details = self._preflight_details(result)
                if details:
                    detail_item = QTreeWidgetItem(row)
                    detail_item.setText(0, f"{self.t['details']}: {details}")
                    detail_item.setToolTip(0, details)
                    detail_item.setForeground(0, QColor("#a8b6c8"))
        self.details["diagnostics"].setText(self._preflight_summary(report))

    def _preflight_message(self, result: CheckResult) -> str:
        template = self.t.get(result.message_id, self.t["check_unavailable"])
        values = dict(result.measurements)
        if result.page is not None: values["page"] = result.page
        values.setdefault("count", 0)
        try:
            return template.format(**values)
        except (KeyError, ValueError, TypeError):
            return template

    def _preflight_details(self, result: CheckResult) -> str:
        entries = []
        labels = {
            "width_px": "measure_width_px", "height_px": "measure_height_px",
            "bits_per_component": "measure_bit_depth", "color_space": "measure_color_space",
            "placement_width_mm": "measure_placement_width",
            "placement_height_mm": "measure_placement_height",
            "stream_bytes": "measure_stream_bytes",
            "ppi_x": "measure_ppi_x", "ppi_y": "measure_ppi_y",
            "effective_ppi": "measure_effective_ppi", "target_ppi": "measure_target_ppi",
            "name": "measure_font", "subtype": "measure_font_type", "count": "measure_count",
            "minimum_mm": "measure_min_bleed", "target_mm": "measure_target_bleed",
            "left_mm": "measure_left", "right_mm": "measure_right",
            "top_mm": "measure_top", "bottom_mm": "measure_bottom",
            "media_width_mm": "measure_media_width", "media_height_mm": "measure_media_height",
            "crop_width_mm": "measure_crop_width", "crop_height_mm": "measure_crop_height",
            "rotation": "measure_rotation",
        }
        for name, value in result.measurements.items():
            if value is None:
                continue
            if name.endswith("_pt") or name.endswith("_x0") or name.endswith("_y0") or name.endswith("_x1") or name.endswith("_y1"):
                continue
            label = self.t.get(labels.get(name, "measure_" + name), name.replace("_", " "))
            if isinstance(value, float):
                value_text = f"{value:.1f}"
            else:
                value_text = str(value)
            if name.endswith("_mm") or name in ("minimum_mm", "target_mm", "left_mm", "right_mm", "top_mm", "bottom_mm"):
                value_text += " mm"
            elif name.endswith("_ppi") or name in ("target_ppi", "effective_ppi", "ppi_x", "ppi_y"):
                value_text += " PPI"
            entries.append(f"{label}: {value_text}")
        if result.object_ref:
            entries.append(f"{self.t['measure_object']}: {result.object_ref}")
        if result.page is not None:
            entries.append(f"{self.t['page']}: {result.page}")
        if result.bounding_box_pt:
            box = " × ".join(f"{value:.1f}" for value in result.bounding_box_pt)
            entries.append(f"{self.t['measure_bounds']}: {box} pt")
        if result.details.get("reuse_status") in ("single", "reused"):
            reuse = self.t["image_reuse_reused"] if result.details["reuse_status"] == "reused" else self.t["image_reuse_single"]
            entries.append(f"{self.t['measure_image_reuse']}: {reuse} ({result.details.get('reuse_count', 1)})")
        if result.details.get("native_illustrator_incorporation") == "unverified":
            entries.append(self.t["image.ai_native_unverified"])
        if result.details.get("preview_quality") == "approximate":
            entries.append(self.t["image.highlight_approximate"])
        return "; ".join(entries)

    def _preflight_summary(self, report):
        results = report.results
        warnings = sum(item.status is Status.WARNING for item in results)
        errors = sum(item.status is Status.ERROR for item in results)
        unknown = sum(item.status is Status.UNKNOWN for item in results)
        images = self.t["measure_unknown"] if report.image_count is None else str(report.image_count)
        placements = (self.t["measure_unknown"] if report.image_placement_count is None
                      else str(report.image_placement_count))
        fonts = self.t["measure_unknown"] if report.font_count is None else str(report.font_count)
        return self.t["preflight_summary"].format(unique_images=images, placements=placements, fonts=fonts,
                                                  warnings=warnings, errors=errors, unknown=unknown)

    def _activate_check_item(self, item, _column):
        result = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(result, CheckResult) and result.page and self.info:
            self.page = max(0, min(len(self.info.pages) - 1, result.page - 1))
            preview_box = result.details.get("preview_box")
            self._highlight_page = result.page if preview_box and result.category == "images" else None
            self.preview.set_image_highlight(
                preview_box if result.category == "images" else None,
                self.t["image.highlight_approximate"] if preview_box else "")
            self._update_page_label(); self._update_dimensions(); self._render()

    def open_preflight_settings(self):
        dialog = QDialog(self); dialog.setWindowTitle(self.t["settings_title"])
        layout = QVBoxLayout(dialog); form = QFormLayout()
        resolution = QComboBox(); resolution.addItems(["150 PPI", "200 PPI", "300 PPI"])
        resolution.setCurrentIndex({150: 0, 200: 1, 300: 2}[self._preflight_settings.target_image_ppi])
        bleed = QComboBox(); bleed.addItems(["0 mm", "2 mm", "3 mm", "5 mm"])
        bleed.setCurrentIndex({0: 0, 2: 1, 3: 2, 5: 3}[int(self._preflight_settings.minimum_bleed_mm)])
        form.addRow(self.t["settings_resolution"], resolution)
        form.addRow(self.t["settings_bleed"], bleed); layout.addLayout(form)
        note = QLabel(self.t["settings_note"]); note.setWordWrap(True); layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        new_settings = PreflightSettings((150, 200, 300)[resolution.currentIndex()],
                                         (0, 2, 3, 5)[bleed.currentIndex()])
        if new_settings != self._preflight_settings:
            self._preflight_settings = new_settings
            self.settings.setValue("preflight/target_image_ppi", new_settings.target_image_ppi)
            self.settings.setValue("preflight/minimum_bleed_mm", new_settings.minimum_bleed_mm)
            if self.info:
                self._validate_selected()

    def _refresh_preflight_language(self):
        if not self.info or not self.path: return
        report = self.preflight_reports.get((self._canonical(self.path), self._preflight_settings))
        if report is not None:
            self._preflight_display(report)

    def _document_state(self, info, loading=False, error=None):
        t = self.t
        if not info:
            status = t.get(error, t["invalid"]) if error else (t["loading"] if loading else t["not_open"])
            for key in self.details: self.details[key].setText(f"{t[key]}: {status}")
            self.check_tree.clear()
            if error: QMessageBox.warning(self, t["app"], status)
            self.zoom_label.setText("—")
            return
        self.details["filename"].setText(f"{t['filename']}: {info.path.name}")
        self.details["type"].setText(f"{t['type']}: {t[info.kind]}")
        self.details["size"].setText(f"{t['size']}: {info.size / 1048576:.2f} {t['mb']}")
        self.details["pages"].setText(f"{t['pages']}: {len(info.pages)}")
        self.details["status"].setText(f"{t['status']}: {t['ready']}")
        self.details["render"].setText(f"{t['render']}: {t['checking']}")
        self.details["diagnostics"].setText(f"{t['diagnostics']}: {t['analysis_running']}")
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
        highlighted = getattr(self, "_highlight_page", None)
        if highlighted is not None and highlighted != self.page + 1:
            self._highlight_page = None
            self.preview.set_image_highlight()
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
        if key in ("zoom_in", "zoom_out"):
            current = self.zoom if self.fit_mode == "manual" else self._fit_zoom()
            target = current * 1.2 if key == "zoom_in" else current / 1.2
            self._set_zoom_factor(max(0.05, min(8.0, target)), debounced=True); return
        elif key == "fit_width": self.fit_mode = "width"
        else: self.fit_mode = "page"
        self._zoom_timer.stop()
        self._render()

    def _set_zoom_factor(self, zoom, debounced=True):
        old = self.zoom if self.fit_mode == "manual" else self._fit_zoom()
        center = self.scroll.viewport().rect().center()
        anchor_x = self.scroll.horizontalScrollBar().value() + center.x()
        anchor_y = self.scroll.verticalScrollBar().value() + center.y()
        self.fit_mode = "manual"
        self.zoom = max(0.05, min(8.0, float(zoom)))
        self.zoom_control.set_zoom(self.zoom)
        self._scale_preview_immediately(old, self.zoom, anchor_x, anchor_y, center.x(), center.y())
        self._schedule_zoom_render(debounced)

    def _schedule_zoom_render(self, debounced=True):
        if debounced:
            self._zoom_timer.start(self._debounce_ms)
        else:
            self._zoom_timer.stop(); self._render()

    def _scale_preview_immediately(self, old_zoom, new_zoom, anchor_x, anchor_y, x, y):
        """Scale the last final PDFium pixmap for instant interaction feedback."""
        if self._final_pixmap is None or old_zoom <= 0:
            return
        dpr = max(1.0, self.devicePixelRatioF())
        factor = new_zoom / self._final_zoom
        base = self._final_pixmap
        requested_width = max(1, round(base.width() * factor)); requested_height = max(1, round(base.height() * factor))
        cap_ratio = min(1.0, (MAX_RENDER_PIXELS / (requested_width * requested_height)) ** 0.5,
                        MAX_RENDER_DIMENSION / requested_width, MAX_RENDER_DIMENSION / requested_height)
        width = max(1, round(requested_width * cap_ratio)); height = max(1, round(requested_height * cap_ratio))
        # Temporary Qt scaling is intentionally fast; a final PDFium render replaces it.
        preview = base.scaled(width, height, Qt.AspectRatioMode.IgnoreAspectRatio,
                              Qt.TransformationMode.FastTransformation)
        preview.setDevicePixelRatio(max(0.05, base.devicePixelRatioF() * cap_ratio))
        self.preview.setPixmap(preview)
        self.preview.resize(QSize(max(1, round(requested_width / dpr)),
                                  max(1, round(requested_height / dpr))))
        self.scroll.horizontalScrollBar().setValue(max(0, round(anchor_x * new_zoom / old_zoom - x)))
        self.scroll.verticalScrollBar().setValue(max(0, round(anchor_y * new_zoom / old_zoom - y)))
        self.zoom_control.set_zoom(new_zoom)
        self.preview.setToolTip(self.t.get("preview_temporary", ""))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.info and self.fit_mode in ("page", "width"): self._schedule_zoom_render(True)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_toolbar_group_width()

    def _update_toolbar_group_width(self):
        self.group_toolbar_layout.activate()
        size = self.group_toolbar_layout.sizeHint()
        self.groups_widget.setMinimumSize(size)
        self.groups_widget.resize(size)
        self.groups_widget.updateGeometry()

    def eventFilter(self, watched, event):
        if watched is self.scroll.viewport() and event.type() == QEvent.Type.Resize:
            if self.info and self.fit_mode in ("page", "width"): self._schedule_zoom_render(True)
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
        self.fit_mode = "manual"; self.zoom = new
        self.zoom_control.set_zoom(new)
        self._scale_preview_immediately(old, new, anchor_x, anchor_y, x, y)
        self._schedule_zoom_render(True)

    def _render(self):
        self._zoom_timer.stop()
        if not self.info:
            self._update_page_label(); return
        page = self.info.pages[self.page]
        zoom = self._fit_zoom() if self.fit_mode in ("page", "width") else self.zoom
        self.zoom_control.set_zoom(zoom)
        dpr = max(1.0, self.devicePixelRatioF())
        pixel_scale = 96.0 / 72.0 * zoom * dpr
        self.render_serial += 1
        token, serial, index, path = self.token, self.render_serial, self.page, self.info.path
        self._render_requests += 1
        if self._render_busy:
            self._render_pending = True
            self._update_page_label(); return
        self._render_busy = True; self._render_active_serial = serial
        self._pdfium_render_started += 1
        task = Task(token, lambda: (serial, index, dpr, zoom, render_page_result(path, index, pixel_scale)))
        task.signals.result.connect(self._image_ready); task.signals.failed.connect(self._render_failed)
        task.signals.finished.connect(self._render_finished); self._start_task(task, priority=10)
        self._update_page_label()

    def _image_ready(self, token, result):
        if token != self.token: return
        serial, index, dpr, zoom, rendered = result
        if serial != self.render_serial or index != self.page: return
        image = rendered.image
        pixmap = QPixmap.fromImage(image); pixmap.setDevicePixelRatio(dpr)
        self._final_pixmap = pixmap; self._final_zoom = zoom
        self.preview.setPixmap(pixmap); self.preview.resize(pixmap.deviceIndependentSize().toSize())
        self._render_limited = rendered.limited
        self.preview.setToolTip(self.t.get("render_limited", "") if rendered.limited else "")
        self._render_completed += 1
        if rendered.limited:
            self.details["render"].setText(f"{self.t['render']}: {self.t.get('render_limited', 'Resolution limited')}")

    def _render_finished(self, _token):
        self._render_busy = False; self._render_active_serial = None
        if self._render_pending and self.info and not self._zoom_timer.isActive():
            self._render_pending = False
            self._render()

    def _render_failed(self, token, _reason):
        if token == self.token: self.details["render"].setText(f"{self.t['render']}: {self.t['error']}")

    def _validation_done(self, token, _result):
        if token != self.token: return
        self._validation_display("passed")

    def _validation_failed(self, token, _reason):
        if token != self.token: return
        self._validation_display("failed")

    def _size_file_menu_for_actions(self):
        """Size the native menu for its translated label and shortcut columns."""
        self.file_menu.setMinimumWidth(0)
        self.file_menu.adjustSize()
        metrics = self.file_menu.fontMetrics()
        actions = [action for action in self.file_menu.actions() if not action.isSeparator()]
        label_width = max((metrics.horizontalAdvance(action.text()) for action in actions), default=0)
        shortcut_width = max((metrics.horizontalAdvance(action.shortcut().toString(QKeySequence.SequenceFormat.NativeText))
                              for action in actions if action.shortcut()), default=0)
        style = self.file_menu.style()
        menu_margin = style.pixelMetric(QStyle.PixelMetric.PM_MenuHMargin, None, self.file_menu)
        panel_width = style.pixelMetric(QStyle.PixelMetric.PM_MenuPanelWidth, None, self.file_menu)
        check_column = max(16, style.pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth, None, self.file_menu))
        # QMenu paints shortcuts in their own trailing column. Include its label,
        # a 22 logical-pixel gap, the check gutter and style/item padding.
        required = label_width + check_column + 28 + 2 * (14 + menu_margin + panel_width)
        if shortcut_width:
            required += shortcut_width + 22
        self.file_menu.setMinimumWidth(max(self.file_menu.sizeHint().width(), required))

    def about(self):
        logo = Path(__file__).resolve().parents[3] / "assets" / "logo" / "ppview.ico"
        dialog = AboutDialog(self, self.language, build_commit(), logo)
        dialog.exec()

    def user_guide(self):
        UserGuideDialog(self, self.language).exec()

    def closeEvent(self, event):
        self._zoom_timer.stop(); self._render_pending = False
        self.token += 1; self.render_serial += 1
        for path in tuple(self.document_paths.values()): release_document(path)
        app = QApplication.instance()
        if app and hasattr(self, "_drop_filter"):
            app.removeEventFilter(self._drop_filter)
        super().closeEvent(event)

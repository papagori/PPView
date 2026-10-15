"""Lightweight startup splash shown before importing the main window."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from ppview import __display_version__
from ppview.i18n.strings import strings


class StartupSplash(QSplashScreen):
    """Compact branded splash; the timer only animates a small spinner."""

    def __init__(self, language: str = "en") -> None:
        dpr = QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1.0
        self._logical_size = (540, 230)
        pixmap = QPixmap(round(self._logical_size[0] * dpr), round(self._logical_size[1] * dpr))
        pixmap.setDevicePixelRatio(dpr)
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
        self.setWindowTitle("PPView startup")
        self._language = language
        self._t = strings(language)
        self._frame = 0
        # A plain gradient is enough for Qt to create and show the splash
        # immediately. Logo decoding and text shaping follow its first paint.
        self._draw_initial_background()
        self._timer = QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._animate)

    def _draw_initial_background(self) -> None:
        pixmap = self.pixmap()
        painter = QPainter(pixmap)
        gradient = QLinearGradient(0, 0, self._logical_size[0], 0)
        gradient.setColorAt(0, QColor("#0b1424"))
        gradient.setColorAt(1, QColor("#174b72"))
        painter.fillRect(QRectF(0, 0, *self._logical_size), gradient)
        painter.end()
        self.setPixmap(pixmap)

    def complete_branding(self) -> None:
        """Paint logo, localized slogan and metadata over the visible splash."""
        self._draw_background()
        self.update()

    def _draw_background(self) -> None:
        pixmap = self.pixmap()
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self._logical_size[0], 0)
        gradient.setColorAt(0, QColor("#0b1424"))
        gradient.setColorAt(1, QColor("#174b72"))
        painter.fillRect(QRectF(0, 0, *self._logical_size), gradient)
        painter.setPen(QColor("#ffffff"))
        # Use the checked-in raster logo rather than triggering first-use SVG
        # rendering on the critical path before the splash is visible.
        import sys
        from pathlib import Path
        logo_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3])) / "assets" / "logo" / "ppview-icon-preview.png"
        logo = QPixmap(str(logo_path))
        painter.drawPixmap(QRectF(30, 30, 54, 54), logo, QRectF(0, 0, logo.width(), logo.height()))
        title = QFont("Segoe UI", 25, QFont.Weight.DemiBold)
        painter.setFont(title)
        painter.drawText(QPointF(100, 57), "PPView")
        painter.setPen(QColor("#c5e5f3"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(QPointF(102, 82), self._t["title_suffix"])
        painter.setPen(QColor("#a9c6d8"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QPointF(31, 166), f"v{__display_version__}")
        painter.drawText(QPointF(31, 190), "© 2026 Matthieu Tuffet")
        painter.setPen(QColor("#e1edf5"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(QPointF(31, 218), self._t["startup_status"])
        painter.end()
        self.setPixmap(pixmap)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()

    def _animate(self) -> None:
        self._frame = (self._frame + 1) % 12
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() - 34, self.height() - 24)
        painter.setPen(QPen(QColor(130, 206, 235, 65), 2.2))
        painter.drawEllipse(center, 8, 8)
        painter.setPen(QPen(QColor("#78d7f2"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(QRectF(center.x() - 8, center.y() - 8, 16, 16), (self._frame * 30) * 16, 220 * 16)

    def finish(self, main_window) -> None:
        self._timer.stop()
        super().finish(main_window)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)

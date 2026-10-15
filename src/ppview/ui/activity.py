"""Small delayed activity labels for background work in the main window."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class DelayedActivity:
    """Show a non-blocking label only when its current operation lasts."""

    def __init__(self, parent: QWidget, *, delay_ms: int = 250, object_name: str = "activity"):
        self.widget = QWidget(parent)
        self.widget.setObjectName(object_name)
        self.widget.setStyleSheet(
            "QWidget { color:#bceaff; background:#142b45; border:1px solid #2d5b7d; "
            "border-radius:8px; }"
            "QProgressBar { background:#203d5a; border:0; border-radius:3px; }"
            "QProgressBar::chunk { background:#55baff; border-radius:3px; }"
        )
        layout = QHBoxLayout(self.widget)
        layout.setContentsMargins(9, 3, 10, 3)
        layout.setSpacing(8)
        self.spinner = QProgressBar(self.widget)
        self.spinner.setObjectName(f"{object_name}Spinner")
        self.spinner.setRange(0, 0)
        self.spinner.setTextVisible(False)
        self.spinner.setFixedSize(30, 7)
        layout.addWidget(self.spinner)
        self.label = QLabel(self.widget)
        self.label.setObjectName(f"{object_name}Message")
        self.label.setStyleSheet("QLabel { color:#bceaff; background:transparent; border:0; padding:0; }")
        layout.addWidget(self.label)
        self.widget.adjustSize()
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.widget.hide()
        self._timer = QTimer(self.widget)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self._show_current)
        self._token = None
        self._message = ""

    @property
    def token(self):
        return self._token

    def begin(self, token, message: str):
        self._timer.stop()
        self._token = token
        self._message = message
        self.label.setText(message)
        self.widget.adjustSize()
        self.widget.hide()
        self._timer.start()

    def finish(self, token):
        if token != self._token:
            return False
        self._timer.stop()
        self._token = None
        self.widget.hide()
        return True

    def cancel(self):
        self._timer.stop()
        self._token = None
        self.widget.hide()

    def set_message(self, message: str):
        self._message = message
        self.label.setText(message)
        self.widget.adjustSize()
        self.widget.updateGeometry()

    def _show_current(self):
        if self._token is not None:
            self.widget.adjustSize()
            self.widget.show()


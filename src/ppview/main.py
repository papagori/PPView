import sys
from PySide6.QtWidgets import QApplication
from ppview.ui.window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("papagori"); app.setApplicationName("PPView")
    window = MainWindow(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())

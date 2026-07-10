import sys
from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    app.setStyleSheet("""
        QMainWindow { background-color: #1e1e1e; color: #ffffff; }
        QWidget { background-color: #1e1e1e; color: #ffffff; }
        QPushButton { background-color: #333333; border: 1px solid #555555; padding: 5px; border-radius: 3px; }
        QPushButton:hover { background-color: #444444; }
        QPushButton:disabled { color: #777777; }
        QTextEdit, QListWidget { background-color: #252526; border: 1px solid #333333; }
        QTabBar::tab { background: #333333; padding: 8px; border: 1px solid #1e1e1e; }
        QTabBar::tab:selected { background: #1e1e1e; }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

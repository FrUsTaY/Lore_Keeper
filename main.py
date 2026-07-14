import os
# CRITICAL: Prevent silent crash on AMD Ryzen 3 (Vega) and similar CPUs.
# Must be set before ANY imports of faster_whisper or ctranslate2
os.environ["CTRANSLATE2_CPU_ISA_TO_USE"] = "GENERIC"
os.environ["OMP_NUM_THREADS"] = "1"       # Prevent OpenMP thread conflicts during init
os.environ["MKL_DEBUG_CPU_TYPE"] = "5"    # Force correct MKL execution on AMD CPUs
# Fix silent OpenMP crash in GUI applications
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.utils.path_utils import ensure_required_directories

def main():
    ensure_required_directories()

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

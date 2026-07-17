import os
# CRITICAL: Prevent silent crash on AMD Ryzen 3 (Vega) and similar CPUs.
# Must be set before ANY imports of faster_whisper or ctranslate2
os.environ["CTRANSLATE2_CPU_ISA_TO_USE"] = "GENERIC"
os.environ["OMP_NUM_THREADS"] = "1"       # Prevent OpenMP thread conflicts during init
os.environ["MKL_DEBUG_CPU_TYPE"] = "5"    # Force correct MKL execution on AMD CPUs
# Prevents silent OpenMP crash in GUI applications
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import os
import sys

# Динамическое подключение CUDA DLL
from src.utils.path_utils import get_path
dll_path = get_path("cuBLAS and cuDNN")
if os.path.exists(dll_path):
    os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(dll_path)
        except Exception as e:
            print(f"Ошибка добавления DLL директории: {e}")

from src.utils.path_utils import ensure_required_directories

import multiprocessing

def main():
    multiprocessing.freeze_support()
    ensure_required_directories()

    # CRITICAL: Prevent MSVCP140.dll version conflict between shiboken6 (PySide6) and cuDNN.
    # PySide6 (shiboken6) bundles its own MSVCP140.dll. If Windows loads it first, cuDNN/ctranslate2
    # will attempt to use it, causing an ABI mismatch and an Access Violation (0xc0000005) crash during
    # GPU initialization. Preloading the system C++ runtime DLLs from System32 forces both to share
    # the correct system-wide version. Do NOT remove this block.
    if sys.platform == "win32":
        import ctypes
        import logging
        try:
            ctypes.CDLL(r"C:\Windows\System32\vcruntime140_1.dll")
            ctypes.CDLL(r"C:\Windows\System32\msvcp140.dll")
        except OSError as e:
            error_msg = f"Warning: could not preload system MSVCP140.dll: {e}. GPU initialization may crash if Visual C++ Redistributable is missing or outdated."
            print(error_msg)
            logging.warning(error_msg)

    from PySide6.QtWidgets import QApplication
    from src.gui.main_window import MainWindow

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

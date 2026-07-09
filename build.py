import os
import subprocess

def build():
    print("Начало сборки через PyInstaller...")

    # Check if pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller не найден. Устанавливаем...")
        subprocess.check_call(["pip", "install", "pyinstaller"])

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--add-data", "configs:configs",
        "--hidden-import", "PySide6",
        "--hidden-import", "pytesseract",
        "--hidden-import", "spacy",
        "--hidden-import", "rapidfuzz",
        "--name", "LoreKeeper",
        "main.py"
    ]

    print(f"Выполняем: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    print("\nСборка завершена! Ищите EXE-файл в папке dist/")

if __name__ == "__main__":
    build()

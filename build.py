import os
import subprocess
import sys

def get_nvidia_packages():
    try:
        output = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True)
        packages = []
        for line in output.splitlines():
            pkg_name = line.split('==')[0].split('@')[0].strip()
            if pkg_name.lower().startswith('nvidia-'):
                packages.append(pkg_name)
        return packages
    except subprocess.CalledProcessError:
        return []

def build():
    print("Начало сборки через PyInstaller...")

    # Check if pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller не найден. Устанавливаем...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    nvidia_packages = get_nvidia_packages()
    nvidia_collect_flags = []
    for pkg in nvidia_packages:
        nvidia_collect_flags.extend(["--collect-all", pkg])

    # 1. Build gpu_tester.exe
    gpu_tester_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--hidden-import", "faster_whisper",
        "--hidden-import", "ctranslate2",
        "--hidden-import", "huggingface_hub",
        "--name", "gpu_tester",
        os.path.join("src", "utils", "gpu_tester.py")
    ]
    gpu_tester_cmd.extend(nvidia_collect_flags)

    print(f"Сборка gpu_tester: {' '.join(gpu_tester_cmd)}")
    subprocess.check_call(gpu_tester_cmd)

    # 2. Build LoreKeeper.exe
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--add-data", f"configs{os.pathsep}configs",
        "--hidden-import", "PySide6",
        "--hidden-import", "mss",
        "--hidden-import", "cv2",
        "--hidden-import", "PIL",
        "--hidden-import", "Pillow",
        "--hidden-import", "imagehash",
        "--hidden-import", "requests",
        "--hidden-import", "pandas",
        "--hidden-import", "numpy",
        "--hidden-import", "spacy",
        "--hidden-import", "rapidfuzz",
        "--hidden-import", "src.groq_client",
        "--hidden-import", "soundfile",
        "--hidden-import", "PyAudioWPatch",
        "--hidden-import", "ctranslate2",
        "--hidden-import", "faster_whisper",
        "--hidden-import", "huggingface_hub",
        "--hidden-import", "pywhispercpp",
        "--hidden-import", "shiboken6",
        "--hidden-import", "torch",
        "--hidden-import", "torchaudio",
        "--hidden-import", "omegaconf",
        "--collect-all", "PySide6",
        "--collect-all", "torch",
        "--collect-binaries", "soundfile",
        "--name", "LoreKeeper",
        "main.py"
    ]
    cmd.extend(nvidia_collect_flags)

    print(f"Сборка LoreKeeper: {' '.join(cmd)}")
    subprocess.check_call(cmd)

    print("\nСборка завершена! Ищите EXE-файлы в папке dist/")

if __name__ == "__main__":
    build()

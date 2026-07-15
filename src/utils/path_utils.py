import os
import sys

if hasattr(sys, '_MEIPASS'):
    PROJECT_ROOT = sys._MEIPASS
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_path(relative_path):
    return os.path.join(PROJECT_ROOT, relative_path)

def ensure_required_directories():
    dirs = ["logs", "outputs/stories", "outputs/screenshots", "outputs/temp_audio"]
    for d in dirs:
        os.makedirs(get_path(d), mode=0o700, exist_ok=True)

    # Cleanup any leftover temp audio files from previous crashes
    temp_audio_dir = get_path("outputs/temp_audio")
    if os.path.exists(temp_audio_dir):
        for f in os.listdir(temp_audio_dir):
            if f.endswith(".wav"):
                try:
                    os.remove(os.path.join(temp_audio_dir, f))
                except OSError:
                    pass

import os
import sys

if getattr(sys, 'frozen', False):
    # When running as compiled executable (PyInstaller)
    # sys.executable points to the .exe file
    USER_DATA_ROOT = os.path.dirname(sys.executable)
else:
    # When running from source
    USER_DATA_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_path(relative_path):
    """
    Returns the path for user data (configs, logs, outputs) relative to the
    application directory (either the project root for source, or alongside the .exe).
    """
    return os.path.join(USER_DATA_ROOT, relative_path)

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

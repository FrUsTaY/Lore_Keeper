import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_path(relative_path):
    return os.path.join(PROJECT_ROOT, relative_path)

def ensure_required_directories():
    dirs = ["logs", "outputs/stories", "outputs/screenshots"]
    for d in dirs:
        os.makedirs(get_path(d), exist_ok=True)

import json
from src.utils.path_utils import get_path

class ConfigManager:
    def __init__(self, config_path="configs/lm_studio_config.json"):
        import os
        self.config_path = get_path(config_path)
        self.config = self.load_config()
        if not os.path.exists(self.config_path):
            self.save_config(self.config)

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config {self.config_path}: {e}")
            return {
                "api_url": "http://localhost:1234/v1/chat/completions",
                "models_url": "http://localhost:1234/v1/models",
                "model": "qwen2.5-1.5b-instruct",
                "temperature": 0.8,
                "max_tokens": 1500,
                "timeout": 120,
                "genre": "fantasy",
                "save_screenshots": True,
                "screenshots_path": get_path("outputs/screenshots"),
                "llm_provider": "LM Studio",
                "groq_token": "",
                "groq_model": "llama-3.1-8b-instant",
                "audio_provider": "Groq API",
                "audio_api_url": "https://api.groq.com/openai/v1/audio/transcriptions",
                "local_whisper_model": "base",
                "enable_hotkey": True,
                "hotkey_combo": "ctrl+shift+f11"
            }

    def save_config(self, new_config):
        import os
        self.config = new_config
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key, default=None):
        val = self.config.get(key, default)
        if key in ["screenshots_path", "tesseract_path"] and isinstance(val, str):
            # Try to handle paths that might be saved as relative in old configs,
            # but don't mess with absolute paths (like C:\...)
            import os
            if not os.path.isabs(val):
                return get_path(val)
        return val

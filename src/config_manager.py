import json

class ConfigManager:
    def __init__(self, config_path="configs/lm_studio_config.json"):
        self.config_path = config_path
        self.config = self.load_config()

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
                "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                "save_screenshots": True,
                "screenshots_path": "outputs/screenshots",
                "llm_provider": "LM Studio",
                "hf_token": "",
                "hf_model": "mistralai/Mistral-7B-Instruct-v0.2"
            }

    def save_config(self, new_config):
        self.config = new_config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key, default=None):
        return self.config.get(key, default)

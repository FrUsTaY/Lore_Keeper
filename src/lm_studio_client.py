import requests
import json
import time

class LMStudioClient:
    def __init__(self, config):
        self.config = config
        self.api_url = self.config.get("api_url")
        self.models_url = self.config.get("models_url")
        self.timeout = self.config.get("timeout", 120)

    def check_health(self):
        """Checks if LM Studio is running and responding."""
        try:
            response = requests.get(self.models_url, timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            # simple retry
            time.sleep(2)
            try:
                response = requests.get(self.models_url, timeout=10)
                return response.status_code == 200
            except:
                return False

    def generate(self, messages):
        """Sends a request to generate completion."""
        payload = {
            "model": self.config.get("model", "local-model"),
            "messages": messages,
            "temperature": self.config.get("temperature", 1.0),
            "max_tokens": -1  # -1 instructs LM Studio/local OpenAI endpoints to generate up to the model's absolute limit
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=None
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            raise Exception(f"LM Studio Error: {e}")

import requests
import json
import time

class GroqClient:
    def __init__(self, config):
        self.config = config
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.timeout = self.config.get("timeout", 120)

    def check_health(self):
        """Checks if Groq API token is valid."""
        token = self.config.get("groq_token", "")

        if not token:
            print("Groq API token is missing.")
            return False

        headers = {"Authorization": f"Bearer {token}"}
        url = "https://api.groq.com/openai/v1/models"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            # simple retry
            time.sleep(2)
            try:
                response = requests.get(url, headers=headers, timeout=10)
                return response.status_code == 200
            except:
                return False

    def generate(self, messages, retries=3):
        """Sends a request to generate completion."""
        model = self.config.get("groq_model", "llama-3.1-8b-instant")
        token = self.config.get("groq_token", "")

        if not token:
            raise Exception("Groq API token is missing.")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Groq uses an OpenAI-compatible messages array format,
        # but requires specific keys so we ensure the structure is exactly right.
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": self.config.get("temperature", 0.8),
            "max_tokens": self.config.get("max_tokens", 1500)
        }

        delay = 2
        for attempt in range(retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
                else:
                    return str(data)

            except requests.exceptions.RequestException as e:
                # Try to get more info from response if possible
                error_msg = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code == 401:
                        raise Exception("Groq API Error: Invalid or missing token (401 Unauthorized).")
                    try:
                        error_data = e.response.json()
                        if 'error' in error_data and 'message' in error_data['error']:
                            error_msg = error_data['error']['message']
                    except:
                        pass
                elif isinstance(e, requests.exceptions.ConnectionError):
                    error_msg = "Ошибка сети (ConnectionError). Не удалось подключиться к серверу Groq."
                elif isinstance(e, requests.exceptions.Timeout):
                    error_msg = "Превышено время ожидания ответа от сервера Groq (Timeout)."

                if attempt == retries - 1:
                    raise Exception(f"Groq Error: {error_msg}")
                print(f"Попытка {attempt+1} не удалась: {error_msg}. Повтор через {delay} сек...")
                time.sleep(delay)
                delay *= 2

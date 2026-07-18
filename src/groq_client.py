import requests
import json
import time
import logging

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
            except requests.exceptions.RequestException as e:
                logging.error(f"Groq API health check failed: {e}")
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
            "temperature": self.config.get("temperature", 1.0)
        }

        delay = 2
        for attempt in range(retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=None)
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

    def transcribe_audio(self, file_path, retries=3):
        """Sends an audio file to an OpenAI-compatible Whisper API for transcription."""
        provider = self.config.get("audio_provider", "Облако (Groq API)")

        # If it's local whisper, this method shouldn't be called (handled in transcriber),
        # but just in case, we do nothing here.
        if provider in ["Local Whisper (CPU/GPU)", "Локальный (Встроенный движок)", "Локально (Встроенный движок Faster-Whisper)"]:
            return ""

        url = self.config.get("audio_api_url", "https://api.groq.com/openai/v1/audio/transcriptions")
        headers = {}

        # Only require token if hitting Groq or an external API that needs it
        if "groq.com" in url:
            token = self.config.get("groq_token", "")
            if not token:
                print("Groq API token is missing for audio transcription.")
                return ""
            headers["Authorization"] = f"Bearer {token}"
            model_name = "whisper-large-v3"
        else:
            # Local LM studio or other
            token = self.config.get("groq_token", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
            model_name = "whisper" # Usually LM studio just ignores this or uses loaded model

        delay = 2
        for attempt in range(retries):
            try:
                with open(file_path, "rb") as f:
                    files = {"file": (file_path, f, "audio/wav")}
                    data = {"model": model_name}

                    response = requests.post(url, headers=headers, files=files, data=data, timeout=None)
                    response.raise_for_status()

                    result = response.json()
                    return result.get("text", "").strip()
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        if 'error' in error_data and 'message' in error_data['error']:
                            error_msg = error_data['error']['message']
                    except:
                        pass
                if attempt == retries - 1:
                    print(f"Audio API Error: {error_msg}")
                    return ""
                time.sleep(delay)
                delay *= 2
            except Exception as e:
                print(f"Audio processing error: {e}")
                return ""

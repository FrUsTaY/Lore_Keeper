import requests
import json
import time

class HuggingFaceClient:
    def __init__(self, config):
        self.config = config
        self.api_url = "https://api-inference.huggingface.co/models/"
        self.timeout = self.config.get("timeout", 120)

    def check_health(self):
        """Checks if Hugging Face API is accessible."""
        model = self.config.get("hf_model", "mistralai/Mistral-7B-Instruct-v0.2")
        token = self.config.get("hf_token", "")

        if not token:
            print("Hugging Face API token is missing.")
            return False

        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.api_url}{model}"

        try:
            # A simple GET request to the model's info endpoint to check if it's accessible
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

    def generate(self, messages):
        """Sends a request to generate completion."""
        model = self.config.get("hf_model", "mistralai/Mistral-7B-Instruct-v0.2")
        token = self.config.get("hf_token", "")

        if not token:
            raise Exception("Hugging Face API token is missing.")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = f"{self.api_url}{model}"

        # Hugging Face Inference API usually expects string input,
        # but for instruct models it's better to format the messages into a prompt
        prompt = self._format_messages_to_prompt(messages)

        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": self.config.get("temperature", 0.8),
                "max_new_tokens": self.config.get("max_tokens", 1500),
                "return_full_text": False
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Hugging Face might return a list of generated texts
            if isinstance(data, list) and len(data) > 0 and 'generated_text' in data[0]:
                return data[0]['generated_text']
            elif isinstance(data, dict) and 'generated_text' in data:
                return data['generated_text']
            elif isinstance(data, dict) and 'error' in data:
                raise Exception(f"Hugging Face Error: {data['error']}")
            else:
                return str(data)

        except requests.exceptions.RequestException as e:
            # Try to get more info from response if possible
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    if 'error' in error_data:
                        error_msg = error_data['error']
                except:
                    pass
            raise Exception(f"Hugging Face Error: {error_msg}")

    def _format_messages_to_prompt(self, messages):
        """Formats the list of messages into a single prompt string suitable for instruct models."""
        prompt = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"[INST] {content} [/INST]\n"
            elif role == "user":
                prompt += f"[INST] {content} [/INST]\n"
            elif role == "assistant":
                prompt += f"{content}\n"
        return prompt

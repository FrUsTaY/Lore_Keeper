import requests
import sys
import json

# Вставьте сюда ваш реальный API ключ Groq (начинается с gsk_...)
API_KEY = "ВАШ_КЛЮЧ"
MODEL = "llama-3.1-8b-instant"

def test_groq():
    if API_KEY == "ВАШ_КЛЮЧ":
        print("[!] ОШИБКА: Пожалуйста, откройте файл test_groq.py и замените 'ВАШ_КЛЮЧ' на ваш реальный токен Groq.")
        sys.exit(1)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "Привет! Ответь коротко: ты меня понимаешь?"}
        ],
        "temperature": 0.5,
        "max_tokens": 50
    }

    print(f"[*] Отправка запроса к Groq API (модель: {MODEL})...")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        print(f"HTTP Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            message = data['choices'][0]['message']['content']
            print("\n✅ Успешный ответ от модели:")
            print("-" * 40)
            print(message)
            print("-" * 40)
        else:
            print("\n❌ Ошибка API:")
            try:
                print(json.dumps(response.json(), ensure_ascii=False, indent=2))
            except:
                print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Сетевая ошибка: {e}")

if __name__ == "__main__":
    test_groq()

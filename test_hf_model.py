import requests
import json
import sys

def test_huggingface_model(token, model, message):
    api_url = f"https://router.huggingface.co/hf-inference/models/{model}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # По словам пользователя "просто текст в формате сообщений",
    # мы будем формировать простой промпт для поля inputs, как это ожидает базовый API
    payload = {
        "inputs": message,
        "parameters": {
            "max_new_tokens": 100,
            "return_full_text": False
        }
    }

    print(f"--- Отправка запроса к Hugging Face API ---")
    print(f"URL: {api_url}")
    print(f"Headers: {{'Authorization': 'Bearer <hidden>', 'Content-Type': 'application/json'}}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print("-" * 40)

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        print(f"HTTP Status Code: {response.status_code}")

        try:
            response_json = response.json()
            print("Ответ сервера (JSON):")
            print(json.dumps(response_json, ensure_ascii=False, indent=2))
        except ValueError:
            print("Ответ сервера (Текст):")
            print(response.text)

        if response.status_code != 200:
            print("\nВНИМАНИЕ: Запрос завершился с ошибкой.")
            print("Возможные причины:")
            print("- Модель загружается (обычно статус 503, нужно подождать и повторить).")
            print("- Модель требует принятия лицензионного соглашения на сайте (статус 401/403).")
            print("- Модель закрыта (gated) или вы не имеете к ней доступа.")
            print("- API токен неверный или не имеет прав (статус 401).")
            print("- Модель слишком велика для бесплатного Inference API (требуется Pro подписка).")

    except requests.exceptions.RequestException as e:
        print(f"\nСетевая ошибка при выполнении запроса: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Зашитые параметры для удобного тестирования
    TOKEN = "ВАШ_ТОКЕН"  # Вставьте сюда ваш реальный Hugging Face токен (hf_...)
    MODEL = "HuggingFaceH4/zephyr-7b-beta"
    MESSAGE = "Привет, как дела?"

    test_huggingface_model(TOKEN, MODEL, MESSAGE)

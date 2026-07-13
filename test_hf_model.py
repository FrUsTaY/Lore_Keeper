import argparse
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
    parser = argparse.ArgumentParser(description="Тестовый скрипт для проверки доступности моделей Hugging Face через Inference API.")
    parser.add_argument("-t", "--token", required=True, help="Ваш Hugging Face API токен (hf_...)")
    parser.add_argument("-m", "--model", required=True, help="ID модели, например: HuggingFaceH4/zephyr-7b-beta")
    parser.add_argument("-msg", "--message", required=True, help="Текст сообщения (prompt), который будет отправлен модели")

    args = parser.parse_args()

    test_huggingface_model(args.token, args.model, args.message)

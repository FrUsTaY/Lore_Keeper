import requests
import sys
import time

# Вставьте сюда ваш реальный Hugging Face токен (hf_...)
TOKEN = "ВАШ_ТОКЕН"

def get_top_text_models(limit=30):
    """Получает список самых популярных моделей для генерации текста."""
    url = f"https://huggingface.co/api/models?pipeline_tag=text-generation&sort=downloads&limit={limit}"
    print(f"[*] Получаем топ-{limit} моделей с Hugging Face...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        models = [m["id"] for m in response.json()]
        return models
    except Exception as e:
        print(f"[!] Ошибка при получении списка моделей: {e}")
        sys.exit(1)

def test_model_availability(model_id, token):
    """Проверяет доступность модели через Inference API."""
    api_url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": "Hi",
        "parameters": {"max_new_tokens": 5}
    }

    try:
        # Небольшой таймаут, чтобы не ждать долго зависшие модели
        response = requests.post(api_url, headers=headers, json=payload, timeout=5)

        if response.status_code == 200:
            return True, "Доступна (200 OK)"
        elif response.status_code == 403:
            return False, "Требуется лицензия/Pro (403)"
        elif response.status_code == 401:
            return False, "Неверный токен (401)"
        elif response.status_code == 503:
            return False, "Загружается/Недоступна (503)"
        elif response.status_code == 400:
            return False, "Не поддерживается Inference API (400)"
        else:
            return False, f"Ошибка ({response.status_code})"
    except requests.exceptions.Timeout:
        return False, "Таймаут (Долго отвечает)"
    except Exception as e:
        return False, f"Сетевая ошибка"

def main():
    if TOKEN == "ВАШ_ТОКЕН":
        print("[!] ОШИБКА: Пожалуйста, откройте этот файл и замените 'ВАШ_ТОКЕН' на ваш реальный токен от Hugging Face.")
        sys.exit(1)

    models_to_test = get_top_text_models(30)

    print("\n[*] Начинаем тестирование моделей через бесплатный API (это займет пару минут)...")
    print("-" * 60)

    available_models = []

    for i, model in enumerate(models_to_test, 1):
        print(f"[{i}/{len(models_to_test)}] Проверка {model}... ", end="", flush=True)

        is_available, status_msg = test_model_availability(model, TOKEN)

        if is_available:
            print(f"✅ {status_msg}")
            available_models.append(model)
        else:
            print(f"❌ {status_msg}")

        # Небольшая пауза, чтобы не получить бан за спам (Rate Limit)
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("🎯 РЕЗУЛЬТАТЫ: ДОСТУПНЫЕ БЕСПЛАТНЫЕ МОДЕЛИ")
    print("=" * 60)

    if not available_models:
        print("К сожалению, ни одна из проверенных популярных моделей сейчас не доступна бесплатно.")
        print("Возможно, ваш токен недействителен, или у Hugging Face высокая нагрузка.")
    else:
        print("Вы можете скопировать любое из этих названий и использовать в проекте:\n")
        for model in available_models:
            print(f"  - {model}")

if __name__ == "__main__":
    main()

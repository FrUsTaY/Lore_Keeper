import json

from pathlib import Path
from src.utils.path_utils import get_path

class PromptBuilder:
    def __init__(self, genres_path="configs/genres.json"):
        full_path = get_path(genres_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                self._genres = json.load(f)
        except Exception as e:
            print(f"Error loading genres from {full_path}: {e}")
            self._genres = {
                "fantasy": {
                    "name": "Фэнтези",
                    "prompt": "Ты — опытный писатель-новеллист, специализирующийся на эпическом фэнтези. Твоя задача — превратить сухой список игровых событий в захватывающий рассказ от первого лица. Используй яркие метафоры, описывай чувства героя, добавляй драматизм. Пиши на русском языке, литературным стилем, избегай канцеляризмов. Рассказ должен быть связным, с плавными переходами между сценами."
                }
            }

    def load_events_from_log(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('events', [])

    def filter_events(self, events, max_events=100):
        # Очистка мусора и дубликатов
        filtered_events = []
        last_text = None
        for event in events:
            text = event.get("text", "").strip()

            # Убираем события короче 3 символов
            if len(text) < 3:
                continue

            # Убираем точные дубликаты подряд (если фраза повторяется >= 2 раз подряд, оставляем одно вхождение)
            if text == last_text:
                continue

            filtered_events.append(event)
            last_text = text

        if len(filtered_events) > max_events:
            # Simple strategy: take last N events
            return filtered_events[-max_events:]
        return filtered_events

    def build_system_prompt(self, genre, entities_context=""):
        genre_data = self._genres.get(genre, self._genres.get("fantasy", {"prompt": "Ты — опытный писатель-новеллист."}))
        base_prompt = genre_data.get("prompt", "Ты — опытный писатель-новеллист.")

        base_prompt += (
            "\n\nВАЖНО: Игнорируй в заметках любые пометки о фоновых шумах, музыке или звуковых "
            "эффектах (например, [Music], [Sighs], [Explosion]). Оставляй только осмысленную речь "
            "персонажей. Напиши финальную историю строго на русском языке, даже если исходные "
            "заметки на английском."
        )

        global_instructions = (
            "ЗАПРЕЩЕНО дословно копировать фразы из заметок в текст истории. "
            "Заметки — это сырой материал для понимания настроения и происходящего, а не готовые диалоги. "
            "Пиши полностью своими словами: придумывай диалоги, описания локаций и деталей, которых нет в заметках. "
            "Не пытайся описать каждое событие по порядку — выбери 2-4 ключевых момента и наполни пространство между ними собственным вымыслом. "
            "Игнорируй короткие, бессвязные или многократно повторяющиеся фразы — не пытайся оправдать их в сюжете.\n\n"
            "Если в заметках встречается маркер '<--- СМЕНА СЦЕНЫ / ПРОШЛО ВРЕМЯ --->', это означает завершение текущего эпизода. "
            "При обнаружении этого маркера обязательно делай логический переход (например: 'Спустя некоторое время...', 'Закончив дела там, я отправился...', 'Дорога привела меня в...'), а также начинай новый абзац или главу. "
            "Кроме того, строго игнорируй бессвязные, одиночные фразы, которые явно выбиваются из контекста (например, случайные реплики NPC)."
        )

        base_prompt += f"\n\nДОПОЛНИТЕЛЬНЫЕ ПРАВИЛА:\n{global_instructions}"

        if entities_context:
            base_prompt += f"\n\nВажный контекст: {entities_context}"

        return base_prompt

    def build_user_prompt(self, events):
        prompt_parts = [
            "Ниже приведены сырые заметки наблюдателя о событиях, "
            "произошедших с игровым персонажем в хронологическом порядке. "
            "Это НЕ готовые реплики для истории, а лишь ориентир по фактам и настроению — "
            "напиши на их основе полностью самостоятельный рассказ от первого лица, "
            "не копируя фразы дословно.\n\nЗаметки:\n"
        ]
        for idx, event in enumerate(events):
            time_str = event.get("timestamp", "").split("T")[-1][:8] # Extract time HH:MM:SS
            text = event.get("text", "")
            prompt_parts.append(f"[{time_str}] {text}\n")

        prompt_parts.append("\nРассказ (полностью своими словами, без цитат из заметок):")
        return "".join(prompt_parts)

    def build_messages(self, events, genre, entities_context="", max_events=100):
        # We assume `events` is already filtered by ContextSelector
        system_prompt = self.build_system_prompt(genre, entities_context)
        user_prompt = self.build_user_prompt(events)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

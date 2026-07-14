import json

class PromptBuilder:
    def __init__(self):
        pass

    def load_events_from_log(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('events', [])

    def filter_events(self, events, max_events=100):
        if len(events) > max_events:
            # Simple strategy: take last N events
            return events[-max_events:]
        return events

    def build_system_prompt(self, genre, entities_context=""):
        prompts = {
            "fantasy": "Ты — опытный писатель-новеллист, специализирующийся на эпическом фэнтези. Твоя задача — превратить сухой список игровых событий в захватывающий рассказ от первого лица. Используй яркие метафоры, описывай чувства героя, добавляй драматизм. Пиши на русском языке, литературным стилем, избегай канцеляризмов. Рассказ должен быть связным, с плавными переходами между сценами. \n\nВАЖНО: Игнорируй в логах любые пометки о фоновых шумах, музыке или звуковых эффектах (например, [Music], [Sighs], [Explosion]). Оставляй только осмысленную речь персонажей. Напиши финальную историю строго на русском языке, даже если исходные логи на английском.",
            "cyberpunk": "Ты — писатель-новеллист в жанре киберпанк. Преврати лог событий в жесткий, неоновый рассказ от первого лица. Используй сленг улиц будущего, описывай технологии, импланты и мрачную атмосферу корпоративной антиутопии. Пиши на русском языке. \n\nВАЖНО: Игнорируй в логах любые пометки о фоновых шумах, музыке или звуковых эффектах (например, [Music], [Sighs], [Explosion]). Оставляй только осмысленную речь персонажей. Напиши финальную историю строго на русском языке, даже если исходные логи на английском.",
            "realism": "Ты — опытный мемуарист. Преврати сухой список событий в реалистичный и правдивый рассказ от первого лица. Пиши сдержанно, но выразительно, делая акцент на правдоподобных деталях. Пиши на русском языке. \n\nВАЖНО: Игнорируй в логах любые пометки о фоновых шумах, музыке или звуковых эффектах (например, [Music], [Sighs], [Explosion]). Оставляй только осмысленную речь персонажей. Напиши финальную историю строго на русском языке, даже если исходные логи на английском.",
            "horror": "Ты — мастер хоррора в духе Лавкрафта и Стивена Кинга. Преврати лог событий в пугающий рассказ от первого лица. Описывай гнетущую атмосферу, страх, неизвестность и чувство обреченности. Пиши на русском языке. \n\nВАЖНО: Игнорируй в логах любые пометки о фоновых шумах, музыке или звуковых эффектах (например, [Music], [Sighs], [Explosion]). Оставляй только осмысленную речь персонажей. Напиши финальную историю строго на русском языке, даже если исходные логи на английском."
        }

        base_prompt = prompts.get(genre, prompts["fantasy"])
        if entities_context:
            base_prompt += f"\n\nВажный контекст: {entities_context}"

        return base_prompt

    def build_user_prompt(self, events):
        prompt_parts = ["Ниже приведены события, произошедшие с игровым персонажем в хронологическом порядке. Напиши на их основе рассказ от первого лица.\n\nСобытия:\n"]
        for idx, event in enumerate(events):
            time_str = event.get("timestamp", "").split("T")[-1][:8] # Extract time HH:MM:SS
            text = event.get("text", "")
            prompt_parts.append(f"[{time_str}] {text}\n")

        prompt_parts.append("\nРассказ:")
        return "".join(prompt_parts)

    def build_messages(self, events, genre, entities_context="", max_events=100):
        # We assume `events` is already filtered by ContextSelector
        system_prompt = self.build_system_prompt(genre, entities_context)
        user_prompt = self.build_user_prompt(events)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

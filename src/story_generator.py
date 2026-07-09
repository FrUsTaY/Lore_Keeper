import os
from datetime import datetime
from src.config_manager import ConfigManager
from src.lm_studio_client import LMStudioClient
from src.prompt_builder import PromptBuilder
from src.deduplicator import Deduplicator
from src.entity_extractor import EntityExtractor
from src.context_selector import ContextSelector

class StoryGenerator:
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or ConfigManager()
        self.client = LMStudioClient(self.config_manager)
        self.builder = PromptBuilder()
        self.deduplicator = Deduplicator()
        self.extractor = EntityExtractor()

    def generate_story_from_log(self, log_path, output_path=None, genre=None, max_events=100, entities_context=""):
        if not self.client.check_health():
            raise Exception("LM Studio недоступна. Пожалуйста, запустите сервер.")

        events = self.builder.load_events_from_log(log_path)

        # Apply Phase 4 Smart Improvements
        events = self.deduplicator.filter_similar_events(events)
        extracted_entities = self.extractor.extract_entities(events)
        if extracted_entities:
            entities_context = (entities_context + " " + extracted_entities).strip()

        context_selector = ContextSelector(max_tokens=self.config_manager.get("max_tokens", 1500))
        events = context_selector.select_events(events)

        genre = genre or self.config_manager.get("genre", "fantasy")

        messages = self.builder.build_messages(events, genre, entities_context)

        print("Отправка запроса в LM Studio...")
        story_text = self.client.generate(messages)

        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"outputs/stories/story_{timestamp}.md"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(story_text)

        print(f"Рассказ сохранен в: {output_path}")
        return output_path, story_text

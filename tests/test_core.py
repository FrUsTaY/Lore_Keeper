import os

def test_imports():
    from src.screen_capture import ScreenCapture
    from src.event_logger import EventLogger
    from src.trigger_manager import TriggerManager

    from src.config_manager import ConfigManager
    from src.lm_studio_client import LMStudioClient
    from src.prompt_builder import PromptBuilder
    from src.story_generator import StoryGenerator

    from src.deduplicator import Deduplicator
    from src.entity_extractor import EntityExtractor
    from src.context_selector import ContextSelector

    from src.session_manager import SessionManager
    assert True

def test_deduplicator_normalize_text():
    from src.deduplicator import Deduplicator
    dedup = Deduplicator()

    # Lowercase conversion
    assert dedup.normalize_text("HELLO WORLD") == "hello world"
    # Cyrillic lowercase conversion, including Ё
    assert dedup.normalize_text("ПРИВЕТ МИР ЁЖИК") == "привет мир ёжик"

    # Number removal
    assert dedup.normalize_text("text 123 with 456 numbers") == "text with numbers"
    # Cyrillic with numbers
    assert dedup.normalize_text("текст 123 с 456 цифрами") == "текст с цифрами"

    # Punctuation removal
    assert dedup.normalize_text("hello, world! how are you?") == "hello world how are you"
    # Cyrillic punctuation removal
    assert dedup.normalize_text("привет, мир! как дела?") == "привет мир как дела"

    # Extra space removal and strip
    assert dedup.normalize_text("  too   many    spaces  ") == "too many spaces"

    # Combined complex case (Cyrillic, uppercase, numbers, punctuation, spaces)
    complex_text = "  ЁЖИК  в ТУМАНЕ!!!  1975 года... \n\t Выпуска 12.  "
    assert dedup.normalize_text(complex_text) == "ёжик в тумане года выпуска"

def test_deduplicator():
    from src.deduplicator import Deduplicator
    dedup = Deduplicator(threshold=85.0)

    events = [
        {"timestamp": "1", "text": "Привет, странник"},
        {"timestamp": "2", "text": "Привет, странник!"},
        {"timestamp": "3", "text": "Абсолютно новый текст"},
        {"timestamp": "4", "text": "ок"}, # Too short, should be dropped
    ]

    filtered = dedup.filter_similar_events(events)
    assert len(filtered) == 2
    # The deduplicator should keep the longer string if they are similar
    assert filtered[0]["text"] == "Привет, странник!"
    assert filtered[1]["text"] == "Абсолютно новый текст"

def test_context_selector():
    from src.context_selector import ContextSelector
    # Very small token limit to force sampling
    selector = ContextSelector(max_tokens=10) # ~30 chars

    events = [
        {"timestamp": "1", "text": "1234567890"},
        {"timestamp": "2", "text": "1234567890"},
        {"timestamp": "3", "text": "1234567890"},
        {"timestamp": "4", "text": "1234567890"},
        {"timestamp": "5", "text": "1234567890"}
    ]

    filtered = selector.select_events(events)
    # It replaced 2 with placeholder so length should be 4
    assert len(filtered) < len(events) or (len(events) == 5 and any("пропущена" in e["text"] for e in filtered))
    # Check that chronological order is preserved somewhat, and placeholder is added
    has_placeholder = any("[Часть событий пропущена]" in e.get("text", "") for e in filtered)
    assert has_placeholder

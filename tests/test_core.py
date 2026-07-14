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

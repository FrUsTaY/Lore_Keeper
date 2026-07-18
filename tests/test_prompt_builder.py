import pytest
from src.prompt_builder import PromptBuilder

def test_build_system_prompt_valid_genre():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt("cyberpunk")
    assert "неоновый рассказ" in prompt
    assert "киберпанк" in prompt
    assert "Важный контекст:" not in prompt
    assert "ДОПОЛНИТЕЛЬНЫЕ ПРАВИЛА:" in prompt
    assert "<--- СМЕНА СЦЕНЫ / ПРОШЛО ВРЕМЯ --->" in prompt

def test_build_system_prompt_default_genre():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt("unknown_genre")
    assert "фэнтези" in prompt
    assert "эпическом" in prompt

def test_build_system_prompt_none_genre():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt(None)
    assert "фэнтези" in prompt

def test_build_system_prompt_with_context():
    builder = PromptBuilder()
    context = "Герой нашел магический меч."
    prompt = builder.build_system_prompt("fantasy", entities_context=context)
    assert "фэнтези" in prompt
    assert f"Важный контекст: {context}" in prompt

def test_build_system_prompt_empty_context():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt("fantasy", entities_context="")
    assert "фэнтези" in prompt
    assert "Важный контекст:" not in prompt

def test_build_system_prompt_none_context():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt("fantasy", entities_context=None)
    assert "фэнтези" in prompt
    assert "Важный контекст:" not in prompt

def test_filter_events():
    builder = PromptBuilder()
    events = [
        {"text": "so", "timestamp": "12:00:00"}, # Too short, should be removed
        {"text": "Hello world", "timestamp": "12:00:01"},
        {"text": "I don't know.", "timestamp": "12:00:02"},
        {"text": "I don't know.", "timestamp": "12:00:03"}, # Duplicate, should be removed
        {"text": "I don't know.", "timestamp": "12:00:04"}, # Duplicate, should be removed
        {"text": "и", "timestamp": "12:00:05"}, # Too short, should be removed
        {"text": "What?", "timestamp": "12:00:06"},
        {"text": "What?", "timestamp": "12:00:07"}, # Duplicate, should be removed
        {"text": "Different", "timestamp": "12:00:08"},
    ]
    filtered = builder.filter_events(events)
    assert len(filtered) == 4
    texts = [e["text"] for e in filtered]
    assert texts == ["Hello world", "I don't know.", "What?", "Different"]

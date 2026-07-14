import pytest
from src.prompt_builder import PromptBuilder

def test_build_system_prompt_valid_genre():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt("cyberpunk")
    assert "неоновый рассказ" in prompt
    assert "киберпанк" in prompt
    assert "Важный контекст:" not in prompt

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

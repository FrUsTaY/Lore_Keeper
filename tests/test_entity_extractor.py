import pytest
from unittest.mock import MagicMock
from src.entity_extractor import EntityExtractor

@pytest.fixture
def extractor():
    """Fixture to provide a clean EntityExtractor instance."""
    return EntityExtractor()

def test_extract_entities_empty_events(extractor):
    """Test extracting entities from an empty list of events."""
    assert extractor.extract_entities([]) == ""
    assert extractor.extract_entities(None) == ""

def test_extract_entities_malformed_events(extractor):
    """Test extracting entities when events are missing the 'text' key or have empty text."""
    # Force fallback for this test
    extractor.nlp = None
    events = [
        {"timestamp": "1"}, # Missing text
        {"timestamp": "2", "text": ""}, # Empty text
        {"text": "Иван"}, # appears only once, won't be returned
    ]
    assert extractor.extract_entities(events) == ""

def test_extract_entities_fallback_regex(extractor):
    """Test the naive regex extraction fallback when spaCy is unavailable."""
    extractor.nlp = None

    # 'Иван' and 'Петр' appear twice (not at start of sentence), 'Сергей' once
    events = [
        {"text": "Привет, Иван! Как дела, Иван?"},
        {"text": "Вот Петр. Он видел, как Петр шел домой."},
        {"text": "Сергей тоже там был."}
    ]

    result = extractor.extract_entities(events)
    assert "Ключевые персонажи:" in result
    assert "Иван" in result
    assert "Петр" in result
    assert "Сергей" not in result # Appears only once
    assert "Локации:" not in result # Regex fallback doesn't extract locations

def test_extract_entities_with_spacy(extractor):
    """Test entity extraction using a mocked spaCy model."""
    mock_nlp = MagicMock()
    mock_doc = MagicMock()

    # Mock entities
    ent1 = MagicMock()
    ent1.label_ = "PER"
    ent1.text = "Алиса"

    ent2 = MagicMock()
    ent2.label_ = "PER"
    ent2.text = "Алиса"

    ent3 = MagicMock()
    ent3.label_ = "LOC"
    ent3.text = "Москва"

    ent4 = MagicMock()
    ent4.label_ = "LOC"
    ent4.text = "Москва"

    ent5 = MagicMock()
    ent5.label_ = "PER"
    ent5.text = "Боб" # Appears only once

    mock_doc.ents = [ent1, ent2, ent3, ent4, ent5]
    mock_nlp.return_value = mock_doc

    extractor.nlp = mock_nlp

    events = [
        {"text": "Алиса поехала в Москва. Алиса любит Москва. Боб остался дома."}
    ]

    result = extractor.extract_entities(events)

    assert "Ключевые персонажи:" in result
    assert "Алиса" in result
    assert "Боб" not in result # Appears only once
    assert "Локации:" in result
    assert "Москва" in result

    # Check that nlp was called with the combined text
    mock_nlp.assert_called_once_with("Алиса поехала в Москва. Алиса любит Москва. Боб остался дома.")

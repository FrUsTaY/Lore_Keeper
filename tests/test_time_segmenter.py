import pytest
from src.time_segmenter import TimeGapSegmenter

class MockConfigManager:
    def __init__(self, settings):
        self.settings = settings

    def get(self, key, default=None):
        return self.settings.get(key, default)

def test_time_segmenter_empty_events():
    segmenter = TimeGapSegmenter()
    assert segmenter.segment_events([]) == []

def test_time_segmenter_single_event():
    segmenter = TimeGapSegmenter()
    events = [{"timestamp": "2023-10-25T10:00:00", "text": "Hello"}]
    assert segmenter.segment_events(events) == events

def test_time_segmenter_no_gap():
    segmenter = TimeGapSegmenter()
    events = [
        {"timestamp": "2023-10-25T10:00:00", "text": "Event 1"},
        {"timestamp": "2023-10-25T10:01:00", "text": "Event 2"}
    ]
    # The default gap is 2 minutes, so 1 minute gap should not trigger a marker.
    assert segmenter.segment_events(events) == events

def test_time_segmenter_with_gap():
    segmenter = TimeGapSegmenter()
    events = [
        {"timestamp": "2023-10-25T10:00:00", "text": "Event 1"},
        {"timestamp": "2023-10-25T10:05:00", "text": "Event 2"}
    ]
    segmented = segmenter.segment_events(events)
    assert len(segmented) == 3
    assert segmented[0] == events[0]
    assert segmented[1]["text"] == "<--- СМЕНА СЦЕНЫ / ПРОШЛО ВРЕМЯ --->"
    assert segmented[1]["timestamp"] == "2023-10-25T10:05:00"
    assert segmented[1]["game_window_title"] == "System"
    assert segmented[2] == events[1]

def test_time_segmenter_invalid_timestamp():
    segmenter = TimeGapSegmenter()
    events = [
        {"timestamp": "invalid", "text": "Event 1"},
        {"timestamp": "2023-10-25T10:05:00", "text": "Event 2"}
    ]
    # Invalid timestamp should be ignored, so no marker should be inserted.
    assert segmenter.segment_events(events) == events

def test_time_segmenter_custom_config():
    config = MockConfigManager({"time_gap_limit_minutes": 10})
    segmenter = TimeGapSegmenter(config)

    events = [
        {"timestamp": "2023-10-25T10:00:00", "text": "Event 1"},
        {"timestamp": "2023-10-25T10:05:00", "text": "Event 2"} # 5 mins gap
    ]
    # With limit 10 mins, 5 mins gap should not trigger a marker.
    assert segmenter.segment_events(events) == events

    events2 = [
        {"timestamp": "2023-10-25T10:00:00", "text": "Event 1"},
        {"timestamp": "2023-10-25T10:15:00", "text": "Event 2"} # 15 mins gap
    ]
    # 15 mins gap should trigger a marker.
    segmented = segmenter.segment_events(events2)
    assert len(segmented) == 3
    assert segmented[1]["text"] == "<--- СМЕНА СЦЕНЫ / ПРОШЛО ВРЕМЯ --->"

def test_time_segmenter_string_config():
    config = MockConfigManager({"time_gap_limit_minutes": "10"}) # String value
    segmenter = TimeGapSegmenter(config)

    events = [
        {"timestamp": "2023-10-25T10:00:00", "text": "Event 1"},
        {"timestamp": "2023-10-25T10:15:00", "text": "Event 2"} # 15 mins gap
    ]
    segmented = segmenter.segment_events(events)
    assert len(segmented) == 3
    assert segmented[1]["text"] == "<--- СМЕНА СЦЕНЫ / ПРОШЛО ВРЕМЯ --->"

def test_time_segmenter_invalid_config():
    config = MockConfigManager({"time_gap_limit_minutes": "invalid"})
    segmenter = TimeGapSegmenter(config)
    assert segmenter.time_gap_limit_minutes == 2.0 # Default fallback

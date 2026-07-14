import os
from src.session_manager import SessionManager

def test_session_manager_add_event(tmp_path):
    # Initialize SessionManager with a temporary directory
    manager = SessionManager(logs_dir=str(tmp_path))

    # Check initial state
    assert manager.current_events == []

    # Start a new session
    session_id = manager.start_new_session()
    assert manager.current_session_id == session_id
    assert manager.current_events == []

    # Add an event
    manager.add_event("2023-10-27T10:00:00", "Hello world")

    # Verify the event was added correctly
    assert len(manager.current_events) == 1
    assert manager.current_events[0] == {
        "timestamp": "2023-10-27T10:00:00",
        "text": "Hello world"
    }

    # Add another event
    manager.add_event("2023-10-27T10:01:00", "Second event")
    assert len(manager.current_events) == 2
    assert manager.current_events[1] == {
        "timestamp": "2023-10-27T10:01:00",
        "text": "Second event"
    }

    # Start a new session again and verify that current_events is reset
    new_session_id = manager.start_new_session()
    assert manager.current_session_id == new_session_id
    assert manager.current_events == []

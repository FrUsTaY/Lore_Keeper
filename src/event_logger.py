import json
import os
from datetime import datetime
from src.utils.path_utils import get_path

class EventLogger:
    def __init__(self, session_id=None):
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = session_id
        self.log_file = get_path(f"logs/raw_events_{session_id}.json")
        self.events = []
        self.schema_version = 1

        # Ensure logs dir exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # Load existing if any
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.events = data.get('events', [])
                    self.schema_version = data.get('schema_version', 1)
            except Exception as e:
                print(f"Error loading {self.log_file}: {e}. Starting fresh.")
                self.events = []
                self.schema_version = 1

    def log_event(self, timestamp, text, window_title="Game"):
        event = {
            "timestamp": timestamp,
            "text": text,
            "game_window_title": window_title
        }
        self.events.append(event)

        # Flush every 10 events
        self.flush()

    def flush(self):
        data = {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "events": self.events
        }
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_events(self):
        return self.events

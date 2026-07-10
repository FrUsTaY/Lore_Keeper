import json
import os
from datetime import datetime
from src.utils.path_utils import get_path

class SessionManager:
    def __init__(self, logs_dir="logs"):
        self.logs_dir = get_path(logs_dir)
        os.makedirs(self.logs_dir, exist_ok=True)
        self.current_session_id = None
        self.current_events = []

    def start_new_session(self):
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_events = []
        return self.current_session_id

    def add_event(self, timestamp, text):
        self.current_events.append({
            "timestamp": timestamp,
            "text": text
        })
        # Note: EventLogger already writes to file. This is for GUI state.

    def get_all_sessions(self):
        """Returns list of all session log files and their info."""
        sessions = []
        for f in os.listdir(self.logs_dir):
            if f.startswith("raw_events_") and f.endswith(".json"):
                filepath = os.path.join(self.logs_dir, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        events = data.get('events', [])

                    # Extract date from filename: raw_events_YYYYMMDD_HHMMSS.json
                    date_str = f.replace("raw_events_", "").replace(".json", "")

                    sessions.append({
                        "id": date_str,
                        "file": filepath,
                        "event_count": len(events)
                    })
                except:
                    pass
        # Sort newest first
        sessions.sort(key=lambda x: x["id"], reverse=True)
        return sessions

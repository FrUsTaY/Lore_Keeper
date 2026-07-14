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
        self._sessions_cache = {}

    def start_new_session(self):
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_events = []

        # Pre-create an empty log file so it's visible immediately
        log_file = os.path.join(self.logs_dir, f"raw_events_{self.current_session_id}.json")
        data = {
            "schema_version": 1,
            "session_id": self.current_session_id,
            "events": []
        }
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

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
        current_files = set()

        for f in os.listdir(self.logs_dir):
            if f.startswith("raw_events_") and f.endswith(".json"):
                filepath = os.path.join(self.logs_dir, f)
                current_files.add(filepath)

                try:
                    mtime = os.path.getmtime(filepath)

                    if filepath in self._sessions_cache and self._sessions_cache[filepath]['mtime'] == mtime:
                        sessions.append(self._sessions_cache[filepath]['data'])
                        continue

                    with open(filepath, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        events = data.get('events', [])

                    # Extract date from filename: raw_events_YYYYMMDD_HHMMSS.json
                    date_str = f.replace("raw_events_", "").replace(".json", "")

                    session_data = {
                        "id": date_str,
                        "file": filepath,
                        "event_count": len(events)
                    }

                    self._sessions_cache[filepath] = {
                        'mtime': mtime,
                        'data': session_data
                    }

                    sessions.append(session_data)
                except:
                    pass

        # Remove cached entries for files that no longer exist
        keys_to_remove = [k for k in self._sessions_cache.keys() if k not in current_files]
        for k in keys_to_remove:
            del self._sessions_cache[k]

        # Sort newest first
        sessions.sort(key=lambda x: x["id"], reverse=True)
        return sessions

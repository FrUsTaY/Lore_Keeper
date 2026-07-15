from datetime import datetime, timedelta

class TimeGapSegmenter:
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        # Fallback to 2 minutes if config_manager is not provided
        raw_limit = 2
        if self.config_manager:
            raw_limit = self.config_manager.get("time_gap_limit_minutes", 2)

        try:
            self.time_gap_limit_minutes = float(raw_limit)
        except (ValueError, TypeError):
            self.time_gap_limit_minutes = 2.0

    def segment_events(self, events):
        """
        Iterates through the list of events and inserts a marker event
        if the time gap between consecutive events is greater than time_gap_limit_minutes.
        """
        if not events:
            return []

        segmented_events = []
        previous_time = None

        for event in events:
            timestamp_str = event.get("timestamp")
            if timestamp_str:
                try:
                    current_time = datetime.fromisoformat(timestamp_str)
                    if previous_time is not None:
                        time_diff = current_time - previous_time
                        if time_diff > timedelta(minutes=self.time_gap_limit_minutes):
                            marker_event = {
                                "timestamp": timestamp_str,
                                "text": "<--- СМЕНА СЦЕНЫ / ПРОШЛО ВРЕМЯ --->",
                                "game_window_title": "System"
                            }
                            segmented_events.append(marker_event)
                    previous_time = current_time
                except ValueError:
                    # Ignore invalid timestamp formats
                    pass

            segmented_events.append(event)

        return segmented_events

class ContextSelector:
    def __init__(self, max_tokens=1500):
        # 1 token roughly = 4 chars in Russian, but let's be conservative
        self.max_chars = max_tokens * 3

    def select_events(self, events):
        """
        Selects the most important events if the log is too long.
        """
        if not events:
            return []

        total_chars = sum(len(e.get('text', '')) for e in events)

        if total_chars <= self.max_chars:
            return events

        # Too long, we need to sample.
        # Simplest approach for MVP: Take the first few to establish context,
        # and the last N events which are most relevant to the current session end.

        # Take 20% from start, 80% from end
        target_chars_start = int(self.max_chars * 0.2)
        target_chars_end = self.max_chars - target_chars_start

        start_events = []
        chars_accum = 0
        for e in events:
            if chars_accum > target_chars_start:
                break
            start_events.append(e)
            chars_accum += len(e.get('text', ''))

        end_events = []
        chars_accum = 0
        for e in reversed(events):
            if chars_accum > target_chars_end:
                break
            end_events.append(e) # Keep chronological
            chars_accum += len(e.get('text', ''))

        end_events.reverse()

        # Remove overlaps and maintain the separation for the marker
        result = []
        seen = set()

        # Add start events, deduplicating based on timestamp
        for e in start_events:
            ts = e.get('timestamp')
            if ts not in seen:
                seen.add(ts)
                result.append(e)

        # Add a marker if we skipped events
        if len(result) < len(events) and end_events:
            result.append({"timestamp": "", "text": "... [Часть событий пропущена] ..."})

        # Add end events, deduplicating based on timestamp
        for e in end_events:
            ts = e.get('timestamp')
            if ts not in seen:
                seen.add(ts)
                result.append(e)

        return result

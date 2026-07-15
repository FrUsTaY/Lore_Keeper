class ContextSelector:
    def __init__(self, max_context_tokens=1500):
        # 1 token roughly = 4 chars in Russian, but let's be conservative
        self.max_chars = max_context_tokens * 3

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

        start_events = self._select_start_events(events, target_chars_start)
        end_events = self._select_end_events(events, target_chars_end)

        return self._combine_and_deduplicate(events, start_events, end_events)

    def _select_start_events(self, events, target_chars):
        start_events = []
        chars_accum = 0
        for e in events:
            if chars_accum > target_chars:
                break
            start_events.append(e)
            chars_accum += len(e.get('text', ''))
        return start_events

    def _select_end_events(self, events, target_chars):
        end_events = []
        chars_accum = 0
        for e in reversed(events):
            if chars_accum > target_chars:
                break
            end_events.append(e) # Keep chronological
            chars_accum += len(e.get('text', ''))
            
        end_events.reverse()
        return end_events

        # Remove overlaps and maintain the separation for the marker
    def _combine_and_deduplicate(self, original_events, start_events, end_events):
        result = []
        seen = set()

        # Add start events, deduplicating based on timestamp
        for e in start_events:
            ts = e.get('timestamp')
            if ts not in seen:
                seen.add(ts)
                result.append(e)

        # Calculate the total unique events spanning both start and end selections
        total_unique_events = len(result) + sum(1 for e in end_events if e.get('timestamp') not in seen)

        # If total unique events is less than the total original events, we skipped some
        if total_unique_events < len(original_events):
            result.append({"timestamp": "", "text": "... [Часть событий пропущена] ..."})

        # Add end events, deduplicating based on timestamp
        for e in end_events:
            ts = e.get('timestamp')
            if ts not in seen:
                seen.add(ts)
                result.append(e)

        return result

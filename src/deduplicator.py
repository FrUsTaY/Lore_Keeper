import re
from rapidfuzz import fuzz

class Deduplicator:
    def __init__(self, threshold=85.0):
        # rapidfuzz returns 0-100 ratio
        self.threshold = threshold

    def normalize_text(self, text):
        """Removes extra spaces, punctuation, lowers case."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def levenshtein_ratio(self, str1, str2):
        return fuzz.ratio(str1, str2)

    def filter_similar_events(self, events):
        """
        Filters out events that are too similar to immediately preceding events.
        Also removes very short noise strings.
        """
        if not events:
            return []

        filtered = []
        last_normalized = ""

        for event in events:
            text = event.get('text', '')
            if len(text) < 4: # Drop very short noise
                continue

            norm_text = self.normalize_text(text)

            if not filtered:
                filtered.append(event)
                last_normalized = norm_text
                continue

            ratio = self.levenshtein_ratio(last_normalized, norm_text)

            if ratio >= self.threshold:
                # If they are very similar, keep the longer one as it might have more context
                prev_text = filtered[-1].get('text', '')
                if len(text) > len(prev_text):
                    filtered[-1] = event
                    last_normalized = norm_text
            else:
                filtered.append(event)
                last_normalized = norm_text

        return filtered

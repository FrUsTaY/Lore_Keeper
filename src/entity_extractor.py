import spacy
from collections import Counter
import warnings

class EntityExtractor:
    def __init__(self):
        self.nlp = None
        try:
            # Hide warnings about missing GPU
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.nlp = spacy.load("ru_core_news_sm")
        except OSError:
            print("Внимание: модель spaCy 'ru_core_news_sm' не найдена. NER будет работать в упрощенном режиме (regex).")
            print("Для установки: python -m spacy download ru_core_news_sm")

    def extract_entities(self, events):
        """
        Extracts key characters and locations from the events log.
        Returns a context string to append to the system prompt.
        """
        if not events:
            return ""

        full_text = " ".join([e.get('text', '') for e in events])

        persons = Counter()
        locations = Counter()

        if self.nlp:
            doc = self.nlp(full_text)
            for ent in doc.ents:
                if ent.label_ == "PER":
                    persons[ent.text] += 1
                elif ent.label_ == "LOC":
                    locations[ent.text] += 1
        else:
            # Fallback naive extraction (Words with Capital letters not at sentence start)
            import re
            words = re.findall(r'(?<!^)(?<!\. )\b([A-ZА-Я][a-zа-я]+)\b', full_text)
            for w in words:
                persons[w] += 1

        context_parts = []

        # Get most common entities (e.g., appear more than once)
        common_persons = [p for p, c in persons.items() if c >= 2]
        if common_persons:
            context_parts.append(f"Ключевые персонажи: {', '.join(common_persons[:10])}.")

        common_locs = [l for l, c in locations.items() if c >= 2]
        if common_locs:
            context_parts.append(f"Локации: {', '.join(common_locs[:5])}.")

        return " ".join(context_parts)

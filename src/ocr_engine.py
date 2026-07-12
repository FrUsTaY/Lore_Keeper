import pytesseract
import os
import re
from rapidfuzz import fuzz

def normalize_text(text):
    text = text.lower()
    # Remove numbers to prevent changing timestamps/speeds from bypassing deduplication
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

class OCREngine:
    def __init__(self, use_gpu=False, tesseract_path=None):
        # pytesseract runs on CPU; use_gpu is kept for backward compatibility
        self.last_normalized_text = ""
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_text(self, image_np):
        """
        Extracts text from the given image (which could be an ROI).
        """
        # Using pytesseract on numpy array (which is RGB by default here)
        # Custom config to treat text as a single block or assume specific language
        # psm 6 assumes a single uniform block of text.
        text = pytesseract.image_to_string(image_np, lang='rus+eng', config='--psm 6')

        extracted_lines = []
        for line in text.split('\n'):
            line = line.strip()
            # Require at least one word with 3+ alphabetical characters to filter out noise like 'Ш л т ry _'
            if len(line) >= 3 and re.search(r'[a-zA-Zа-яА-ЯёЁ]{3,}', line):
                extracted_lines.append(line)

        if not extracted_lines:
            return []

        # Deduplicate consecutive reads using normalized text and fuzzy matching
        combined = " ".join(extracted_lines)
        normalized = normalize_text(combined)

        if fuzz.ratio(normalized, self.last_normalized_text) >= 85:
            return []

        self.last_normalized_text = normalized
        return extracted_lines

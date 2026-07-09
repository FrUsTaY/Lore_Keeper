import pytesseract
import os

class OCREngine:
    def __init__(self, use_gpu=False, tesseract_path=None):
        # pytesseract runs on CPU; use_gpu is kept for backward compatibility
        self.last_text = []
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
            if len(line) >= 3:
                extracted_lines.append(line)

        # Deduplicate identical consecutive reads for simple noise reduction
        if extracted_lines == self.last_text:
            return []

        self.last_text = extracted_lines
        return extracted_lines

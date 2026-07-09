import pytesseract

class OCREngine:
    def __init__(self, use_gpu=False):
        # pytesseract runs on CPU; use_gpu is kept for backward compatibility
        self.last_text = []

    def extract_text(self, image_np):
        """
        Extracts text from the given image (which could be an ROI).
        """
        # pytesseract can process numpy arrays directly
        # lang='rus+eng' uses Russian and English language packs
        raw_text = pytesseract.image_to_string(image_np, lang='rus+eng')

        extracted_lines = []
        for line in raw_text.split('\n'):
            text = line.strip()
            # Simple post-processing: filter out very short noise
            if len(text) >= 3:
                extracted_lines.append(text)

        # Deduplicate identical consecutive reads for simple noise reduction
        if extracted_lines == self.last_text:
            return []

        self.last_text = extracted_lines
        return extracted_lines

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
        # easyocr expects RGB or BGR, numpy array is fine
        results = self.reader.readtext(image_np)

        extracted_lines = []
        for (bbox, text, prob) in results:
            text = text.strip()
            # Simple post-processing: filter out very short noise
            if len(text) >= 3:
                extracted_lines.append(text)

        # Deduplicate identical consecutive reads for simple noise reduction
        if extracted_lines == self.last_text:
            return []

        self.last_text = extracted_lines
        return extracted_lines

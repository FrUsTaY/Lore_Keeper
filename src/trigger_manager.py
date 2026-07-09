import time
from datetime import datetime
from src.screen_capture import ScreenCapture
from src.roi_detector import ROIDetector
from src.ring_buffer import RingBuffer
from src.ocr_engine import OCREngine
from src.event_logger import EventLogger
import json

class TriggerManager:
    def __init__(self, config_path="configs/capture_config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.capture_interval = self.config.get("capture_interval", 0.2)
        self.active_interval = self.config.get("active_capture_interval", 1.0)
        self.hash_threshold = self.config.get("hash_threshold", 0.1)
        self.stability_time = self.config.get("stability_time", 2.0)

        self.screencap = ScreenCapture()
        self.roi_detector = ROIDetector()
        self.buffer = RingBuffer(max_size=self.config.get("ring_buffer_size", 30))

        # Load LM studio config just to get tesseract_path for now
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        tesseract_path = cm.get("tesseract_path", "")
        self.ocr = OCREngine(use_gpu=False, tesseract_path=tesseract_path)
        self.logger = EventLogger()

        self.is_running = False
        self.mode = "BACKGROUND" # BACKGROUND or ACTIVE

        self.last_hash = None
        self.last_change_time = 0

    def start(self):
        self.is_running = True
        print(f"Starting TriggerManager. Session: {self.logger.session_id}")

        while self.is_running:
            start_time = time.time()

            # 1. Capture screen
            img = self.screencap.grab_screen()
            current_hash = self.screencap.compute_hash(img)
            timestamp = datetime.now().isoformat()

            # 2. Store in buffer
            self.buffer.append(timestamp, current_hash, img)

            # 3. Detect changes
            if self.last_hash is not None:
                # Calculate normalized hamming distance
                # imagehash phash returns a hash object where (-) operator gives hamming distance
                diff = current_hash - self.last_hash
                normalized_diff = diff / len(current_hash.hash) ** 2

                if normalized_diff > self.hash_threshold:
                    self.mode = "ACTIVE"
                    self.last_change_time = time.time()
                elif time.time() - self.last_change_time > self.stability_time:
                    self.mode = "BACKGROUND"

            self.last_hash = current_hash

            # 4. Process OCR if ACTIVE
            if self.mode == "ACTIVE":
                roi_rect = self.config.get("roi_rect")
                if not roi_rect:
                    roi_rect = self.roi_detector.get_default_roi(img.shape)

                roi_img = self.screencap.get_roi(img, roi_rect)
                lines = self.ocr.extract_text(roi_img)

                if lines:
                    text = " ".join(lines)
                    print(f"[OCR] {text}")
                    self.logger.log_event(timestamp, text)

                    # Save screenshot for debugging
                    import cv2
                    import os
                    os.makedirs("outputs/screenshots", exist_ok=True)
                    # use HHMMSS from timestamp to avoid invalid chars
                    time_str = timestamp.split("T")[-1].replace(":", "")[:6]
                    cv2.imwrite(f"outputs/screenshots/scr_{time_str}.jpg", img)

                # Sleep active interval
                sleep_time = self.active_interval - (time.time() - start_time)
            else:
                # Sleep background interval
                sleep_time = self.capture_interval - (time.time() - start_time)

            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self):
        self.is_running = False
        self.logger.flush()
        print("TriggerManager stopped and logs saved.")

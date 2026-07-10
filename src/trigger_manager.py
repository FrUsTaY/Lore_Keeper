import time
from datetime import datetime
from src.screen_capture import ScreenCapture
from src.roi_detector import ROIDetector
from src.ring_buffer import RingBuffer
from src.ocr_engine import OCREngine
from src.event_logger import EventLogger
import json
from rapidfuzz import fuzz
from src.utils.path_utils import get_path

class TriggerManager:
    def __init__(self, config_path="configs/capture_config.json", session_id=None):
        with open(get_path(config_path), 'r', encoding='utf-8') as f:
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
        self.cm = ConfigManager()
        tesseract_path = self.cm.get("tesseract_path", "")
        self.ocr = OCREngine(use_gpu=False, tesseract_path=tesseract_path)
        self.logger = EventLogger(session_id=session_id)

        self.is_running = False
        self.mode = "BACKGROUND" # BACKGROUND or ACTIVE

        self.last_hash = None
        self.last_change_time = 0
        self.last_screenshot_text = ""
        self.last_screenshot_time = 0

    def start(self):
        self.is_running = True
        print(f"Starting TriggerManager. Session: {self.logger.session_id}")
        consecutive_errors = 0

        while self.is_running:
            start_time = time.time()

            try:
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

                        # Save screenshot if enabled in config
                        save_screenshots = self.cm.get("save_screenshots", True)

                        if save_screenshots:
                            current_time = time.time()
                            similarity = fuzz.ratio(text, self.last_screenshot_text)

                            # Save screenshot only if text is different enough and enough time has passed (e.g. 5 seconds)
                            screenshot_delay = self.config.get("screenshot_delay", 5.0)

                            if similarity < 85.0 and (current_time - self.last_screenshot_time) >= screenshot_delay:
                                import cv2
                                import os
                                screenshots_path = self.cm.get("screenshots_path", "outputs/screenshots")
                                os.makedirs(screenshots_path, exist_ok=True)
                                # use HHMMSS from timestamp to avoid invalid chars
                                time_str = timestamp.split("T")[-1].replace(":", "")[:6]
                                cv2.imwrite(os.path.join(screenshots_path, f"scr_{time_str}.jpg"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

                                self.last_screenshot_text = text
                                self.last_screenshot_time = current_time

                    # Sleep active interval
                    sleep_time = self.active_interval - (time.time() - start_time)
                else:
                    # Sleep background interval
                    sleep_time = self.capture_interval - (time.time() - start_time)

                time.sleep(max(0, sleep_time))

                consecutive_errors = 0

            except Exception as e:
                print(f"Error in TriggerManager loop: {e}")
                consecutive_errors += 1
                if consecutive_errors > 10:
                    print("Too many consecutive errors. Stopping TriggerManager.")
                    self.stop()
                    break
                time.sleep(1.0) # Pause briefly on error

    def stop(self):
        self.is_running = False
        self.logger.flush()
        print("TriggerManager stopped and logs saved.")

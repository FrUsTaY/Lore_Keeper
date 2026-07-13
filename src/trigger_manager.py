import time
from datetime import datetime
import json
from src.utils.path_utils import get_path
from src.event_logger import EventLogger
from src.audio_capture import AudioCapture
from src.audio_transcriber import AudioTranscriber

class TriggerManager:
    def __init__(self, config_path="configs/capture_config.json", session_id=None):
        with open(get_path(config_path), 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.audio_chunk_duration = self.config.get("audio_chunk_duration", 8.0)
        self.silence_threshold = self.config.get("silence_threshold", 0.005)

        # Still keep mss for screenshots if needed
        from src.screen_capture import ScreenCapture
        self.screencap = ScreenCapture()

        from src.config_manager import ConfigManager
        self.cm = ConfigManager()

        # Init Groq
        from src.groq_client import GroqClient
        self.groq_client = GroqClient(self.cm.config)

        self.logger = EventLogger(session_id=session_id)

        # Init Audio
        self.audio_capture = AudioCapture()
        self.transcriber = AudioTranscriber(
            groq_client=self.groq_client,
            logger=self.logger,
            on_transcription_callback=self._on_transcription
        )

        self.is_running = False

    def _on_transcription(self, text):
        """Called when a valid transcription is received. We can take a screenshot here."""
        save_screenshots = self.cm.get("save_screenshots", True)
        if save_screenshots:
            try:
                import cv2
                import os
                img = self.screencap.grab_screen()
                screenshots_path = self.cm.get("screenshots_path", "outputs/screenshots")
                os.makedirs(screenshots_path, exist_ok=True)
                timestamp = datetime.now().isoformat()
                time_str = timestamp.split("T")[-1].replace(":", "")[:6]
                cv2.imwrite(os.path.join(screenshots_path, f"scr_{time_str}.jpg"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            except Exception as e:
                print(f"Error saving screenshot: {e}")

    def start(self):
        self.is_running = True
        print(f"Starting TriggerManager (Audio Mode). Session: {self.logger.session_id}")
        consecutive_errors = 0

        self.transcriber.start()

        while self.is_running:
            try:
                # This will block for self.audio_chunk_duration seconds while recording
                # If silence, it returns None
                timestamp = datetime.now().isoformat()
                audio_data = self.audio_capture.record_chunk(
                    duration=self.audio_chunk_duration,
                    silence_threshold=self.silence_threshold,
                    is_running_callback=lambda: self.is_running
                )

                if audio_data is not None and self.is_running:
                    # Send to queue
                    self.transcriber.add_audio(audio_data, self.audio_capture.sample_rate, timestamp)

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
        self.transcriber.stop()
        self.audio_capture.terminate()
        self.logger.flush()
        print("TriggerManager stopped and logs saved.")

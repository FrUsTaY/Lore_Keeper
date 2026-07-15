from PySide6.QtCore import QThread, Signal
import time
import os
import json
from src.trigger_manager import TriggerManager
from src.story_generator import StoryGenerator

class CaptureWorker(QThread):
    new_event = Signal(str, str) # timestamp, text
    status_changed = Signal(str)
    model_load_error = Signal(str) # Special signal for hard GUI error dialogs

    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        # Override logger to intercept events
        self.trigger_manager = TriggerManager(session_id=self.session_manager.current_session_id)

        # We hook into the trigger manager's logger
        original_log = self.trigger_manager.logger.log_event

        def intercepted_log(timestamp, text, window_title="Game"):
            original_log(timestamp, text, window_title)
            self.session_manager.add_event(timestamp, text)
            self.new_event.emit(timestamp, text)

        self.trigger_manager.logger.log_event = intercepted_log

        # Attach callback for local whisper signal
        if hasattr(self.trigger_manager, 'transcriber'):
            self.trigger_manager.transcriber.on_model_loaded_callback = self._on_model_loaded

        self.is_running = False

    def _on_model_loaded(self, success, message):
        if success:
            self.status_changed.emit(f"Recording ({message})")
        else:
            # If it's a hard error (fallback is disabled), we want to emit an error specifically
            # to be caught by the main window to show a MessageBox, or update status bar
            self.status_changed.emit(f"Ошибка Whisper: {message}")
            if "Fallback to CPU is disabled" in message:
                self.model_load_error.emit(message)

    def run(self):
        self.is_running = True
        self.status_changed.emit("Recording")
        try:
            self.trigger_manager.start()
        except Exception as e:
            self.status_changed.emit(f"Error: {e}")
        finally:
            self.trigger_manager.stop()
            self.status_changed.emit("Idle")
            print("CaptureWorker loop completely finished.")

    def stop(self):
        self.is_running = False
        self.trigger_manager.is_running = False

        # We need to explicitly signal transcriber to stop so queue unblocks
        if hasattr(self.trigger_manager, 'transcriber'):
            self.trigger_manager.transcriber.stop()



class GenerationWorker(QThread):
    progress_update = Signal(str)
    generation_complete = Signal(str, str) # path, text
    generation_error = Signal(str)

    def __init__(self, log_path, config_manager, genre=None):
        super().__init__()
        self.log_path = log_path
        self.config_manager = config_manager
        self.genre = genre
        self.generator = StoryGenerator(config_manager)

    def run(self):
        try:
            self.progress_update.emit("Инициализация генерации...")
            time.sleep(0.5)

            self.progress_update.emit("Отправка запроса в LM Studio (это может занять время)...")
            path, text = self.generator.generate_story_from_log(
                log_path=self.log_path,
                genre=self.genre
            )
            self.generation_complete.emit(path, text)
        except Exception as e:
            self.generation_error.emit(str(e))

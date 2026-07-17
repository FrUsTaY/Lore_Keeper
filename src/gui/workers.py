from PySide6.QtCore import QThread, Signal
import time
import os
import json
from src.trigger_manager import TriggerManager
from src.story_generator import StoryGenerator

class CUDADownloadWorker(QThread):
    progress = Signal(int)
    status_update = Signal(str)
    finished = Signal(bool, str)

    def run(self):
        import requests
        import zipfile
        import tempfile
        import shutil

        # Fallback URLs
        urls = [
            "https://github.com/FrUsTaY/Lore_Keeper/releases/download/cuBLAS.and.cuDNN_CUDA12_win_v1/cuBLAS.and.cuDNN_CUDA12_win_v1.zip"
        ]

        # Target directory in root
        from src.utils.path_utils import get_path
        target_dir = get_path("cuBLAS and cuDNN")

        archive_path = None
        download_success = False

        try:
            for url in urls:
                self.status_update.emit(f"Подключение к серверу...")
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    response = requests.get(url, stream=True, timeout=10, headers=headers)
                    response.raise_for_status()

                    total_size = int(response.headers.get('content-length', 0))

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
                        archive_path = temp_file.name
                        downloaded = 0

                        self.status_update.emit(f"Скачивание компонентов CUDA...")
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                temp_file.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    percent = int((downloaded / total_size) * 100)
                                    # Reserve 0-90% for download, 90-100% for extraction
                                    self.progress.emit(int(percent * 0.9))

                    download_success = True
                    break # Successful download
                except requests.exceptions.RequestException as e:
                    print(f"Failed to download from {url}: {e}")
                    if archive_path and os.path.exists(archive_path):
                        os.remove(archive_path)
                    continue

            if not download_success:
                self.finished.emit(False, "Не удалось скачать архив ни с одного из зеркал. Проверьте подключение к интернету.")
                return

            self.status_update.emit("Распаковка файлов (это может занять пару минут)...")

            # Ensure target directory exists and is clean
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)

            with zipfile.ZipFile(archive_path, 'r') as z:
                z.extractall(path=target_dir)

            self.progress.emit(100)
            self.finished.emit(True, "Компоненты успешно установлены! Пожалуйста, перезапустите программу, чтобы активировать ускорение на вашей видеокарте.")

        except Exception as e:
            self.finished.emit(False, f"Произошла ошибка при установке: {e}")
            if os.path.exists(target_dir):
                try:
                    shutil.rmtree(target_dir)
                except:
                    pass
        finally:
            if archive_path and os.path.exists(archive_path):
                try:
                    os.remove(archive_path)
                except:
                    pass

class CaptureWorker(QThread):
    new_event = Signal(str, str) # timestamp, text
    status_changed = Signal(str)
    model_load_error = Signal(str) # Special signal for hard GUI error dialogs
    transcription_error = Signal(str)

    def __init__(self, session_manager):
        super().__init__()
        self.session_manager = session_manager
        self.trigger_manager = TriggerManager(session_id=self.session_manager.current_session_id)

        # Connect cleanly via callback
        self.trigger_manager.logger.on_new_event_callback = self._on_logger_event
        self.trigger_manager.on_transcription_error_callback = self._on_transcription_error

        # Attach callback for local whisper signal
        if hasattr(self.trigger_manager, 'transcriber'):
            self.trigger_manager.transcriber.on_model_loaded_callback = self._on_model_loaded

        self.is_running = False

    def _on_logger_event(self, timestamp, text, window_title):
        self.session_manager.add_event(timestamp, text)
        self.new_event.emit(timestamp, text)

    def _on_transcription_error(self, error_msg):
        self.transcription_error.emit(error_msg)

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

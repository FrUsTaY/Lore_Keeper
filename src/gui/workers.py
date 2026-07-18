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
            "https://github.com/FrUsTaY/public-releases/releases/download/cuBLAS.and.cuDNN_CUDA12_win_v3/cuBLAS.and.cuDNN_CUDA12_win_v3.zip"
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
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                        'Accept': 'application/octet-stream'
                    }
                    response = requests.get(url, stream=True, timeout=10, headers=headers, allow_redirects=True)
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
    download_requested = Signal(str, str) # title, message

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
            self.trigger_manager.transcriber.on_model_loading_callback = self._on_model_loading
            self.trigger_manager.transcriber.on_download_requested_callback = self._on_download_requested

        self.is_running = False

    def _on_logger_event(self, timestamp, text, window_title):
        self.session_manager.add_event(timestamp, text)
        self.new_event.emit(timestamp, text)

    def _on_transcription_error(self, error_msg):
        self.transcription_error.emit(error_msg)

    def _on_model_loading(self, message):
        self.status_changed.emit(message)

    def _on_download_requested(self, title, message):
        self.download_requested.emit(title, message)

    def set_download_response(self, response):
        if hasattr(self.trigger_manager, 'transcriber') and self.trigger_manager.transcriber.local_transcriber:
            self.trigger_manager.transcriber.local_transcriber.download_response = response
            self.trigger_manager.transcriber.local_transcriber.download_event.set()

    def _on_model_loaded(self, success, message):
        if success:
            self.status_changed.emit(f"Recording ({message})")
        else:
            # If it's a hard error (fallback is disabled), we want to emit an error specifically
            # to be caught by the main window to show a MessageBox, or update status bar
            self.status_changed.emit(f"Ошибка Whisper: {message}")
            if "Fallback to CPU is disabled" in message or "отменена пользователем" in message:
                self.model_load_error.emit(message)

    def run(self):
        self.is_running = True
        self.status_changed.emit("Инициализация захвата...")
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



class TTSWorker(QThread):
    progress = Signal(int)
    status_update = Signal(str)
    download_requested = Signal(str, str, str) # title, message, url
    finished = Signal(bool, str) # success, path_to_audio_or_error_msg

    def __init__(self, text, md_filepath, speaker="xenia"):
        super().__init__()
        self.text = text
        self.md_filepath = md_filepath
        self.speaker = speaker
        self.download_response = None

        import threading
        self.download_event = threading.Event()
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            try:
                import torch
            except ImportError as e:
                print(f"[TTSWorker] Ошибка импорта torch: {e}")
                import traceback
                traceback.print_exc()
                raise

            import requests
            from src.utils.path_utils import get_path

            # Clean up text a bit (Silero TTS has a 1000 char limit usually, and struggles with some markdown)
            # But the user's stories could be longer. Let's just strip basic markdown headers if needed,
            # and limit length if we have to, or rely on Silero's internal chunking if it exists.
            # Actually, standard Silero apply_tts might fail on very long texts.
            # We can split text by sentences or paragraphs if needed, but let's start with basic loading.

            silero_dir = get_path("models/silero")
            os.makedirs(silero_dir, exist_ok=True)
            model_path = os.path.join(silero_dir, "v4_ru.pt")
            model_url = "https://models.silero.ai/models/tts/ru/v4_ru.pt"

            if not os.path.exists(model_path):
                # Request download
                try:
                    response = requests.head(model_url, timeout=10, allow_redirects=True)
                    size_mb = int(response.headers.get('content-length', 0)) / (1024 * 1024)
                except Exception:
                    size_mb = 0

                msg = f"Модель озвучки Silero TTS не найдена.\nСкачать? (~{size_mb:.1f} МБ)"
                self.download_requested.emit("Скачивание модели", msg, model_url)

                # Wait for user response
                self.download_event.wait()
                if not self.download_response:
                    self.finished.emit(False, "Скачивание модели отменена пользователем.")
                    return

                # Perform download
                self.status_update.emit("Скачивание модели Silero TTS...")
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                        'Accept': 'application/octet-stream'
                    }
                    response = requests.get(model_url, stream=True, timeout=10, headers=headers, allow_redirects=True)
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))

                    downloaded = 0
                    with open(model_path + ".tmp", 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if self._is_stopped:
                                os.remove(model_path + ".tmp")
                                self.finished.emit(False, "Остановлено.")
                                return
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    percent = int((downloaded / total_size) * 100)
                                    self.progress.emit(percent)
                    os.rename(model_path + ".tmp", model_path)
                except Exception as e:
                    if os.path.exists(model_path + ".tmp"):
                        os.remove(model_path + ".tmp")
                    self.finished.emit(False, f"Ошибка скачивания: {e}")
                    return

            if self._is_stopped:
                self.finished.emit(False, "Остановлено.")
                return

            self.status_update.emit("Генерация аудио...")

            # Load model
            model = torch.package.PackageImporter(model_path).load_pickle("tts_models", "model")
            model.to(torch.device('cpu'))

            # Clean text (remove some markdown that might trip up TTS)
            import re
            clean_text = re.sub(r'[#*_`~>\[\]\(\)\-\=]', '', self.text)
            clean_text = re.sub(r'\n+', ' ', clean_text)

            # Silero RU model fails with ValueError if it encounters english letters or foreign symbols.
            # We keep only cyrillic, numbers, standard punctuation, and spaces.
            # This regex allows:
            # - Russian letters (а-яА-ЯёЁ)
            # - Numbers (0-9)
            # - Basic punctuation (. , ! ? : ; " ' -)
            # - Whitespace (\s)
            clean_text = re.sub(r'[^а-яА-ЯёЁ0-9\s.,!?:;"\'-]', '', clean_text)

            clean_text = clean_text.strip()

            # Silero v4 typically handles ~1000 chars per pass. We might need to chunk.
            # But apply_tts handles some chunking, though sometimes fails on very large texts.
            # Let's chunk by sentences just in case.
            # A simple sentence splitter using regex
            sentences = re.split(r'(?<=[.!?]) +', clean_text)

            audio_chunks = []
            sample_rate = 48000

            for sent in sentences:
                if self._is_stopped:
                    self.finished.emit(False, "Остановлено.")
                    return
                sent = sent.strip()
                if not sent:
                    continue
                # If a sentence is somehow still > 1000 chars, chunk it by commas or spaces
                while len(sent) > 900:
                    part = sent[:900]
                    audio = model.apply_tts(text=part, speaker=self.speaker, sample_rate=sample_rate)
                    audio_chunks.append(audio)
                    sent = sent[900:]
                if sent:
                    audio = model.apply_tts(text=sent, speaker=self.speaker, sample_rate=sample_rate)
                    audio_chunks.append(audio)

            if not audio_chunks:
                self.finished.emit(False, "Текст для озвучки пуст.")
                return

            if self._is_stopped:
                self.finished.emit(False, "Остановлено.")
                return

            # Concatenate chunks
            final_audio = torch.cat(audio_chunks, dim=0)

            # Save wav using soundfile to avoid torchaudio backend codec issues on Windows
            output_wav = self.md_filepath.rsplit('.', 1)[0] + ".wav"
            import soundfile as sf

            # Convert torch tensor to numpy array (1D)
            audio_numpy = final_audio.numpy()

            # Write to disk
            sf.write(output_wav, audio_numpy, sample_rate)

            self.finished.emit(True, output_wav)

        except Exception as e:
            print(f"[TTSWorker] Ошибка генерации аудио: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"Ошибка генерации аудио: {e}")


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

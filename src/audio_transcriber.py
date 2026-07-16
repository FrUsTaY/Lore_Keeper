import threading
import queue
import time
import os
import logging
import tempfile
from src.groq_client import GroqClient
from src.local_transcriber import LocalWhisperTranscriber
import soundfile as sf

class AudioTranscriber:
    def __init__(self, groq_client: GroqClient, logger, on_transcription_callback=None, on_error_callback=None):
        self.client = groq_client
        self.logger = logger
        self.queue = queue.Queue()
        self.is_running = False
        self.thread = None
        self.on_transcription = on_transcription_callback
        self.on_error_callback = on_error_callback

        self.local_transcriber = None

        # Миграция
        provider = self.client.config.get("audio_provider", "Облако (Groq API)")
        if provider in ["Groq API", "LM Studio (Custom URL)", "Облачный (Groq API)"]:
            self.provider = "Облако (Groq API)"
        elif provider in ["Local Whisper (CPU/GPU)", "Локальный (Встроенный движок)"]:
            self.provider = "Локально (Встроенный движок Faster-Whisper)"
        else:
            self.provider = provider

        self.model_size = self.client.config.get("local_whisper_model", "large-v3-turbo")
        self.whisper_device = self.client.config.get("whisper_device", "auto")

        # Ensure temp directory exists
        self.temp_dir = "outputs/temp_audio"
        os.makedirs(self.temp_dir, exist_ok=True)

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            # push a dummy item to wake up the queue if it's blocking
            try:
                self.queue.put(None, block=False)
            except queue.Full as e:
                logging.warning(f"Queue full when trying to stop: {e}")
            self.thread.join(timeout=2.0)

    def add_audio(self, audio_data, sample_rate, timestamp):
        """Adds audio data to the queue to be transcribed."""
        # We save it to a temporary file first because Groq expects a file
        try:
            with tempfile.NamedTemporaryFile(delete=False, dir=self.temp_dir, suffix=".wav") as temp_file:
                filename = temp_file.name

            sf.write(filename, audio_data, sample_rate)
            self.queue.put((filename, timestamp))
        except Exception as e:
            print(f"Error saving temp audio: {e}")

    def _process_queue(self):
        # Initialize Local Whisper lazily in the background thread to avoid freezing GUI or silent crashes during init
        if self.provider == "Локально (Встроенный движок Faster-Whisper)":
            try:
                self.local_transcriber = LocalWhisperTranscriber(model_size=self.model_size, device=self.whisper_device)

                # Expose the signal so the CaptureWorker can catch it and forward to GUI
                if hasattr(self, 'on_model_loaded_callback') and self.on_model_loaded_callback:
                    self.local_transcriber.signals.model_loaded.connect(self.on_model_loaded_callback)

                # Pre-load model asynchronously
                self.local_transcriber.load_model_async()
            except Exception as e:
                print(f"Failed to initialize Local Whisper model: {e}")
                self.local_transcriber = None
                self.is_running = False

        while self.is_running:
            # Check if using local provider and it's still loading
            if self.provider == "Локально (Встроенный движок Faster-Whisper)" and self.local_transcriber:
                if not self.local_transcriber.is_ready:
                    if self.local_transcriber.is_loading:
                        # If model is actively loading, sleep and continue so chunks queue up without blocking
                        time.sleep(1.0)
                        continue
                    else:
                        # Model failed to load completely. Stop processing local transcription to avoid infinite loop.
                        print("Local Whisper model failed to initialize. Disabling local transcription.")
                        self.local_transcriber = None
                        self.is_running = False
                        break

            try:
                item = self.queue.get(timeout=1.0)
                if item is None:
                    continue

                filename, timestamp = item

                start_time = time.time()

                try:
                    # Transcribe
                    if self.provider == "Локально (Встроенный движок Faster-Whisper)" and self.local_transcriber:
                        text = self.local_transcriber.transcribe(filename)
                    elif self.provider == "Облако (Groq API)":
                        text = self.client.transcribe_audio(filename)
                    else:
                        text = "" # Fallback if local transcriber failed to load
                finally:
                    # Remove temp file
                    try:
                        os.remove(filename)
                    except OSError as e:
                        logging.warning(f"Failed to remove temp file {filename}: {e}")

                if text and text.strip():
                    # Check if it's a hallucination or meaningless
                    # Whisper sometimes hallucinates "[Silence]", "[Music]", etc.
                    clean_text = self._clean_whisper_text(text)
                    if clean_text:
                        print(f"[Whisper] {clean_text}")
                        self.logger.log_event(timestamp, clean_text)

                        if self.on_transcription:
                            self.on_transcription(clean_text)

                # Rate limit: Wait 2.5 seconds between requests to avoid 429 Too Many Requests
                elapsed_time = time.time() - start_time
                sleep_time = 2.5 - elapsed_time
                time.sleep(max(0.0, sleep_time))
                self.queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                error_msg = f"Ошибка транскрибации: {e}"
                print(error_msg)
                if self.on_error_callback:
                    self.on_error_callback(error_msg)
                time.sleep(2.0) # wait before retrying

    def _clean_whisper_text(self, text):
        import re
        # Remove common Whisper hallucinations that are in brackets
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = text.strip()

        # If the string is empty or just punctuation
        if not re.search(r'[a-zA-Zа-яА-ЯёЁ]', text):
            return ""

        return text

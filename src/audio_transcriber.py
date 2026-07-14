import threading
import queue
import time
import os
from src.groq_client import GroqClient
from src.local_transcriber import LocalWhisperTranscriber
import soundfile as sf
from datetime import datetime

class AudioTranscriber:
    def __init__(self, groq_client: GroqClient, logger, on_transcription_callback=None):
        self.client = groq_client
        self.logger = logger
        self.queue = queue.Queue()
        self.is_running = False
        self.thread = None
        self.on_transcription = on_transcription_callback

        self.local_transcriber = None
        self.provider = self.client.config.get("audio_provider", "Groq API")
        self.model_size = self.client.config.get("local_whisper_model", "base")

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
            except:
                pass
            self.thread.join(timeout=2.0)

    def add_audio(self, audio_data, sample_rate, timestamp):
        """Adds audio data to the queue to be transcribed."""
        # We save it to a temporary file first because Groq expects a file
        filename = os.path.join(self.temp_dir, f"chunk_{int(time.time()*1000)}.wav")
        try:
            sf.write(filename, audio_data, sample_rate)
            self.queue.put((filename, timestamp))
        except Exception as e:
            print(f"Error saving temp audio: {e}")

    def _process_queue(self):
        # Initialize Local Whisper lazily in the background thread to avoid freezing GUI or silent crashes during init
        if self.provider == "Local Whisper (CPU/GPU)":
            try:
                self.local_transcriber = LocalWhisperTranscriber(model_size=self.model_size)
                # Pre-load model to catch errors early in the thread
                self.local_transcriber._load_model()
            except Exception as e:
                print(f"Failed to initialize Local Whisper model: {e}")
                self.local_transcriber = None
                self.is_running = False

        while self.is_running:
            try:
                item = self.queue.get(timeout=1.0)
                if item is None:
                    continue

                filename, timestamp = item

                start_time = time.time()

                # Transcribe
                if self.provider == "Local Whisper (CPU/GPU)" and self.local_transcriber:
                    text = self.local_transcriber.transcribe(filename)
                elif self.provider != "Local Whisper (CPU/GPU)":
                    text = self.client.transcribe_audio(filename)
                else:
                    text = "" # Fallback if local transcriber failed to load

                # Remove temp file
                try:
                    os.remove(filename)
                except:
                    pass

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
                print(f"Transcription error: {e}")
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

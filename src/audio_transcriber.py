import threading
import queue
import time
import os
from src.groq_client import GroqClient
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
            self.queue.put(None)
            self.thread.join()

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
        while self.is_running:
            try:
                item = self.queue.get(timeout=1.0)
                if item is None:
                    continue

                filename, timestamp = item

                # Transcribe
                text = self.client.transcribe_audio(filename)

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
                time.sleep(2.5)
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

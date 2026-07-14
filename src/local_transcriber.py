import os

class LocalWhisperTranscriber:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None

    def _load_model(self):
        if self.model is None:
            print(f"Loading local Whisper model ({self.model_size})...")
            try:
                from faster_whisper import WhisperModel
                # Run on GPU with FP16 if available, else CPU with INT8
                self.model = WhisperModel(self.model_size, device="auto", compute_type="default")
                print("Local Whisper model loaded successfully.")
            except Exception as e:
                print(f"\n[CRITICAL ERROR] Error loading local Whisper model: {e}")
                print("This might happen due to missing CUDA libraries or out of memory errors.")
                raise e

    def transcribe(self, file_path):
        if not os.path.exists(file_path):
            return ""

        try:
            self._load_model()
            segments, info = self.model.transcribe(file_path, beam_size=5)
            text = " ".join([segment.text for segment in segments])
            return text.strip()
        except Exception as e:
            print(f"Local transcription error: {e}")
            return ""

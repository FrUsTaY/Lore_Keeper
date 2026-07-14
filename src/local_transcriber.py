import os
import ctypes
import threading

class LocalWhisperTranscriber:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None
        self.is_loading = False
        self.is_ready = False

    def load_model_async(self, callback=None):
        if self.is_loading or self.is_ready:
            return

        self.is_loading = True

        def load_task():
            # Fix silent OpenMP crash in GUI applications
            os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
            print(f"[Local Whisper] Starting initialization for model size '{self.model_size}'...")

            try:
                from faster_whisper import WhisperModel

                cuda_available = False
                try:
                    ctypes.CDLL('nvcuda.dll')
                    cuda_available = True
                    print("[Local Whisper] NVIDIA CUDA detected (nvcuda.dll loaded).")
                except Exception as e:
                    print(f"[Local Whisper] CUDA not detected or nvcuda.dll missing: {e}")

                if cuda_available:
                    try:
                        print(f"[Local Whisper] Attempting to load model '{self.model_size}' on CUDA (float16)...")
                        self.model = WhisperModel(
                            self.model_size,
                            device="cuda",
                            compute_type="float16"
                        )
                        print("[Local Whisper] Model loaded successfully on CUDA.")
                    except Exception as e:
                        print(f"[Local Whisper] Failed to load on CUDA: {e}. Falling back to CPU.")
                        cuda_available = False

                if not cuda_available:
                    # CRITICAL: Prevent silent crash on AMD Ryzen 3 3200U (Vega) and similar CPUs
                    os.environ["CTRANSLATE2_CPU_ISA_TO_USE"] = "GENERIC"
                    print("[Local Whisper] Applying fallback: CTRANSLATE2_CPU_ISA_TO_USE=GENERIC (Disabled AVX2).")
                    print(f"[Local Whisper] Attempting to load model '{self.model_size}' on CPU (float32)...")

                    self.model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="float32",
                        cpu_threads=4
                    )
                    print("[Local Whisper] Model loaded successfully on CPU.")

                self.is_ready = True
                if callback:
                    callback(True)

            except Exception as e:
                print(f"\n[CRITICAL ERROR] Error loading local Whisper model: {e}")
                print("This might happen due to missing libraries or out of memory errors.")
                self.is_ready = False
                if callback:
                    callback(False)
            finally:
                self.is_loading = False

        thread = threading.Thread(target=load_task, daemon=True)
        thread.start()

    def transcribe(self, file_path):
        if not os.path.exists(file_path):
            return ""

        if not self.is_ready or self.model is None:
            print("[Local Whisper] Model is not ready yet. Skipping transcription.")
            return ""

        try:
            segments, info = self.model.transcribe(file_path, beam_size=5)
            text = " ".join([segment.text for segment in segments])
            return text.strip()
        except Exception as e:
            print(f"Local transcription error: {e}")
            return ""

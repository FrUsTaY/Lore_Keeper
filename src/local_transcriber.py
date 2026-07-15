import os
import ctypes
import threading
import logging
import sys
import site
from PySide6.QtCore import QObject, Signal

class LocalWhisperSignals(QObject):
    model_loaded = Signal(bool, str)

class FasterWhisperEngine:
    def __init__(self, model_size):
        self.model_size = model_size
        self.model = None

    def load(self):
        from faster_whisper import WhisperModel, download_model

        print(f"[FasterWhisper] Resolving absolute path for model '{self.model_size}'...")
        model_path = download_model(self.model_size, local_files_only=False)
        print(f"[FasterWhisper] Resolved model path: {model_path}")

        print(f"[FasterWhisper] Attempting to load model on CUDA (float16)...")
        self.model = WhisperModel(
            model_path,
            device="cuda",
            compute_type="float16"
        )
        print("[FasterWhisper] Model loaded successfully on CUDA.")

    def transcribe(self, file_path):
        if self.model is None:
            return ""

        lang_env = os.environ.get("WHISPER_LANGUAGE", "auto").strip().lower()
        if lang_env == "auto" or lang_env == "":
            lang = None
        else:
            lang = lang_env

        segments, info = self.model.transcribe(
            file_path,
            beam_size=5,
            task="transcribe",
            language=lang
        )
        return " ".join([segment.text for segment in segments]).strip()

class WhisperCppEngine:
    def __init__(self, model_size):
        self.model_size = model_size
        self.model = None

    def load(self):
        from huggingface_hub import hf_hub_download
        from pywhispercpp.model import Model

        filename = f"ggml-{self.model_size}.bin"
        print(f"[Whisper.cpp] Downloading/Resolving GGML model '{filename}' from ggerganov/whisper.cpp...")

        # Download the GGML model (or get path if cached)
        model_path = hf_hub_download(repo_id="ggerganov/whisper.cpp", filename=filename)
        print(f"[Whisper.cpp] Resolved model path: {model_path}")

        print(f"[Whisper.cpp] Attempting to load model on CPU...")

        lang_env = os.environ.get("WHISPER_LANGUAGE", "auto").strip().lower()
        if lang_env == "auto" or lang_env == "":
            lang = "auto"
        else:
            lang = lang_env

        self.model = Model(
            model_path,
            n_threads=4,
            print_realtime=False,
            print_progress=False,
            translate=False,
            language=lang
        )
        print("[Whisper.cpp] Model loaded successfully on CPU.")

    def transcribe(self, file_path):
        if self.model is None:
            return ""

        # whisper.cpp usually requires 16kHz WAV. The temp_audio from AudioTranscriber
        # is saved using soundfile, typically using the sample rate from the WASAPI loopback
        # (often 44.1kHz or 48kHz). However, if there are sample rate issues we might need to resample.
        # But for now we try passing the file directly, or use librosa if we have to.
        # pywhispercpp actually has a helper or can transcribe from file directly.
        # However, the transcribe method expects numpy arrays or handles it internally if we pass a file?
        # Let's read it properly using soundfile and resample to 16000.

        import soundfile as sf
        import numpy as np

        # librosa is standard for resampling, but we don't have it in requirements.
        # Let's try native soundfile / scipy if we need to resample, or rely on whisper_cpp internal tools if available.
        # pywhispercpp Model.transcribe(audio) -> audio is 1D array of type float32 at 16kHz
        import scipy.signal

        audio_data, sr = sf.read(file_path, dtype='float32')
        if len(audio_data.shape) > 1:
            # Convert to mono
            audio_data = np.mean(audio_data, axis=1)

        if sr != 16000:
            # Resample to 16kHz using scipy
            num_samples = round(len(audio_data) * float(16000) / sr)
            audio_data = scipy.signal.resample(audio_data, num_samples)

        # pywhispercpp expects a numpy array.
        segments = self.model.transcribe(audio_data)

        # pywhispercpp returns a list of Segment objects which have a `text` attribute
        text_parts = []
        try:
            for segment in segments:
                if hasattr(segment, 'text'):
                    text_parts.append(segment.text)
        except (TypeError, AttributeError) as e:
            logging.error(f"[Whisper.cpp] Error parsing transcription segments: {e}")
            pass

        return " ".join(text_parts).strip()

class LocalWhisperTranscriber:
    def __init__(self, model_size="base", device="auto"):
        self.model_size = model_size
        self.device = device
        self.engine = None
        self.is_loading = False
        self.is_ready = False
        self.signals = LocalWhisperSignals()

    def load_model_async(self):
        if self.is_loading or self.is_ready:
            return

        self.is_loading = True

        def load_task():
            print(f"[Local Whisper Adapter] Starting initialization for model size '{self.model_size}' (device={self.device})...")

            try:
                # Add DLL paths if we are on Windows and not forcing CPU
                if os.name == 'nt' and self.device in ['auto', 'gpu']:
                    site_packages = site.getsitepackages()
                    site_packages.append(site.getusersitepackages())
                    if hasattr(sys, 'real_prefix') or sys.prefix != sys.base_prefix:
                        # Inside virtualenv or venv
                        site_packages.insert(0, os.path.join(sys.prefix, 'Lib', 'site-packages'))

                    for sp in site_packages:
                        cublas_path = os.path.join(sp, 'nvidia', 'cublas', 'bin')
                        cudnn_path = os.path.join(sp, 'nvidia', 'cudnn', 'bin')
                        cuda_rt_path = os.path.join(sp, 'nvidia', 'cuda_runtime', 'bin')

                        for p in [cublas_path, cudnn_path, cuda_rt_path]:
                            if os.path.exists(p):
                                try:
                                    os.add_dll_directory(p)
                                    print(f"[Local Whisper Adapter] Added DLL directory: {p}")
                                except Exception as dll_err:
                                    print(f"[Local Whisper Adapter] Failed to add DLL directory {p}: {dll_err}")

                cuda_available = False
                cuda_error_msg = ""

                if self.device in ['auto', 'gpu']:
                    # Try loading basic nvcuda.dll first
                    try:
                        ctypes.CDLL('nvcuda.dll')
                        print("[Local Whisper Adapter] NVIDIA CUDA detected (nvcuda.dll loaded).")
                        cuda_available = True
                    except Exception as e:
                        cuda_error_msg = f"nvcuda.dll not found: {e}"
                        print(f"[Local Whisper Adapter] {cuda_error_msg}")

                    if cuda_available and os.name == 'nt':
                        # Check critical DLLs for faster-whisper (CTranslate2/cuDNN)
                        test_dlls = ['cublas64_12.dll', 'cudnn_ops_infer64_8.dll']
                        for dll in test_dlls:
                            try:
                                ctypes.WinDLL(dll)
                                print(f"[Local Whisper Adapter] Successfully tested load of {dll}")
                            except OSError as e:
                                cuda_available = False
                                winerror = getattr(e, 'winerror', 'Unknown')
                                cuda_error_msg = f"Missing DLL: {dll} (WinError {winerror})"
                                print(f"[Local Whisper Adapter] {cuda_error_msg}")
                                break

                if self.device == 'gpu' and not cuda_available:
                    raise RuntimeError(f"GPU initialization failed: {cuda_error_msg}. Fallback to CPU is disabled in settings.")

                if cuda_available:
                    print("[Local Whisper Adapter] Selecting FasterWhisperEngine (GPU mode).")
                    self.engine = FasterWhisperEngine(self.model_size)
                    try:
                        self.engine.load()
                        self.is_ready = True
                        self.signals.model_loaded.emit(True, "Loaded on GPU")
                        return
                    except Exception as e:
                        error_msg = f"FasterWhisperEngine failed: {e}"
                        print(f"[Local Whisper Adapter] {error_msg}")
                        if self.device == 'gpu':
                            raise RuntimeError(f"GPU initialization failed during model load: {e}. Fallback to CPU is disabled.")
                        else:
                            print("[Local Whisper Adapter] Falling back to CPU Engine.")
                            cuda_available = False
                            self.signals.model_loaded.emit(False, f"[Whisper] Не удалось запустить GPU ({error_msg}). Автоматически переключено на CPU")

                if not cuda_available or self.device == 'cpu':
                    print("[Local Whisper Adapter] Selecting WhisperCppEngine (CPU mode).")
                    self.engine = WhisperCppEngine(self.model_size)
                    self.engine.load()
                    self.is_ready = True

                    if self.device == 'auto' and cuda_error_msg:
                        # Emitting False with the message so the warning is shown, but we actually loaded CPU
                        # CaptureWorker handles this via status_changed string
                        self.signals.model_loaded.emit(False, f"[Whisper] Не удалось запустить GPU ({cuda_error_msg}). Автоматически переключено на CPU")
                    else:
                        self.signals.model_loaded.emit(True, "Loaded on CPU")

            except Exception as e:
                print(f"\n[CRITICAL ERROR] Error loading local Whisper model via Adapter: {e}")
                self.is_ready = False
                self.signals.model_loaded.emit(False, str(e))
            finally:
                self.is_loading = False

        thread = threading.Thread(target=load_task, daemon=True)
        thread.start()

    def transcribe(self, file_path):
        if not os.path.exists(file_path):
            return ""

        if not self.is_ready or self.engine is None:
            print("[Local Whisper Adapter] Engine is not ready yet. Skipping transcription.")
            return ""

        try:
            return self.engine.transcribe(file_path)
        except Exception as e:
            print(f"Local transcription error: {e}")
            return ""

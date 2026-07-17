import os
import ctypes
import threading
import logging
import sys
import site
import subprocess
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from src.utils.gpu_tester import _preload_cuda_dlls

class LocalWhisperSignals(QObject):
    model_loaded = Signal(bool, str)
    model_loading = Signal(str)

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

    def unload(self):
        import gc
        print("[FasterWhisper] Unloading model and clearing GPU VRAM...")
        self.model = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        print("[FasterWhisper] Model unloaded.")

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

        # pywhispercpp Model.transcribe(audio) -> audio is 1D array of type float32 at 16kHz

        audio_data, sr = sf.read(file_path, dtype='float32')
        if len(audio_data.shape) > 1:
            # Convert to mono
            audio_data = np.mean(audio_data, axis=1)

        if sr != 16000:
            # Resample to 16kHz using numpy interp to avoid external heavy dependencies like scipy/librosa
            num_samples = round(len(audio_data) * float(16000) / sr)
            old_indices = np.arange(len(audio_data))
            new_indices = np.linspace(0, len(audio_data) - 1, num_samples)
            audio_data = np.interp(new_indices, old_indices, audio_data).astype(np.float32)

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

    def unload(self):
        import gc
        print("[Whisper.cpp] Unloading model from CPU RAM...")
        self.model = None
        gc.collect()
        print("[Whisper.cpp] Model unloaded.")

class LocalWhisperTranscriber:
    def __init__(self, model_size="base", device="auto"):
        self.model_size = model_size
        self.device = device
        self.engine = None
        self.is_loading = False
        self.is_ready = False
        self.signals = LocalWhisperSignals()

    def unload_model(self):
        print("[Local Whisper Adapter] Unloading model...")
        if self.engine:
            self.engine.unload()
            self.engine = None
        self.is_ready = False
        self.is_loading = False
        print("[Local Whisper Adapter] Model successfully unloaded.")

    def load_model_async(self):
        if self.is_loading or self.is_ready:
            return

        self.is_loading = True

        def load_task():
            print(f"[Local Whisper Adapter] Starting initialization for model size '{self.model_size}' (device={self.device})...")

            try:
                cuda_available = False
                cuda_error_msg = ""

                # Add DLL paths and preload them if we are on Windows and not forcing CPU
                if os.name == 'nt' and self.device in ['auto', 'gpu']:
                    cuda_available, cuda_error_msg = _preload_cuda_dlls()
                    if cuda_available:
                        print("[Local Whisper Adapter] Successfully pre-loaded all CUDA DLLs.")
                    else:
                        print(f"[Local Whisper Adapter] Failed to pre-load CUDA DLLs: {cuda_error_msg}")

                if self.device == 'gpu' and not cuda_available:
                    raise RuntimeError(f"GPU initialization failed: {cuda_error_msg}. Fallback to CPU is disabled in settings.")

                if cuda_available:
                    self.signals.model_loading.emit("Инициализация и загрузка GPU модели (может занять время)...")
                    print("[Local Whisper Adapter] Spawning isolated subprocess to test GPU initialization safely...")
                    script_path = Path(__file__).parent / "utils" / "gpu_tester.py"
                    cmd_args = [sys.executable, str(script_path), str(self.model_size)]
                    print(f"[Local Whisper Adapter] Debug subprocess cmd: {cmd_args}")
                    try:
                        result = subprocess.run(
                            cmd_args,
                            capture_output=True,
                            text=True,
                            timeout=15
                        )
                        if result.returncode == 0:
                            print("[Local Whisper Adapter] Isolated test passed. Selecting FasterWhisperEngine (GPU mode) in main process.")
                            self.engine = FasterWhisperEngine(self.model_size)
                            try:
                                self.engine.load()
                                self.is_ready = True
                                self.signals.model_loaded.emit(True, "Loaded on GPU")
                                return
                            except Exception as e:
                                error_msg = f"FasterWhisperEngine failed during main process load: {e}"
                                print(f"[Local Whisper Adapter] {error_msg}")
                                if self.device == 'gpu':
                                    raise RuntimeError(f"GPU initialization failed during model load: {e}. Fallback to CPU is disabled.")
                                else:
                                    print("[Local Whisper Adapter] Falling back to CPU Engine.")
                                    cuda_available = False
                                    self.signals.model_loaded.emit(False, f"[Whisper] Не удалось запустить GPU ({error_msg}). Автоматически переключено на CPU")
                        else:
                            error_msg = f"GPU process test failed (exit code {result.returncode}). Stdout: {result.stdout} Stderr: {result.stderr}"
                            print(f"[Local Whisper Adapter] {error_msg}")
                            if self.device == 'gpu':
                                raise RuntimeError(f"GPU initialization test failed: {error_msg}. Fallback to CPU is disabled.")
                            else:
                                print("[Local Whisper Adapter] Falling back to CPU Engine.")
                                cuda_available = False
                                self.signals.model_loaded.emit(False, f"[Whisper] Запуск GPU привел к сбою ({result.returncode}). Автоматически переключено на CPU")
                    except subprocess.TimeoutExpired:
                        error_msg = "GPU process test timed out."
                        print(f"[Local Whisper Adapter] {error_msg}")
                        if self.device == 'gpu':
                            raise RuntimeError(f"GPU initialization test failed: {error_msg}. Fallback to CPU is disabled.")
                        else:
                            print("[Local Whisper Adapter] Falling back to CPU Engine.")
                            cuda_available = False
                            self.signals.model_loaded.emit(False, f"[Whisper] Запуск GPU привел к сбою (Timeout). Автоматически переключено на CPU")

                if not cuda_available or self.device == 'cpu':
                    print("[Local Whisper Adapter] Selecting WhisperCppEngine (CPU mode).")
                    self.engine = WhisperCppEngine(self.model_size)

                    if self.device == 'auto' and cuda_error_msg:
                        self.signals.model_loading.emit(f"[Whisper] Не удалось запустить GPU ({cuda_error_msg}). Автоматически переключено на CPU. Начинается загрузка модели...")
                    else:
                        self.signals.model_loading.emit("Инициализация и загрузка CPU модели (может занять время)...")

                    self.engine.load()
                    self.is_ready = True
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

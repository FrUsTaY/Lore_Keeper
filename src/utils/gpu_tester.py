import os
import sys
import ctypes
from pathlib import Path

# Add project root to sys.path so 'src.utils...' imports work when run as standalone subprocess
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def _clean_nvidia_paths():
    """Removes any paths containing 'nvidia' from sys.path and os.environ['PATH']."""
    sys.path = [p for p in sys.path if 'nvidia' not in p.lower()]
    path_env = os.environ.get("PATH", "")
    if path_env:
        paths = path_env.split(os.pathsep)
        clean_paths = [p for p in paths if 'nvidia' not in p.lower()]
        os.environ["PATH"] = os.pathsep.join(clean_paths)

def _preload_cuda_dlls():
    if os.name != 'nt':
        return True, ""

    _clean_nvidia_paths()
    from src.utils.path_utils import get_path
    dll_path = get_path("cuBLAS and cuDNN")

    if os.path.exists(dll_path):
        os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")
        try:
            os.add_dll_directory(dll_path)
        except Exception:
            pass

    try:
        ctypes.CDLL('nvcuda.dll')
    except Exception as e:
        return False, f"nvcuda.dll not found: {e}"

    test_dlls = [
        'cublas64_12.dll',
        'cublasLt64_12.dll',
        'cudnn64_9.dll',
        'cudnn_ops64_9.dll',
        'cudnn_adv64_9.dll',
        'cudnn_cnn64_9.dll',
        'cudnn_engines_precompiled64_9.dll',
        'cudnn_engines_runtime_compiled64_9.dll',
        'cudnn_graph64_9.dll',
        'cudnn_heuristic64_9.dll'
    ]

    for dll in test_dlls:
        try:
            full_dll_path = os.path.join(dll_path, dll)
            if os.path.exists(full_dll_path):
                ctypes.CDLL(full_dll_path)
            else:
                ctypes.CDLL(dll)
        except OSError as e:
            winerror = getattr(e, 'winerror', 'Unknown')
            return False, f"Missing DLL: {dll} (WinError {winerror})"

    return True, ""

def test_gpu_init(model_size):
    """
    Isolated test function to try initializing the Faster Whisper engine on GPU.
    Runs in a separate process.
    """
    # Force clean paths immediately
    _clean_nvidia_paths()

    try:
        success, error_msg = _preload_cuda_dlls()
        if not success:
            print(f"[Isolated GPU Test] Failed to preload DLLs: {error_msg}")
            sys.exit(1)

        from faster_whisper import WhisperModel, download_model

        print(f"[Isolated GPU Test] Resolving absolute path for model '{model_size}'...")
        model_path = download_model(model_size, local_files_only=False)

        print(f"[Isolated GPU Test] Attempting to load model on CUDA (float16)...")
        _ = WhisperModel(
            model_path,
            device="cuda",
            compute_type="float16"
        )
        print("[Isolated GPU Test] Model loaded successfully on CUDA.")
        sys.exit(0)
    except Exception as e:
        print(f"[Isolated GPU Test] Exception during load: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gpu_tester.py <model_size>")
        sys.exit(1)

    model_size = sys.argv[1]
    test_gpu_init(model_size)

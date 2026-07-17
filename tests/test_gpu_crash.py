import os
import sys
import ctypes
import faulthandler
from faster_whisper import WhisperModel, download_model

# Enable faulthandler to catch segfaults and print tracebacks
faulthandler.enable()

def _clean_nvidia_paths():
    print("Cleaning NVIDIA paths from sys.path and PATH...")
    sys.path = [p for p in sys.path if 'nvidia' not in p.lower()]
    path_env = os.environ.get("PATH", "")
    if path_env:
        paths = path_env.split(os.pathsep)
        clean_paths = [p for p in paths if 'nvidia' not in p.lower()]
        os.environ["PATH"] = os.pathsep.join(clean_paths)

def load_dlls():
    print("Loading cuDNN 9 DLLs...")

    # Add project root to path for local execution testing
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    dll_path = os.path.join(project_root, "cuBLAS and cuDNN")

    if not os.path.exists(dll_path):
        print(f"Warning: DLL path does not exist: {dll_path}")
        return False

    os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(dll_path)
            print(f"Added DLL directory: {dll_path}")
        except Exception as e:
            print(f"Error adding DLL directory: {e}")

    try:
        ctypes.CDLL('nvcuda.dll')
        print("NVIDIA CUDA detected (nvcuda.dll loaded).")
    except Exception as e:
        print(f"nvcuda.dll not found: {e}")
        return False

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

    success = True
    for dll in test_dlls:
        try:
            full_dll_path = os.path.join(dll_path, dll)
            if os.path.exists(full_dll_path):
                ctypes.CDLL(full_dll_path)
                print(f"Explicitly loaded: {full_dll_path}")
            else:
                ctypes.CDLL(dll)
                print(f"Explicitly loaded from system: {dll}")
        except OSError as e:
            winerror = getattr(e, 'winerror', 'Unknown')
            print(f"Missing DLL: {dll} (WinError {winerror})")
            success = False
            break

    return success

def run_model_test(compute_type, model_size="large-v3-turbo"):
    print(f"\n--- Testing Model Initialization ---")
    print(f"Model Size: {model_size}")
    print(f"Compute Type: {compute_type}")

    try:
        print(f"Resolving absolute path for model '{model_size}'...")
        model_path = download_model(model_size, local_files_only=False)
        print(f"Resolved model path: {model_path}")

        print(f"Attempting to load model on CUDA with compute_type='{compute_type}'...")
        model = WhisperModel(
            model_path,
            device="cuda",
            compute_type=compute_type
        )
        print(f"SUCCESS: Model loaded successfully with compute_type='{compute_type}'.")
    except Exception as e:
        print(f"FAILED: Exception during model load: {e}")

if __name__ == "__main__":
    print("Starting GPU Crash Test Script...")

    _clean_nvidia_paths()

    if not load_dlls():
        print("\nFailed to load necessary DLLs. Aborting test.")
        sys.exit(1)

    print("\nDLL loading completed. Proceeding to initialize models.")

    # Test float16 first
    run_model_test("float16")

    # Test int8_float16
    run_model_test("int8_float16")

    print("\nTesting complete.")
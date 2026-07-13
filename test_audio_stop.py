import pyaudiowpatch as pyaudio
p = pyaudio.PyAudio()
try:
    p.terminate()
    print("Terminated successfully")
except Exception as e:
    print(f"Error terminating: {e}")

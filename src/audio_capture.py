import numpy as np
import time

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    # Fallback for non-Windows environments (e.g. testing)
    pyaudio = None

class AudioCapture:
    def __init__(self, sample_rate=44100, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        if pyaudio:
            self.p = pyaudio.PyAudio()
            self.device_index = self._get_loopback_device()
        else:
            self.p = None
            self.device_index = None

    def _get_loopback_device(self):
        """Finds the WASAPI Loopback device."""
        if not self.p:
            return None

        try:
            # Get default WASAPI info
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = self.p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

            if not default_speakers["isLoopbackDevice"]:
                for loopback in self.p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        return loopback["index"]
            else:
                return default_speakers["index"]
        except Exception as e:
            print(f"Error finding loopback device: {e}")

        # Fallback to finding any loopback
        try:
            for loopback in self.p.get_loopback_device_info_generator():
                return loopback["index"]
        except:
            pass

        return None

    def record_chunk(self, duration=10.0, silence_threshold=0.01, is_running_callback=None):
        """Records a chunk of audio and returns it if above silence threshold."""
        if not self.p:
            # Mock behavior for testing on linux
            for _ in range(int(duration)):
                if is_running_callback and not is_running_callback():
                    break
                time.sleep(1.0)
            return None # Simulate silence

        if self.device_index is None:
            # Try to re-detect
            self.device_index = self._get_loopback_device()
            if self.device_index is None:
                raise Exception("No WASAPI Loopback device found.")

        frames = []
        try:
            device_info = self.p.get_device_info_by_index(self.device_index)
            # WASAPI loopback requires exact match of sample rate and channels
            native_channels = int(device_info["maxInputChannels"])
            native_rate = int(device_info["defaultSampleRate"])

            # Store the native values so transcriber knows how to write it
            self.sample_rate = native_rate
            self.channels = native_channels

            stream = self.p.open(format=pyaudio.paInt16,
                                 channels=native_channels,
                                 rate=native_rate,
                                 input=True,
                                 input_device_index=self.device_index,
                                 frames_per_buffer=self.chunk_size)

            total_chunks = int(native_rate / self.chunk_size * duration)
            for i in range(total_chunks):
                if is_running_callback and not is_running_callback():
                    break

                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(np.frombuffer(data, dtype=np.int16))

            stream.stop_stream()
            stream.close()

            if not frames:
                return None

            audio_data = np.hstack(frames)
            # Reshape based on channels so soundfile can write it properly
            if native_channels > 1:
                audio_data = audio_data.reshape(-1, native_channels)

            # Normalize to float32 [-1.0, 1.0] for processing
            audio_float = audio_data.astype(np.float32) / 32768.0

            # Check volume (if stereo, mean across all works fine for RMS)
            rms = np.sqrt(np.mean(audio_float**2))
            if rms < silence_threshold:
                return None

            return audio_float

        except OSError as e:
            # Device might have disconnected, reset index
            print(f"Audio capture error: {e}")
            self.device_index = None
            raise

    def terminate(self):
        if self.p:
            self.p.terminate()

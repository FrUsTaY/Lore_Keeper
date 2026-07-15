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
        self.stream = None
        self.channels = 1

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

    def start_stream(self):
        """Opens the PyAudio stream once to prevent memory leaks."""
        if not self.p:
            return

        if self.device_index is None:
            self.device_index = self._get_loopback_device()
            if self.device_index is None:
                raise Exception("No WASAPI Loopback device found.")

        device_info = self.p.get_device_info_by_index(self.device_index)
        self.channels = int(device_info["maxInputChannels"])
        self.sample_rate = int(device_info["defaultSampleRate"])

        self.stream = self.p.open(format=pyaudio.paInt16,
                             channels=self.channels,
                             rate=self.sample_rate,
                             input=True,
                             input_device_index=self.device_index,
                             frames_per_buffer=self.chunk_size)

    def stop_stream(self):
        """Closes the active stream."""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None

    def record_chunk(self, duration=10.0, min_volume_db=-25, is_running_callback=None):
        """Reads from the open stream for `duration` seconds."""
        if not self.p:
            # Mock behavior for testing on linux
            for _ in range(int(duration)):
                if is_running_callback and not is_running_callback():
                    break
                time.sleep(1.0)
            return None # Simulate silence

        if not self.stream:
            self.start_stream()

        frames = []
        try:
            total_chunks = int(self.sample_rate / self.chunk_size * duration)
            for i in range(total_chunks):
                if is_running_callback and not is_running_callback():
                    break

                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(np.frombuffer(data, dtype=np.int16))

            if not frames:
                return None

            audio_data = np.hstack(frames)

            if self.channels > 1:
                audio_data = audio_data.reshape(-1, self.channels)

            # Normalize to float32 [-1.0, 1.0] for processing
            audio_float = audio_data.astype(np.float32) / 32768.0

            # Check volume in dB
            rms = np.sqrt(np.mean(audio_float**2))
            volume_db = 20 * np.log10(rms + 1e-10) # add small epsilon to avoid log10(0)
            if volume_db < min_volume_db:
                return None

            return audio_float

        except OSError as e:
            # Device might have disconnected, reset index and stream
            import logging
            logging.error(f"Audio capture error (possible device disconnect): {e}")
            self.stop_stream()
            self.device_index = None
            raise

    def terminate(self):
        self.stop_stream()
        if self.p:
            self.p.terminate()

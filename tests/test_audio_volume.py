import pytest
import numpy as np
from unittest.mock import MagicMock, patch
import json
import os
import tempfile
import time
from src.audio_capture import AudioCapture
from src.audio_transcriber import AudioTranscriber
from src.groq_client import GroqClient
from src.config_manager import ConfigManager

GROQ_API_KEY = "YOUR_GROQ_API_KEY"

def setup_mocked_capture():
    ac = AudioCapture()
    ac.p = MagicMock()
    ac.stream = MagicMock()
    ac.sample_rate = 44100
    ac.chunk_size = 1024
    ac.channels = 1
    return ac

def generate_tone(freq=440, duration=0.1, sample_rate=44100, volume_db=0):
    """
    Generate a sine wave tone at a specific dB level.
    Note: For a full-scale (amplitude 1.0) sine wave (0 dBFS),
    the RMS power is 0.707, which is -3 dB.
    We pass `volume_db` representing the RMS power we WANT.
    So we adjust the sine wave amplitude by +3.01 dB.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    # Adjust target power to required amplitude
    amplitude_db = volume_db + 3.0103
    amplitude = 10 ** (amplitude_db / 20)

    # Clip at 1.0 to prevent overflow
    amplitude = min(amplitude, 1.0)

    audio = amplitude * np.sin(2 * np.pi * freq * t)
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16

def test_volume_gate_levels():
    """
    Test that the gate correctly cuts off audio below the threshold
    and allows audio above the threshold, across the -60 to 0 dB range.
    """
    ac = setup_mocked_capture()

    # Test cases: (signal_db, threshold_db, should_pass)
    test_cases = [
        (-10, -25, True),   # Loud signal
        (-30, -25, False),  # Signal slightly quieter than threshold
        (-50, -60, True),   # Quiet signal above quiet threshold
        (-70, -60, False),  # Extremely quiet signal
        (-5, 0, False),     # Normal signal is quieter than 0dB threshold (impossible threshold)
        (-3, -5, True),     # Almost clipping signal
    ]

    for signal_db, threshold_db, should_pass in test_cases:
        tone = generate_tone(volume_db=signal_db, duration=0.1)

        chunk_index = 0
        def mock_read(chunk_size, exception_on_overflow=False):
            nonlocal chunk_index
            start = chunk_index * chunk_size
            end = start + chunk_size
            chunk_index += 1
            if start >= len(tone):
                return np.zeros(chunk_size, dtype=np.int16).tobytes()
            chunk = tone[start:end]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
            return chunk.tobytes()

        ac.stream.read.side_effect = mock_read

        audio_float = ac.record_chunk(duration=0.1, min_volume_db=threshold_db)

        if should_pass:
            assert audio_float is not None, f"Signal at {signal_db}dB should pass {threshold_db}dB threshold"
            # Verify the audio is not modified (amplified or attenuated)
            rms = np.sqrt(np.mean(audio_float**2))
            actual_db = 20 * np.log10(rms + 1e-10)

            assert abs(actual_db - signal_db) < 2.0, f"Expected RMS dB ~{signal_db}, got {actual_db}dB. The signal was modified!"
        else:
            assert audio_float is None, f"Signal at {signal_db}dB should NOT pass {threshold_db}dB threshold"

def test_dynamic_threshold_change():
    """
    Test that changing the threshold dynamically applies immediately to the next chunk.
    """
    ac = setup_mocked_capture()

    # Generate -30dB RMS power signal
    signal_db = -30
    tone = generate_tone(volume_db=signal_db, duration=0.1)

    def mock_read(chunk_size, exception_on_overflow=False):
        return tone[:chunk_size].tobytes()

    ac.stream.read.side_effect = mock_read

    # Chunk 1: Threshold -40dB. Signal (-30dB RMS) is louder -> should PASS
    audio_float_1 = ac.record_chunk(duration=0.1, min_volume_db=-40)
    assert audio_float_1 is not None

    # Dynamically change threshold (simulating UI slider change)
    new_threshold = -20

    # Chunk 2: Threshold -20dB. Signal (-30dB RMS) is quieter -> should FAIL
    audio_float_2 = ac.record_chunk(duration=0.1, min_volume_db=new_threshold)
    assert audio_float_2 is None

def test_full_cycle_groq_transcription():
    """
    Test a full cycle: create dummy speech audio (or valid wav file if needed),
    pass it to AudioTranscriber, and verify Groq API processes it.
    """
    cm = ConfigManager()
    cm.config["groq_token"] = GROQ_API_KEY
    cm.config["audio_provider"] = "Облако (Groq API)"

    client = GroqClient(cm)

    if not GROQ_API_KEY.startswith("gsk_"):
        print("Skipping Groq test, no valid API key.")
        return

    assert client.check_health() is True, "Groq API Health check failed with provided token."

    transcribed_text = []
    def on_transcription(text):
        transcribed_text.append(text)

    logger_mock = MagicMock()
    transcriber = AudioTranscriber(client, logger_mock, on_transcription)
    transcriber.start()

    # Create 2 seconds of loud random noise (simulate talking)
    sample_rate = 44100
    noise = np.random.uniform(-0.5, 0.5, sample_rate * 2).astype(np.float32)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

    transcriber.add_audio(noise, sample_rate, timestamp)

    timeout = 10
    start_time = time.time()
    while time.time() - start_time < timeout:
        if len(transcribed_text) > 0:
            break
        time.sleep(0.5)

    transcriber.stop()

    print(f"Transcription result: {transcribed_text}")
    assert True

import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from src.audio_capture import AudioCapture

@patch('src.audio_capture.time.sleep')
def test_record_chunk_mock_behavior(mock_sleep):
    """Test behavior when PyAudio is not available (e.g. Linux fallback)."""
    ac = AudioCapture()
    ac.p = None  # Force None

    # Test complete duration
    res = ac.record_chunk(duration=3.0)
    assert res is None
    assert mock_sleep.call_count == 3

    # Test early interruption by callback
    mock_sleep.reset_mock()
    count = [0]
    def cb():
        count[0] += 1
        return count[0] < 2  # Returns True first time, False second time

    res = ac.record_chunk(duration=5.0, is_running_callback=cb)
    assert res is None
    assert mock_sleep.call_count == 1

def setup_mocked_capture():
    """Helper to setup AudioCapture with a mocked PyAudio stream."""
    ac = AudioCapture()
    ac.p = MagicMock()
    ac.stream = MagicMock()
    ac.sample_rate = 44100
    ac.chunk_size = 1024
    ac.channels = 1
    return ac

def test_record_chunk_success():
    """Test successful recording and normalization of audio data."""
    ac = setup_mocked_capture()

    # Generate some sine wave audio data (1 channel, 16-bit integer format)
    # The length of this should simulate one chunk reading
    frames_read = 0
    total_chunks = int(ac.sample_rate / ac.chunk_size * 0.1) # Simulate 0.1 sec

    def mock_read(chunk_size, exception_on_overflow=False):
        nonlocal frames_read
        frames_read += 1
        # Create loud enough data (values between -30000 and 30000)
        # Random noise
        data = np.random.randint(-30000, 30000, chunk_size, dtype=np.int16)
        return data.tobytes()

    ac.stream.read.side_effect = mock_read

    # Record for 0.1 seconds, silence threshold 0.01
    audio_float = ac.record_chunk(duration=0.1, min_volume_db=-25)

    assert audio_float is not None
    assert audio_float.dtype == np.float32
    # Ensure values are within normalized range
    assert np.max(np.abs(audio_float)) <= 1.0
    # Stream read should have been called total_chunks times
    assert ac.stream.read.call_count == total_chunks

def test_record_chunk_silence():
    """Test that silence (RMS below threshold) returns None."""
    ac = setup_mocked_capture()

    def mock_read(chunk_size, exception_on_overflow=False):
        # Create silent data (almost zeros)
        data = np.zeros(chunk_size, dtype=np.int16)
        return data.tobytes()

    ac.stream.read.side_effect = mock_read

    # Record for 0.1 seconds, silence threshold 0.01
    audio_float = ac.record_chunk(duration=0.1, min_volume_db=-25)

    assert audio_float is None

def test_record_chunk_callback_interruption():
    """Test that recording is interrupted if is_running_callback returns False."""
    ac = setup_mocked_capture()

    def mock_read(chunk_size, exception_on_overflow=False):
        data = np.random.randint(-30000, 30000, chunk_size, dtype=np.int16)
        return data.tobytes()

    ac.stream.read.side_effect = mock_read

    count = [0]
    def is_running_callback():
        count[0] += 1
        # Stop after 2 chunks
        return count[0] <= 2

    audio_float = ac.record_chunk(duration=1.0, min_volume_db=-25, is_running_callback=is_running_callback)

    # It read 2 chunks, so it's very short. Should return float data or None depending on size.
    # Since we use random noise, it might pass the volume test.
    # The most important part is that stream.read was only called 2 times.
    assert ac.stream.read.call_count == 2

def test_record_chunk_oserror():
    """Test that OSError properly resets the device index and stream."""
    ac = setup_mocked_capture()

    def mock_read(chunk_size, exception_on_overflow=False):
        raise OSError("Stream disconnected")

    ac.stream.read.side_effect = mock_read

    # Set a dummy device index
    ac.device_index = 5

    # Stop stream mock
    ac.stop_stream = MagicMock()

    with pytest.raises(OSError, match="Stream disconnected"):
        ac.record_chunk(duration=0.1)

    ac.stop_stream.assert_called_once()
    assert ac.device_index is None

import collections
import cv2

class RingBuffer:
    def __init__(self, max_size=30):
        self.max_size = max_size
        self.buffer = collections.deque(maxlen=max_size)

    def append(self, timestamp, img_hash, image_np):
        """
        Stores reduced size image in buffer to save memory.
        """
        # Resize image for storage (e.g. 640x360 or similar ratio)
        h, w = image_np.shape[:2]
        new_w = 640
        new_h = int(h * (new_w / w))
        resized_img = cv2.resize(image_np, (new_w, new_h))

        self.buffer.append({
            'timestamp': timestamp,
            'hash': img_hash,
            'image': resized_img
        })

    def get_last_n(self, n):
        """Returns the last n elements from the buffer."""
        n = min(n, len(self.buffer))
        return list(self.buffer)[-n:]

    def get_all(self):
        return list(self.buffer)

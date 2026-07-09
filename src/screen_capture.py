import mss
import cv2
import numpy as np
from PIL import Image
import imagehash

class ScreenCapture:
    def __init__(self):
        pass

    def grab_screen(self):
        """Grabs the primary screen."""
        with mss.mss() as sct:
            monitor = sct.monitors[1] # Primary monitor
            sct_img = sct.grab(monitor)
            # Convert to BGR for cv2 if needed, but returning RGB numpy array is standard
            img = np.array(sct_img)
            # Drop alpha channel
            img = img[:, :, :3]
            return img

    def compute_hash(self, image_np):
        """Computes perceptual hash of a numpy image."""
        # Convert numpy array (RGB) to PIL Image
        pil_img = Image.fromarray(image_np)
        return imagehash.phash(pil_img)

    def get_roi(self, image_np, region):
        """
        Extracts Region of Interest from an image.
        region: tuple (x, y, width, height)
        """
        if not region:
            return image_np
        x, y, w, h = region
        # Ensure we don't go out of bounds
        max_h, max_w = image_np.shape[:2]
        x_end = min(x + w, max_w)
        y_end = min(y + h, max_h)
        return image_np[y:y_end, x:x_end]

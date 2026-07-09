import cv2
import numpy as np

class ROIDetector:
    def __init__(self):
        self.default_region = None

    def find_roi(self, sample_images):
        """
        In a real scenario, this might analyze multiple frames to find
        the static dialog box. For MVP, we default to the bottom third of the screen.
        """
        if not sample_images:
            return None

        # Take the first image to get dimensions
        img = sample_images[0]
        h, w = img.shape[:2]

        # Default ROI: Bottom 1/3 of the screen
        roi_y = int(h * 2 / 3)
        roi_h = h - roi_y

        self.default_region = (0, roi_y, w, roi_h)
        return self.default_region

    def get_default_roi(self, image_shape):
        """Returns bottom third based on shape"""
        h, w = image_shape[:2]
        roi_y = int(h * 2 / 3)
        roi_h = h - roi_y
        return (0, roi_y, w, roi_h)

"""
Image pre-processing and post-processing utilities for Anime2Sketch.
Incorporates CLAHE (Contrast Limited Adaptive Histogram Equalization)
and dynamic range scaling.
"""

import cv2
import numpy as np

def enhance_clahe_contrast(img_bgr, clip_limit=2.0, tile_grid_size=(8, 8)):
    """
    Applies CLAHE to the Luminance (L) channel in LAB color space.
    Enhances faint sketch strokes and separates ink from paper background.
    """
    if img_bgr is None:
        return None
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    cl = clahe.apply(l)
    merged = cv2.merge((cl, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

def prepare_image_for_sketch(img_bgr, target_size=None, apply_clahe=True):
    """
    Normalizes and prepares an image for sketch extraction.
    """
    out = img_bgr.copy()
    if target_size is not None:
        out = cv2.resize(out, target_size, interpolation=cv2.INTER_AREA)
    if apply_clahe:
        out = enhance_clahe_contrast(out, clip_limit=1.8)
    return out

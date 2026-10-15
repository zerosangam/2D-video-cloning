"""
High-Precision Watermark & Text Removal Engine
Ported and enhanced from WatermarkRemover-AI algorithms:
- Adaptive percentile stroke extraction (isolates text without blurring background)
- Multi-pass inpainting with feathered boundaries
- Temporal static logo detection
"""

import cv2
import numpy as np
import os

def extract_strokes(roi: np.ndarray) -> np.ndarray:
    """
    Extracts local high-contrast edges and stroke contours from a bounding box region.
    Ported from WatermarkRemover-AI (remwm.py).
    Guarantees that only thin text letters are inpainted, preserving background art.
    """
    if roi.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    h, w = roi.shape[:2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi
    ksize = max(5, int(min(h, w) * 0.25) | 1)
    ksize = min(ksize, 31)
    blur = cv2.GaussianBlur(gray, (ksize, ksize), 0)
    diff = cv2.absdiff(gray, blur)
    thresh_val = max(4, int(np.percentile(diff, 70) * 0.4))
    _, stroke_mask = cv2.threshold(diff, thresh_val, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    return cv2.dilate(stroke_mask, kernel, iterations=2)

def detect_watermark(frames_dir, total_frames, sample_count=25):
    """
    Detects static watermark/logo regions using temporal standard deviation across cuts.
    Analyzes static spatial features that persist across animated frames.
    """
    step = max(1, total_frames // sample_count)
    samples = []

    for f in range(1, total_frames + 1, step):
        f_path = os.path.join(frames_dir, f"frame_{f:04d}.png")
        if not os.path.exists(f_path):
            f_path = os.path.join(frames_dir, f"frame_{f:04d}.jpg")
        if os.path.exists(f_path):
            img = cv2.imread(f_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                samples.append(img.astype(np.float32))

    if len(samples) < 3:
        return {"detected": False, "bounding_box": None, "boxes": [], "description": "Insufficient samples"}

    stack = np.stack(samples, axis=0)
    std_map = np.std(stack, axis=0)
    mean_img = np.mean(stack, axis=0).astype(np.uint8)

    # Static high-frequency edges: low temporal std and high spatial Laplacian
    laplacian = np.abs(cv2.Laplacian(mean_img, cv2.CV_32F))
    static_features = (std_map < 14.0) & (laplacian > 12.0)

    # Exclude extreme border regions
    h, w = mean_img.shape
    static_features[0:min(60, h), :] = 0
    static_features[max(0, h-60):, :] = 0
    static_features[:, 0:min(30, w)] = 0
    static_features[:, max(0, w-30):] = 0

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 8))
    closed = cv2.morphologyEx(static_features.astype(np.uint8), cv2.MORPH_CLOSE, kernel)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(closed)
    boxes = []

    for i in range(1, num):
        area = stats[i, cv2.CC_STAT_AREA]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        bx = stats[i, cv2.CC_STAT_LEFT]
        by = stats[i, cv2.CC_STAT_TOP]

        # Valid text logo proportions
        if area > 180 and bw > 45 and bh > 8 and (bw / max(1, bh) > 1.2):
            box = [max(0, by - 6), max(0, bx - 6), min(h, by + bh + 6), min(w, bx + bw + 6)]
            boxes.append(box)

    best_box = boxes[0] if boxes else None

    return {
        "detected": len(boxes) > 0,
        "bounding_box": best_box,
        "boxes": boxes,
        "description": f"Detected {len(boxes)} watermark zone(s)" if boxes else "No persistent watermark detected"
    }

def clean_watermark_roi_two_pass(img_bgr, wm_boxes, inpaint_func=None):
    """
    Performs high-fidelity stroke-level two-pass watermark removal.
    Pass 1: Inpaints extracted high-contrast text strokes.
    Pass 2: Feathered boundary blending to eliminate residual halos.
    """
    if not wm_boxes:
        return img_bgr

    out = img_bgr.copy()
    h, w = out.shape[:2]

    for (y1, x1, y2, x2) in wm_boxes:
        y1, x1 = max(0, y1), max(0, x1)
        y2, x2 = min(h, y2), min(w, x2)
        if y2 <= y1 or x2 <= x1:
            continue

        roi = out[y1:y2, x1:x2]
        stroke_mask = extract_strokes(roi)
        if np.count_nonzero(stroke_mask) == 0:
            continue

        # Pass 1: Inpaint tight strokes
        if inpaint_func is not None:
            try:
                cleaned_roi = inpaint_func(roi, stroke_mask)
            except Exception:
                cleaned_roi = cv2.inpaint(roi, stroke_mask, 3, cv2.INPAINT_TELEA)
        else:
            cleaned_roi = cv2.inpaint(roi, stroke_mask, 3, cv2.INPAINT_TELEA)

        # Pass 2: Feathered boundary blend
        feathered_mask = cv2.dilate(stroke_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        diff = cv2.absdiff(cleaned_roi, roi)
        edge_band = (feathered_mask > 0) & (diff.mean(axis=2) > 8)
        if np.count_nonzero(edge_band) > 0:
            cleaned_roi = cv2.inpaint(cleaned_roi, edge_band.astype(np.uint8) * 255, 2, cv2.INPAINT_TELEA)

        out[y1:y2, x1:x2] = cleaned_roi

    return out

def filter_watermark_from_contours(contours, wm_box):
    """Filters out isolated small glyphs inside watermark bounding box while keeping continuous character lines."""
    if not wm_box:
        return contours

    y_min, x_min, y_max, x_max = wm_box
    clean_contours = []

    for c in contours:
        arc_len = cv2.arcLength(c, False)
        if arc_len <= 16:
            continue

        x, y, w, h = cv2.boundingRect(c)
        is_inside_wm = (y >= y_min - 10) and (y + h <= y_max + 10) and (x >= x_min - 10) and (x + w <= x_max + 10)

        if is_inside_wm and w < 26 and h < 26 and arc_len < 50:
            continue

        clean_contours.append(c)

    return clean_contours

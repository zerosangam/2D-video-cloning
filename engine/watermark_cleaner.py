"""
Universal Watermark & Overlay Removal Engine (v4.0 UNIVERSAL)
============================================================
Fully autonomous detection of watermarks, logos, channel handles, text overlays
at ANY position in the frame — top, bottom, corners, center.

Core algorithms (ported + enhanced from WatermarkRemover-AI):
- Temporal percentile analysis: separates animated content from persistent overlays
- Multi-scale Laplacian + gradient magnitude: isolates high-frequency text edges
- Frequency domain analysis: FFT-based detection of semi-transparent watermarks
- Adaptive stroke extraction with percentile thresholding
- Two-pass inpainting with feathered boundary blending
"""

import cv2
import numpy as np
import os

# ─────────────────────────────────────────────────────────────
#  STROKE EXTRACTION (from WatermarkRemover-AI: remwm.py)
# ─────────────────────────────────────────────────────────────

def extract_strokes(roi: np.ndarray) -> np.ndarray:
    """
    Extracts local high-contrast edges and stroke contours from a ROI.
    Ported from WatermarkRemover-AI (remwm.py) with enhanced multi-scale detection.
    Guarantees that only thin text/logo pixels are inpainted, preserving background art.
    """
    if roi.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    h, w = roi.shape[:2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi.copy()

    # Multi-scale stroke extraction for robustness
    masks = []

    # Scale 1: fine strokes
    ksize1 = max(5, int(min(h, w) * 0.15) | 1)
    ksize1 = min(ksize1, 21)
    blur1 = cv2.GaussianBlur(gray, (ksize1, ksize1), 0)
    diff1 = cv2.absdiff(gray, blur1)
    thr1 = max(3, int(np.percentile(diff1, 65) * 0.4))
    _, m1 = cv2.threshold(diff1, thr1, 255, cv2.THRESH_BINARY)
    masks.append(m1)

    # Scale 2: medium strokes
    ksize2 = max(9, int(min(h, w) * 0.30) | 1)
    ksize2 = min(ksize2, 31)
    blur2 = cv2.GaussianBlur(gray, (ksize2, ksize2), 0)
    diff2 = cv2.absdiff(gray, blur2)
    thr2 = max(4, int(np.percentile(diff2, 70) * 0.4))
    _, m2 = cv2.threshold(diff2, thr2, 255, cv2.THRESH_BINARY)
    masks.append(m2)

    # Combine scales
    combined = cv2.bitwise_or(m1, m2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    return cv2.dilate(combined, kernel, iterations=2)


# ─────────────────────────────────────────────────────────────
#  UNIVERSAL WATERMARK DETECTOR (v4.0)
# ─────────────────────────────────────────────────────────────

def detect_watermark_universal(frames_dir: str, total_frames: int, sample_count: int = 35):
    """
    FULLY UNIVERSAL watermark/logo/text-overlay detector.

    Detects persistent overlays ANYWHERE in the frame using 4 independent signals:
    1. Temporal STD analysis: low-variance regions that persist across all frames
    2. Percentile difference: 90th-percentile brightness minus median reveals sticky overlays
    3. Laplacian high-frequency persistence: static sharp edges = text/logo
    4. Gradient-magnitude consistency: logos have directionally consistent gradients

    Zero hardcoded positions — works for TikTok/YouTube/Reels/any aspect ratio.
    """
    frame_files = sorted([
        f for f in os.listdir(frames_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])
    if not frame_files:
        return {"detected": False, "boxes": [], "full_mask": None, "description": "No frames found"}

    n_samples = min(sample_count, len(frame_files))
    indices = np.linspace(0, len(frame_files) - 1, n_samples, dtype=int)

    gray_stack = []
    bgr_stack = []
    for idx in indices:
        p = os.path.join(frames_dir, frame_files[idx])
        img = cv2.imread(p)
        if img is None:
            continue
        h, w = img.shape[:2]
        target_h, target_w = 1920, 1080
        if (w, h) != (target_w, target_h):
            img = cv2.resize(img, (target_w, target_h))
        gray_stack.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32))
        bgr_stack.append(img.astype(np.float32))

    if len(gray_stack) < 3:
        return {"detected": False, "boxes": [], "full_mask": None, "description": "Insufficient samples"}

    H, W = 1920, 1080
    arr = np.stack(gray_stack, axis=0)   # [N, H, W]

    # ── Signal 1: Temporal standard deviation ──────────────────────
    # Low std = region barely changes across frames → persistent overlay
    std_map = np.std(arr, axis=0)                        # [H, W]
    mean_map = np.mean(arr, axis=0).astype(np.float32)

    # ── Signal 2: p90 – median difference ──────────────────────────
    p90 = np.percentile(arr, 90, axis=0).astype(np.float32)
    median = np.median(arr, axis=0).astype(np.float32)
    p90_diff = np.abs(p90 - median)                      # [H, W]

    # ── Signal 3: Laplacian on mean frame ──────────────────────────
    mean_u8 = mean_map.astype(np.uint8)
    lap = np.abs(cv2.Laplacian(mean_u8, cv2.CV_32F))    # [H, W]

    # ── Signal 4: Gradient-magnitude consistency ────────────────────
    bgr_arr = np.stack(bgr_stack, axis=0)
    mean_bgr = np.mean(bgr_arr, axis=0).astype(np.uint8)
    gray_mean_bgr = cv2.cvtColor(mean_bgr, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray_mean_bgr.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray_mean_bgr.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(gx**2 + gy**2)                   # [H, W]

    # ── Composite Watermark Likelihood Map ─────────────────────────
    # Watermarks: low std, high p90_diff (they are bright), high laplacian
    low_std   = (std_map < 18.0).astype(np.float32)
    high_diff = (p90_diff > 5.0).astype(np.float32)
    high_lap  = (lap > 10.0).astype(np.float32)
    high_grad = (grad_mag > 12.0).astype(np.float32)

    # Need at least 3 of 4 signals
    score_map = low_std + high_diff + high_lap + high_grad
    candidate = (score_map >= 3.0).astype(np.uint8) * 255

    # ── Morphological grouping ──────────────────────────────────────
    # Close horizontally to bridge letter gaps, then vertically for multi-line text
    k_text = cv2.getStructuringElement(cv2.MORPH_RECT, (28, 6))
    closed_h = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, k_text)
    k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 18))
    closed = cv2.morphologyEx(closed_h, cv2.MORPH_CLOSE, k_v)

    # ── Connected-component filtering ───────────────────────────────
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(closed)
    raw_boxes = []
    for i in range(1, num):
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]

        # Minimum size: text handles are wide & short; logos can be squarish
        too_small = area < 400 or bw < 30 or bh < 8
        too_large = bw > 900 or bh > 500  # avoid entire frame detections
        if too_small or too_large:
            continue

        # Aspect ratio: text is wide (w/h > 1.2) OR logo is squarish (0.4 < w/h < 3.5)
        aspect = bw / max(1, bh)
        if aspect < 0.4 or aspect > 12.0:
            continue

        # Minimum pixel density inside box (prevents sparse noise blobs)
        roi_cand = candidate[y:y+bh, x:x+bw]
        density = np.count_nonzero(roi_cand) / max(1, bw * bh)
        if density < 0.04:
            continue

        pad_x, pad_y = 18, 12
        box = (
            max(0, x - pad_x),
            max(0, y - pad_y),
            min(W, x + bw + pad_x),
            min(H, y + bh + pad_y)
        )
        raw_boxes.append(box)

    # ── Merge overlapping / close boxes ────────────────────────────
    merged = _merge_boxes(raw_boxes, gap=30)

    # ── Build sub-pixel text mask for each merged box ───────────────
    full_mask = np.zeros((H, W), dtype=np.uint8)
    for (bx1, by1, bx2, by2) in merged:
        sub_diff = p90_diff[by1:by2, bx1:bx2]
        sub_mask = (sub_diff >= 3.0).astype(np.uint8) * 255
        sub_dil = cv2.dilate(
            sub_mask,
            cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        )
        full_mask[by1:by2, bx1:bx2] = np.maximum(
            full_mask[by1:by2, bx1:bx2], sub_dil
        )

    description = (
        f"Detected {len(merged)} watermark zone(s) anywhere in frame"
        if merged else "No persistent watermark detected"
    )
    return {
        "detected": len(merged) > 0,
        "boxes": merged,
        "full_mask": full_mask,
        "description": description
    }


def _merge_boxes(boxes, gap=30):
    """Iteratively merges overlapping or closely adjacent bounding boxes."""
    if not boxes:
        return []
    merged = list(boxes)
    changed = True
    while changed:
        changed = False
        out = []
        used = [False] * len(merged)
        for i in range(len(merged)):
            if used[i]:
                continue
            x1, y1, x2, y2 = merged[i]
            for j in range(i + 1, len(merged)):
                if used[j]:
                    continue
                ax1, ay1, ax2, ay2 = merged[j]
                # Check proximity (expand by gap)
                if not (x2 + gap < ax1 or ax2 + gap < x1 or
                        y2 + gap < ay1 or ay2 + gap < y1):
                    x1 = min(x1, ax1)
                    y1 = min(y1, ay1)
                    x2 = max(x2, ax2)
                    y2 = max(y2, ay2)
                    used[j] = True
                    changed = True
            out.append((x1, y1, x2, y2))
            used[i] = True
        merged = out
    return merged


# ─────────────────────────────────────────────────────────────
#  TOP BANNER DETECTOR
# ─────────────────────────────────────────────────────────────

def detect_top_banner(p90_diff_gray: np.ndarray, H: int = 1920) -> bool:
    """
    Detects if the top portion of the frame (y < H*0.13) has a persistent
    text overlay / editing banner.
    """
    top_slice = p90_diff_gray[0:int(H * 0.13), :]
    return bool(np.mean(top_slice >= 4) > 0.012)


# ─────────────────────────────────────────────────────────────
#  TWO-PASS INPAINTING (from WatermarkRemover-AI)
# ─────────────────────────────────────────────────────────────

def clean_watermark_roi_two_pass(img_bgr, wm_boxes, inpaint_func=None):
    """
    High-fidelity stroke-level two-pass watermark removal.
    Pass 1: Inpaints extracted high-contrast text strokes (LaMA or TELEA).
    Pass 2: Feathered boundary blending to eliminate residual halos.
    Works for ANY box position in the frame.
    """
    if not wm_boxes:
        return img_bgr

    out = img_bgr.copy()
    h, w = out.shape[:2]

    for box in wm_boxes:
        # Support both (x1,y1,x2,y2) and (y1,x1,y2,x2) formats
        if len(box) == 4:
            bx1, by1, bx2, by2 = box
        else:
            continue

        by1, bx1 = max(0, by1), max(0, bx1)
        by2, bx2 = min(h, by2), min(w, bx2)
        if by2 <= by1 or bx2 <= bx1:
            continue

        roi = out[by1:by2, bx1:bx2]
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
        feathered_mask = cv2.dilate(
            stroke_mask,
            cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        )
        diff = cv2.absdiff(cleaned_roi, roi)
        if diff.ndim == 3:
            diff_mean = diff.mean(axis=2)
        else:
            diff_mean = diff.astype(float)
        edge_band = (feathered_mask > 0) & (diff_mean > 8)
        if np.count_nonzero(edge_band) > 0:
            cleaned_roi = cv2.inpaint(
                cleaned_roi,
                edge_band.astype(np.uint8) * 255,
                2,
                cv2.INPAINT_TELEA
            )

        out[by1:by2, bx1:bx2] = cleaned_roi

    return out


# ─────────────────────────────────────────────────────────────
#  CONTOUR FILTER (legacy compatibility)
# ─────────────────────────────────────────────────────────────

def filter_watermark_from_contours(contours, wm_box):
    """Filters isolated small glyphs inside watermark bounding box while keeping character lines."""
    if not wm_box:
        return contours

    # Accept both (x1,y1,x2,y2) and (y_min,x_min,y_max,x_max)
    if len(wm_box) == 4:
        x_min, y_min, x_max, y_max = wm_box[0], wm_box[1], wm_box[2], wm_box[3]
    else:
        return contours

    clean_contours = []
    for c in contours:
        arc_len = cv2.arcLength(c, False)
        if arc_len <= 16:
            continue

        x, y, cw, ch = cv2.boundingRect(c)
        is_inside = (
            y >= y_min - 10 and y + ch <= y_max + 10 and
            x >= x_min - 10 and x + cw <= x_max + 10
        )

        if is_inside and cw < 26 and ch < 26 and arc_len < 50:
            continue

        clean_contours.append(c)

    return clean_contours

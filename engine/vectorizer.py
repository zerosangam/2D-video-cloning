import cv2
import os
import json
import numpy as np
from engine.watermark_cleaner import filter_watermark_from_contours

def pixel_to_blender_coords(px, py, width, height, ortho_scale=10.24):
    """Maps pixel coordinates (0..width, 0..height) to Blender 2D (X, Z) coordinates."""
    # Scale factor: ortho_scale represents total vertical units in Blender
    scale = ortho_scale / float(height)
    half_w = float(width) / 2.0
    half_h = float(height) / 2.0

    bx = round((float(px) - half_w) * scale, 3)
    bz = round((half_h - float(py)) * scale, 3)
    return [bx, bz]

def vectorize_all_keyframes(frames_dir, keyframes, meta, wm_box):
    """Converts image frames into vector strokes and fills for Blender Grease Pencil."""
    width = meta["width"]
    height = meta["height"]
    ortho_scale = 10.24

    vector_data = {}

    for f in keyframes:
        f_path = os.path.join(frames_dir, f"frame_{f:04d}.png")
        if not os.path.exists(f_path):
            f_path = os.path.join(frames_dir, f"frame_{f:04d}.jpg")
        if not os.path.exists(f_path):
            continue

        img = cv2.imread(f_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Blank cuts check
        if gray.mean() < 5.0 or np.std(gray) < 2.0:
            vector_data[f] = {"fills": [], "ink": []}
            continue

        # 1. Ink Outline Extraction (Cartoon line art < 70)
        ink_mask = (gray < 70).astype(np.uint8) * 255
        raw_cnts, _ = cv2.findContours(ink_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_KCOS)
        clean_cnts = filter_watermark_from_contours(raw_cnts, wm_box)

        ink_strokes = []
        for c in clean_cnts:
            approx = cv2.approxPolyDP(c, 1.2, True)
            if len(approx) >= 3:
                pts = approx.reshape(-1, 2)
                b_pts = [pixel_to_blender_coords(px, py, width, height, ortho_scale) for px, py in pts]
                ink_strokes.append(b_pts)

        # 2. Surface Fills Extraction (Whiteboards and Desks)
        fills_strokes = []
        # Whiteboard detection (bright region > 190)
        wb_mask = (gray > 190).astype(np.uint8) * 255
        wb_cnts, _ = cv2.findContours(wb_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in wb_cnts:
            if cv2.contourArea(c) > 25000: # large whiteboard surface
                approx = cv2.approxPolyDP(c, 4.0, True)
                if len(approx) >= 4:
                    pts = approx.reshape(-1, 2)
                    b_pts = [pixel_to_blender_coords(px, py, width, height, ortho_scale) for px, py in pts]
                    fills_strokes.append({"mat_index": 1, "pts": b_pts}) # Whiteboard material

        # Wooden desks / props detection (HSV filter)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask_wood = cv2.inRange(hsv, np.array([15, 30, 80]), np.array([35, 100, 160]))
        cnts_wood, _ = cv2.findContours(mask_wood, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts_wood:
            if cv2.contourArea(c) > 600:
                approx = cv2.approxPolyDP(c, 2.0, True)
                if len(approx) >= 3:
                    pts = approx.reshape(-1, 2)
                    b_pts = [pixel_to_blender_coords(px, py, width, height, ortho_scale) for px, py in pts]
                    fills_strokes.append({"mat_index": 2, "pts": b_pts}) # Desk wood material

        vector_data[f] = {
            "fills": fills_strokes,
            "ink": ink_strokes
        }

    return vector_data

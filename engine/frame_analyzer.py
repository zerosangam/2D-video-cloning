import cv2
import os
import json
import numpy as np

def rgb_to_hex(r, g, b):
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}"

def extract_master_palette(frames_dir, sample_step=15):
    """Extracts dominant color clusters across the video and maps them to semantic roles."""
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    if not frame_files:
        raise ValueError(f"No frames found in {frames_dir}")

    all_pixels = []
    for i in range(0, len(frame_files), sample_step):
        img_path = os.path.join(frames_dir, frame_files[i])
        img = cv2.imread(img_path)
        if img is None:
            continue
        small = cv2.resize(img, (72, 128))
        all_pixels.append(small.reshape(-1, 3))

    if not all_pixels:
        raise ValueError("Could not read sampled frames for palette extraction")

    stacked = np.vstack(all_pixels).astype(np.float32)
    # K-means clustering for 6 dominant colors
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    K = 6
    _, labels, centers = cv2.kmeans(stacked, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

    # Sort centers by luminance (Y channel)
    centers_bgr = np.uint8(centers)
    centers_rgb = [ [int(c[2]), int(c[1]), int(c[0])] for c in centers_bgr ]
    centers_rgb.sort(key=lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])

    # Assign semantic roles
    palette = {
        "ink_outline": {
            "hex": rgb_to_hex(*centers_rgb[0]),
            "rgb": centers_rgb[0],
            "role": "Line art, facial features, handwriting, borders"
        },
        "shadow_prop": {
            "hex": rgb_to_hex(*centers_rgb[1]),
            "rgb": centers_rgb[1],
            "role": "Dark props, upholstery, shadows"
        },
        "secondary_surface": {
            "hex": rgb_to_hex(*centers_rgb[2]),
            "rgb": centers_rgb[2],
            "role": "Furniture, wooden desks, secondary props"
        },
        "background_canvas": {
            "hex": rgb_to_hex(*centers_rgb[3]),
            "rgb": centers_rgb[3],
            "role": "Wall backdrop canvas and neutral skin"
        },
        "whiteboard_highlight": {
            "hex": rgb_to_hex(*centers_rgb[-1]),
            "rgb": centers_rgb[-1],
            "role": "Whiteboard, paper panels, specular highlights"
        }
    }
    return palette

def detect_shots_and_keyframes(frames_dir, total_frames, threshold=18.0):
    """Detects scene cuts, holds, and animated keyframes across all frames."""
    key_frames = [1]
    prev_gray = None
    cuts = []

    for f in range(1, total_frames + 1):
        frame_path = os.path.join(frames_dir, f"frame_{f:04d}.png")
        if not os.path.exists(frame_path):
            frame_path = os.path.join(frames_dir, f"frame_{f:04d}.jpg")
        if not os.path.exists(frame_path):
            continue
        img = cv2.imread(frame_path)
        small = cv2.resize(img, (144, 256))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            mean_diff = float(np.mean(diff))

            # Scene jump cut detected
            if mean_diff > threshold:
                cuts.append(f)
                key_frames.append(f)
            # Subtle pose motion detected
            elif mean_diff > 1.8:
                key_frames.append(f)

        prev_gray = gray

    if total_frames not in key_frames:
        key_frames.append(total_frames)

    return sorted(list(set(key_frames))), cuts

def generate_timeline_json(frames_dir, meta, palette, cuts, keyframes, watermark_info):
    """Constructs comprehensive 270-frame timeline metadata log."""
    total_frames = meta["total_frames"]
    fps = meta["fps"]
    timeline_cards = []

    shot_idx = 1
    current_cut_set = set(cuts)

    for f in range(1, total_frames + 1):
        if f in current_cut_set:
            shot_idx += 1

        total_sec = (f - 1) // fps
        frame_rem = int((f - 1) % fps)
        hrs = int(total_sec // 3600)
        mins = int((total_sec % 3600) // 60)
        secs = int(total_sec % 60)
        timecode = f"{hrs:02d}:{mins:02d}:{secs:02d}:{frame_rem:02d}"

        card = {
            "frame_number": f,
            "timecode": timecode,
            "shot_id": shot_idx,
            "is_keyframe": f in keyframes,
            "color_palette_hex": [p["hex"] for p in palette.values()],
            "camera_data": {
                "fov_deg": 50.0,
                "focal_length_mm": 50.0,
                "type": "ORTHOGRAPHIC"
            },
            "watermark_detected": watermark_info.get("detected", False),
            "watermark_region": watermark_info.get("bounding_box", [475, 180, 525, 420])
        }
        timeline_cards.append(card)

    return {
        "project": "Automated 2D Video Recreation Engine",
        "video_metadata": meta,
        "master_palette": palette,
        "total_shots": shot_idx,
        "timeline": timeline_cards
    }

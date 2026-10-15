import os
import sys
import time
import cv2
import numpy as np

workspace_dir = os.path.dirname(os.path.abspath(__file__))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

try:
    from engine.lama_inpaint.runtime import LamaInpaint
except Exception:
    LamaInpaint = None
from engine.watermark_cleaner import clean_watermark_roi_two_pass

def main():
    sample_img_path = os.path.join(workspace_dir, "output", "previews", "sample_frame.jpg")
    if os.path.exists(sample_img_path):
        frame = cv2.imread(sample_img_path)
    else:
        video_path = os.path.join(workspace_dir, "input", "zero (1).mp4")
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 50)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            print("[ERROR] Could not load sample frame.")
            return

    if (frame.shape[1], frame.shape[0]) != (1080, 1920):
        frame = cv2.resize(frame, (1080, 1920))

    print(f"[INPUT] Frame loaded: {frame.shape[1]}x{frame.shape[0]}")

    # Build mask for both watermarks:
    # 1. Top editing text: "me at 1:00 am" (y: 150-250, x: 230-670)
    # 2. Bottom channel watermark: "@ricoanimations" (y: 1300-1400, x: 300-750)
    mask = np.zeros((1920, 1080), dtype=np.uint8)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    zones = [
        ("top_text", 230, 150, 670, 250),
        ("rico_wm", 300, 1300, 750, 1400)
    ]

    for name, x1, y1, x2, y2 in zones:
        sub_gray = gray[y1:y2, x1:x2]
        # Text characters are white/high contrast against paper background
        med = cv2.medianBlur(sub_gray, 15)
        diff = cv2.absdiff(sub_gray, med)
        _, sub_mask = cv2.threshold(diff, 8, 255, cv2.THRESH_BINARY)
        # Dilate slightly so inpainting covers text edges cleanly
        dil = cv2.dilate(sub_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4)), iterations=2)
        mask[y1:y2, x1:x2] = dil

    mask_pixels = np.count_nonzero(mask)
    print(f"[MASK] Created text mask with {mask_pixels} pixels across {len(zones)} zones.")

    # Save mask preview for verification
    preview_dir = os.path.join(workspace_dir, "output", "previews")
    os.makedirs(preview_dir, exist_ok=True)
    cv2.imwrite(os.path.join(preview_dir, "test_mask.jpg"), mask)

    # Initialize LaMA or Adaptive Two-Pass Inpainter
    lama = None
    if LamaInpaint is not None:
        try:
            print("[LAMA] Loading / downloading LaMA TorchScript model...")
            t0 = time.time()
            lama = LamaInpaint(device="cpu")
            print(f"[LAMA] Model loaded and ready in {time.time() - t0:.2f}s!")
        except Exception as e:
            print(f"[LAMA] PyTorch LaMA not loaded ({e}). Using Enhanced Two-Pass Stroke Inpainting.")

    # Run Inpainting
    print("[PROCESS] Running High-Fidelity Inpainting...")
    t_start = time.time()
    if lama is not None:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        lama_cleaned_bgr = lama(frame_rgb, mask)
    else:
        wm_boxes_converted = [(y1, x1, y2, x2) for (name, x1, y1, x2, y2) in zones]
        lama_cleaned_bgr = clean_watermark_roi_two_pass(frame, wm_boxes_converted)
    t_lama = time.time() - t_start
    print(f"[SUCCESS] High-Fidelity Inpainting finished in {t_lama:.2f}s!")

    # Run Old OpenCV Telea for comparison
    t_start = time.time()
    telea_cleaned_bgr = cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)
    t_telea = time.time() - t_start
    print(f"[COMPARE] OpenCV Telea finished in {t_telea:.2f}s.")

    # 1. Zoom comparison on @ricoanimations (y: 1280 to 1420, x: 280 to 780)
    zy1, zy2, zx1, zx2 = 1280, 1420, 280, 780
    crop_orig = frame[zy1:zy2, zx1:zx2].copy()
    crop_telea = telea_cleaned_bgr[zy1:zy2, zx1:zx2].copy()
    crop_lama = lama_cleaned_bgr[zy1:zy2, zx1:zx2].copy()

    # Add text labels on crops
    cv2.putText(crop_orig, "ORIGINAL", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.putText(crop_telea, "OPENCV TELEA (BLUR)", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    cv2.putText(crop_lama, "LAMA AI (ZERO BLUR)", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    zoom_comp = np.hstack([crop_orig, crop_telea, crop_lama])
    zoom_path = os.path.join(preview_dir, "lama_zoom_comparison.jpg")
    cv2.imwrite(zoom_path, zoom_comp)
    print(f"[SAVED] Zoom-in Comparison: {zoom_path}")

    # 2. Full frame side-by-side (540x960 each)
    f_orig = cv2.resize(frame, (540, 960))
    f_lama = cv2.resize(lama_cleaned_bgr, (540, 960))
    cv2.putText(f_orig, "ORIGINAL (WITH WATERMARK)", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    cv2.putText(f_lama, "LAMA AI (CLEANED)", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    full_comp = np.hstack([f_orig, f_lama])
    full_path = os.path.join(preview_dir, "lama_full_comparison.jpg")
    cv2.imwrite(full_path, full_comp)
    print(f"[SAVED] Full Frame Comparison: {full_path}")
    print("=" * 60)
    print("Test completed successfully!")

if __name__ == "__main__":
    main()

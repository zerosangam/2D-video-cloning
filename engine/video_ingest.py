import cv2
import os
import json
import subprocess

def probe_video(video_path):
    """Probes video file using OpenCV and returns comprehensive metadata."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0 or fps > 240:
        fps = 30.0  # sensible fallback
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0.0
    cap.release()

    meta = {
        "video_path": os.path.abspath(video_path),
        "filename": os.path.basename(video_path),
        "width": width,
        "height": height,
        "aspect_ratio": f"{width}:{height}" if height > 0 else "unknown",
        "fps": round(fps, 2),
        "total_frames": total_frames,
        "duration_sec": round(duration_sec, 2),
        "duration_timecode": f"{int(duration_sec//3600):02d}:{int((duration_sec%3600)//60):02d}:{int(duration_sec%60):02d}:{int((duration_sec*fps)%fps):02d}"
    }
    return meta

def extract_all_frames(video_path, frames_dir, log_callback=None):
    """Extracts all frames of the video into target directory using OpenCV."""
    os.makedirs(frames_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_idx = 1
    extracted_paths = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_filename = f"frame_{frame_idx:04d}.png"
        out_path = os.path.join(frames_dir, frame_filename)
        cv2.imwrite(out_path, frame)
        extracted_paths.append(out_path)
        
        if log_callback and (frame_idx % 50 == 0 or frame_idx == total_frames):
            log_callback(f"Extracted frame {frame_idx}/{total_frames}")
        frame_idx += 1

    cap.release()
    return extracted_paths

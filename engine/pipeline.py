import os
import sys
import json
import time
import subprocess
import shutil
from engine.video_ingest import probe_video, extract_all_frames
from engine.frame_analyzer import extract_master_palette, detect_shots_and_keyframes, generate_timeline_json
from engine.watermark_cleaner import detect_watermark
from engine.vectorizer import vectorize_all_keyframes

def get_blender_binary():
    custom = os.environ.get("BLENDER_EXE") or os.environ.get("BLENDER_PATH")
    if custom and os.path.exists(custom):
        return custom
    sys_blender = shutil.which("blender")
    if sys_blender:
        return sys_blender
    for ver in ["5.2", "5.1", "5.0", "4.3", "4.2"]:
        cand = rf"C:\Program Files\Blender Foundation\Blender {ver}\blender.exe"
        if os.path.exists(cand):
            return cand
    return "blender"

BLENDER_EXE = get_blender_binary()

def run_pipeline(video_path=None, base_dir=None):
    t_pipeline_start = time.time()
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    input_dir = os.path.join(base_dir, "input")
    output_dir = os.path.join(base_dir, "output")
    cache_dir = os.path.join(base_dir, "cache")
    frames_dir = os.path.join(cache_dir, "frames")
    previews_dir = os.path.join(output_dir, "previews")
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(previews_dir, exist_ok=True)

    # 1. Detect input video if not provided
    if not video_path:
        video_candidates = [
            os.path.join(input_dir, f) for f in os.listdir(input_dir)
            if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))
        ]
        if not video_candidates:
            # Check fallback in base_dir
            fallback = os.path.join(base_dir, "ref-1.mp4")
            if os.path.exists(fallback):
                video_candidates = [fallback]
            else:
                raise FileNotFoundError(f"No video found in {input_dir}. Please drop a video into 'input/' folder!")
        video_path = video_candidates[0]

    print("=" * 60)
    print("      SANGAM RECREATION ENGINE — AUTOMATED 2D ECOSYSTEM")
    print("=" * 60)
    print(f"Target Video: {video_path}")

    # Stage 1: Ingest & Probe
    print("\n[STAGE 1/6] Ingesting Video & Metadata...")
    meta = probe_video(video_path)
    print(f"  • Resolution: {meta['width']}x{meta['height']} ({meta['aspect_ratio']})")
    print(f"  • Frame Rate: {meta['fps']} FPS")
    print(f"  • Total Frames: {meta['total_frames']}")
    print(f"  • Duration: {meta['duration_sec']}s ({meta['duration_timecode']})")

    # Stage 2: Extract Frames
    print("\n[STAGE 2/6] Extracting frames to cache...")
    frames = extract_all_frames(video_path, frames_dir, log_callback=lambda msg: print(f"    {msg}"))
    print(f"  • Extracted {len(frames)} native frames.")

    # Stage 3: Frame & Palette Analysis
    print("\n[STAGE 3/6] Analyzing frames, color clusters & shot timing...")
    palette = extract_master_palette(frames_dir)
    print("  • Extracted Master Palette:")
    for role, pinfo in palette.items():
        print(f"      - {role}: {pinfo['hex']} (RGB: {pinfo['rgb']})")

    keyframes, cuts = detect_shots_and_keyframes(frames_dir, meta["total_frames"])
    print(f"  • Detected {len(cuts)} scene cuts / jump transitions.")
    print(f"  • Identified {len(keyframes)} active animation keyframes.")

    # Stage 4: Watermark & Branding Detection
    print("\n[STAGE 4/6] Detecting and filtering channel branding...")
    wm_info = detect_watermark(frames_dir, meta["total_frames"])
    print(f"  • Branding Overlay Filter: {wm_info.get('description', 'Active')}")
    print(f"  • Exclusion Zone: {wm_info.get('bounding_box')}")

    # Build and save timeline metadata
    timeline_data = generate_timeline_json(frames_dir, meta, palette, cuts, keyframes, wm_info)
    timeline_path = os.path.join(output_dir, "timeline.json")
    palette_path = os.path.join(output_dir, "palette.json")
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(timeline_data, f, indent=2)
    with open(palette_path, "w", encoding="utf-8") as f:
        json.dump(palette, f, indent=2)
    print(f"  • Saved timeline metadata to {timeline_path}")
    print(f"  • Saved color palette to {palette_path}")

    # Stage 5: 2D Vector Stroke Extraction
    print("\n[STAGE 5/6] Extracting 2D Grease Pencil vector strokes & fills...")
    strokes_data = vectorize_all_keyframes(frames_dir, keyframes, meta, wm_info.get("bounding_box"))
    strokes_path = os.path.join(cache_dir, "strokes.json")
    with open(strokes_path, "w", encoding="utf-8") as f:
        json.dump(strokes_data, f)
    print(f"  • Generated vector strokes for {len(strokes_data)} keyframes.")

    # Stage 6: Blender Build & Render
    print("\n[STAGE 6/6] Launching Blender 5.2 2D Grease Pencil Engine...")
    output_mp4 = os.path.join(output_dir, "final_output.mp4")
    output_blend = os.path.join(output_dir, "project.blend")
    
    build_config = {
        "metadata": meta,
        "strokes_path": strokes_path,
        "palette_path": palette_path,
        "output_mp4": output_mp4,
        "output_blend": output_blend,
        "previews_dir": previews_dir,
        "audio_source": video_path
    }
    config_path = os.path.join(cache_dir, "build_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(build_config, f, indent=2)

    builder_script = os.path.join(base_dir, "engine", "blender_builder.py")
    blender_cmd = [
        BLENDER_EXE,
        "--background",
        "--python", builder_script,
        "--", config_path
    ]

    print("  • Executing Blender headless render...")
    blender_res = subprocess.run(blender_cmd, capture_output=True, text=True)
    if blender_res.returncode != 0:
        print("Blender Error Output:")
        print(blender_res.stderr)
        raise RuntimeError("Blender build failed.")

    print(blender_res.stdout)

    t_total = time.time() - t_pipeline_start
    print("=" * 60)
    print(f"RECREATION COMPLETE IN {t_total:.2f} SECONDS!")
    print(f"Output Video: {output_mp4}")
    print(f"Blender File: {output_blend}")
    print(f"Previews Dir: {previews_dir}")
    print("=" * 60)
    return {
        "status": "SUCCESS",
        "total_time": round(t_total, 2),
        "output_mp4": output_mp4,
        "output_blend": output_blend,
        "timeline_path": timeline_path,
        "palette_path": palette_path,
        "previews_dir": previews_dir
    }

if __name__ == "__main__":
    v_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(v_arg)

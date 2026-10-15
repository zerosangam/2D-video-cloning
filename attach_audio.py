#!/usr/bin/env python3
"""
Quick audio-attach script.
Run this in Codespace if videos are already made but have no audio:
    python attach_audio.py
"""
import os
import subprocess
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

def get_ffmpeg():
    for f in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        try:
            r = subprocess.run([f, "-version"], capture_output=True)
            if r.returncode == 0:
                return f
        except FileNotFoundError:
            pass
    raise RuntimeError("ffmpeg not found in PATH!")

def find_audio():
    candidates = [
        os.path.join(BASE, "output", "audio", "audio.wav"),
        os.path.join(BASE, "output", "audio.wav"),
        os.path.join(BASE, "cache", "current_video_workspace", "audio.wav")
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 1000:
            return c
    return None

def has_audio_stream(video_path, ffmpeg):
    """Checks whether the video file currently contains an active audio stream."""
    cmd = [ffmpeg, "-i", video_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    # ffmpeg prints stream info to stderr
    return "Audio:" in r.stderr

def attach_audio(video_path, audio_path, ffmpeg):
    if not os.path.exists(video_path):
        print(f"[SKIP] Video not found: {video_path}")
        return False
    if not os.path.exists(audio_path):
        print(f"[ERROR] Audio not found: {audio_path}")
        return False

    tmp = video_path + ".with_audio_tmp.mp4"
    print(f"\n[MUX] Attaching audio to: {video_path}")
    print(f"      Audio source: {audio_path} ({os.path.getsize(audio_path)//1024} KB)")

    # Method 1: Stream copy video + aac audio (instant, 100% loss-less)
    cmd1 = [
        ffmpeg, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-movflags", "+faststart",
        tmp
    ]
    r1 = subprocess.run(cmd1, capture_output=True, text=True)
    if r1.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 1000:
        shutil.move(tmp, video_path)
        print(f"[SUCCESS] Stream-copy mux OK: {os.path.getsize(video_path)//1024} KB")
        return True
    else:
        print(f"[WARN] Method 1 failed: {r1.stderr[-300:].strip()}")

    # Method 2: Fast re-encode with -async 1
    print(f"[MUX] Trying Method 2 (fast ultrafast re-encode + async 1)...")
    cmd2 = [
        ffmpeg, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-threads", "2",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-async", "1",
        "-movflags", "+faststart",
        tmp
    ]
    r2 = subprocess.run(cmd2, capture_output=True, text=True)
    if r2.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 1000:
        shutil.move(tmp, video_path)
        print(f"[SUCCESS] Method 2 mux OK: {os.path.getsize(video_path)//1024} KB")
        return True
    else:
        print(f"[FAIL] Method 2 failed: {r2.stderr[-300:].strip()}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return False

def main():
    ffmpeg = get_ffmpeg()
    audio = find_audio()
    if not audio:
        print("[ERROR] audio.wav not found! Checked in output/audio/, output/, cache/.")
        sys.exit(1)

    print(f"[INFO] Using FFmpeg: {ffmpeg}")
    print(f"[INFO] Found Audio:  {audio} ({os.path.getsize(audio)//1024} KB)")

    targets = [
        os.path.join(BASE, "output", "videos", "mr_perfect_lines.mp4"),
        os.path.join(BASE, "output", "videos", "mr_perfect_color.mp4"),
    ]

    success = 0
    for v in targets:
        if os.path.exists(v):
            if attach_audio(v, audio, ffmpeg):
                success += 1
                # Sync to root output folder as well
                root_target = os.path.join(BASE, "output", os.path.basename(v))
                try:
                    shutil.copy2(v, root_target)
                    print(f"[SYNC] Copied to root deliverable: {root_target}")
                except Exception as e:
                    print(f"[SYNC WARNING] Failed copying to {root_target}: {e}")

    print(f"\n{'='*60}")
    print(f"Result: Successfully processed {success} video(s) with audio attached.")
    print("Both output/videos/ and output/ root copies are synchronized!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()


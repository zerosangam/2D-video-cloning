import sys
import os

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

workspace_dir = os.path.dirname(os.path.abspath(__file__))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

venv_py = os.path.join(workspace_dir, ".venv", "Scripts", "python.exe")
if os.path.exists(venv_py) and os.path.normcase(sys.executable) != os.path.normcase(venv_py):
    import subprocess
    cmd = [venv_py] + sys.argv
    sys.exit(subprocess.call(cmd))

SUPPORTED_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv')

def check_runtime_dependencies():
    """Validates required third-party libraries and tools before pipeline start."""
    missing = []
    try:
        import cv2  # noqa: F401
    except ImportError:
        missing.append("opencv-python (cv2)")

    try:
        import numpy  # noqa: F401
    except ImportError:
        missing.append("numpy")

    try:
        import imageio_ffmpeg  # noqa: F401
    except ImportError:
        missing.append("imageio_ffmpeg")

    if missing:
        print("[ERROR] Missing required Python packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nPlease install missing packages by running:")
        print(f"  {sys.executable} -m pip install " + " ".join([p.split()[0] for p in missing]))
        sys.exit(1)

def main():
    check_runtime_dependencies()
    from master_system.mr_perfect_master_engine import run_mr_perfect_pipeline

    input_dir = os.path.join(workspace_dir, "input")
    os.makedirs(input_dir, exist_ok=True)

    if any(arg in sys.argv for arg in ["--help", "-h"]):
        print("Usage: python start_cloning.py [path_to_video.mp4] [--fast] [--no-resume]")
        print("Options:")
        print("  --fast       Enable Ultra-Fast 100x mode (OpenCV inpainting, ~1-2 mins)")
        print("  --mode lama  Use Studio AI LaMA inpainting (Default, highest neural quality)")
        print("  --no-resume  Recompute all frames from scratch instead of resuming")
        print("If no video path is specified, the script automatically scans the 'input/' folder.")
        sys.exit(0)

    fast_mode = "--fast" in sys.argv
    inpaint_mode = "fast" if fast_mode else "lama"
    for idx, arg in enumerate(sys.argv):
        if arg == "--mode" and idx + 1 < len(sys.argv):
            inpaint_mode = sys.argv[idx + 1]

    resume_flag = "--no-resume" not in sys.argv

    video_args = [a for a in sys.argv[1:] if not a.startswith("--") and (a != inpaint_mode)]
    if video_args:
        video_input = video_args[0]
    else:
        video_files = [
            os.path.join(input_dir, f) for f in os.listdir(input_dir)
            if f.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        if not video_files:
            print(f"[ERROR] No video found in: {input_dir}")
            print(f"Please place your reference video (.mp4/.mov/.mkv) in '{input_dir}' and run again.")
            sys.exit(1)
        video_input = video_files[0]

    out_dir = os.path.join(workspace_dir, "output")
    cache_dir = os.path.join(workspace_dir, "cache")
    run_mr_perfect_pipeline(
        video_input,
        out_dir=out_dir,
        cache_dir=cache_dir,
        inpaint_mode=inpaint_mode,
        resume=resume_flag
    )

if __name__ == "__main__":
    main()

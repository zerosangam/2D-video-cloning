"""
================================================================================
CLOUDINARY HIGH-SPEED CLOUD STORAGE ENGINE FOR 2D VIDEO CLONING
================================================================================
Handles:
1. Chunked Upload of large videos (>50MB, >100MB) without memory overload.
2. Fast generation of secure, streamable CDN video URLs (https://res.cloudinary.com/...).
3. Direct download from Cloudinary / Web URLs into local input/ directory.
4. Seamless integration with Telegram Bot & LangGraph Pipeline.
================================================================================
"""

import os
import sys
import time
import requests
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

def load_dotenv(env_path: Optional[str] = None):
    """Loads environment variables from .env file."""
    path = env_path or os.path.join(workspace_dir, ".env")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

# Initialize environment
load_dotenv()

# Configure Cloudinary
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "dug9qd7hh")
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "833589372781463")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "UsXm5Uci56neSWUYvjDiCIlj7Cw")

cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET,
    secure=True
)


def upload_video_to_cloud(
    file_path: str,
    folder: str = "2d_video_cloning",
    public_id: Optional[str] = None,
    chunk_size_mb: int = 6
) -> Dict[str, Any]:
    """
    Uploads a video to Cloudinary using chunked upload (safe for >50MB and >100MB files).
    Returns a dict containing 'secure_url', 'public_id', 'bytes', and 'duration'.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Local video file not found: {file_path}")

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"\n[Cloudinary] Starting chunked upload for '{os.path.basename(file_path)}' ({file_size_mb:.2f} MB)...")
    t0 = time.time()

    chunk_bytes = chunk_size_mb * 1024 * 1024
    upload_kwargs = {
        "resource_type": "video",
        "chunk_size": chunk_bytes,
        "folder": folder,
        "overwrite": True
    }
    if public_id:
        upload_kwargs["public_id"] = public_id

    response = cloudinary.uploader.upload_large(file_path, **upload_kwargs)
    t_upload = time.time() - t0

    result = {
        "secure_url": response.get("secure_url"),
        "public_id": response.get("public_id"),
        "format": response.get("format"),
        "bytes": response.get("bytes", 0),
        "duration": response.get("duration", 0),
        "upload_time_sec": round(t_upload, 2)
    }

    print(f"[Cloudinary] [OK] Upload complete in {t_upload:.2f}s!")
    print(f"[Cloudinary] CDN Link: {result['secure_url']}")
    return result


def download_video_from_cloud(cloud_url: str, dest_path: Optional[str] = None) -> str:
    """
    Downloads a video from Cloudinary / direct URL into local workspace.
    """
    if not dest_path:
        filename = cloud_url.split("?")[0].split("/")[-1]
        if not filename.lower().endswith((".mp4", ".mov", ".mkv")):
            filename = f"cloud_video_{int(time.time())}.mp4"
        dest_path = os.path.join(workspace_dir, "input", filename)

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    print(f"\n[Cloudinary] Downloading from: {cloud_url}")
    t0 = time.time()

    with requests.get(cloud_url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total_len = resp.headers.get("content-length")
        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

    mb = downloaded / (1024 * 1024)
    print(f"[Cloudinary] [OK] Downloaded {mb:.2f} MB in {time.time() - t0:.2f}s -> {dest_path}")
    return dest_path



def check_cloudinary_status() -> bool:
    """Tests connection to Cloudinary API."""
    try:
        res = cloudinary.api.ping()
        return res.get("status") == "ok"
    except Exception as e:
        print(f"[Cloudinary] Connection error: {e}")
        return False


if __name__ == "__main__":
    print("==================================================")
    print("CLOUDINARY CLOUD STORAGE VERIFICATION")
    print("==================================================")
    ok = check_cloudinary_status()
    print(f"Cloud Name: {CLOUD_NAME}")
    print(f"Status:     {'CONNECTED (ACTIVE)' if ok else 'FAILED'}")
    print("==================================================")

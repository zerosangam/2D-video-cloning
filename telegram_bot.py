"""
================================================================================
TELEGRAM AI 2D VIDEO CLONING BOT (POWERED BY LANGGRAPH + MEM0 + CLOUDINARY)
================================================================================
Bot Name: AI.bot (@ai2Dcloningbot)
Features:
1. Receives video files or Cloudinary URLs from Telegram chat.
2. Seamlessly uploads large video assets to Cloudinary CDN for instant URL streaming.
3. Triggers autonomous 2D Recreation Pipeline (DoG inking, LaMa watermark clean, audio sync).
4. Delivers the final 2D recreated animation back to Telegram:
   - Direct MP4 Video in chat (if <= 50MB)
   - High-Speed Cloudinary CDN Download & Streaming Link (for any file size)
================================================================================
"""

import os
import sys
import time
import subprocess
import telebot
from telebot import types

# Workspace & UTF-8 setup
workspace_dir = os.path.dirname(os.path.abspath(__file__))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Import project cloud uploader
from engine.cloud_uploader import upload_video_to_cloud, download_video_from_cloud, load_dotenv

# Load credentials from .env
load_dotenv()
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8757679341:AAG3jpgPlO9L7VX-A7FaxTP15lbSahGgqjU")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────────────────────
# 1. COMMAND HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🎬 *Welcome to the 2D Video Cloning AI Bot!*\n\n"
        "I automatically convert reference videos into *2D gapless single-line ink art* "
        "and *flat color animation* with zero manual drawing and exact audio lip-sync.\n\n"
        "🚀 *How to use:*\n"
        "1. *Send a Video file* directly here in chat.\n"
        "2. *Or send a Video URL* (Cloudinary, Google Drive, direct MP4 link).\n\n"
        "☁️ *Cloudinary Integration:*\n"
        "Large videos (>50MB) are automatically backed by Cloudinary CDN with direct download links!\n\n"
        "Drop your video below to start cloning! 👇"
    )
    bot.reply_to(message, welcome_text)


# ─────────────────────────────────────────────────────────────────────────────
# 2. URL LINK HANDLER
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda msg: msg.text and (msg.text.startswith("http://") or msg.text.startswith("https://")))
def handle_video_url(message):
    url = message.text.strip()
    chat_id = message.chat.id
    status_msg = bot.reply_to(message, "📥 *Received Video URL!*\nDownloading into cloud workspace...")

    input_dir = os.path.join(workspace_dir, "input")
    os.makedirs(input_dir, exist_ok=True)
    local_input = os.path.join(input_dir, f"telegram_input_{int(time.time())}.mp4")

    try:
        download_video_from_cloud(url, local_input)
        process_and_deliver(local_input, chat_id, status_msg)
    except Exception as e:
        bot.edit_message_text(f"❌ *Download Error:*\n`{str(e)}`", chat_id=chat_id, message_id=status_msg.message_id)


# ─────────────────────────────────────────────────────────────────────────────
# 3. DIRECT VIDEO & DOCUMENT HANDLER
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(content_types=['video', 'document'])
def handle_video_file(message):
    chat_id = message.chat.id
    status_msg = bot.reply_to(message, "📥 *Video received!*\nProcessing file...")

    try:
        # Determine file ID
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_size = message.video.file_size
            file_ext = ".mp4"
        else:
            doc = message.document
            if not doc.file_name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                bot.edit_message_text("❌ Please send a valid video file (.mp4, .mov, .mkv).", chat_id=chat_id, message_id=status_msg.message_id)
                return
            file_id = doc.file_id
            file_size = doc.file_size
            file_ext = os.path.splitext(doc.file_name)[1]

        # Telegram Bot API getFile limit check (20 MB for bot download)
        if file_size > 20 * 1024 * 1024:
            bot.edit_message_text(
                f"⚠️ *File is {file_size/(1024*1024):.1f} MB!*\n"
                "Telegram's standard Bot API limits direct downloads to 20MB.\n\n"
                "💡 *Solution:* Upload to Cloudinary or Google Drive and paste the link here, "
                "and I will process it with zero size limits!",
                chat_id=chat_id, message_id=status_msg.message_id
            )
            return

        bot.edit_message_text("⬇️ Downloading video to AI workspace...", chat_id=chat_id, message_id=status_msg.message_id)
        file_info = bot.get_file(file_id)
        downloaded_bytes = bot.download_file(file_info.file_path)

        input_dir = os.path.join(workspace_dir, "input")
        os.makedirs(input_dir, exist_ok=True)
        local_input = os.path.join(input_dir, f"telegram_input_{int(time.time())}{file_ext}")

        with open(local_input, "wb") as f:
            f.write(downloaded_bytes)

        # Upload backup to Cloudinary
        try:
            bot.edit_message_text("☁️ Uploading input asset to Cloudinary CDN...", chat_id=chat_id, message_id=status_msg.message_id)
            cloud_res = upload_video_to_cloud(local_input, folder="2d_video_cloning/inputs")
            print(f"[Telegram Bot] Input video saved to Cloudinary: {cloud_res['secure_url']}")
        except Exception as e:
            print(f"[Telegram Bot] Cloudinary backup note: {e}")

        process_and_deliver(local_input, chat_id, status_msg)

    except Exception as e:
        bot.edit_message_text(f"❌ *Error:* `{str(e)}`", chat_id=chat_id, message_id=status_msg.message_id)


# ─────────────────────────────────────────────────────────────────────────────
# 4. PROCESSING & DELIVERY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def process_and_deliver(video_path: str, chat_id: int, status_msg: types.Message):
    """Executes 2D cloning, uploads result to Cloudinary, and delivers to Telegram."""
    bot.edit_message_text(
        "🎨 *2D Cloning Engine in Progress!*\n"
        "• Difference of Gaussians (DoG) 2px Inking\n"
        "• LaMa Deep Learning Watermark Cleaner\n"
        "• Exact Audio Lip-Sync Lock\n\n"
        "⏳ _Please wait while frames are rendered..._",
        chat_id=chat_id, message_id=status_msg.message_id
    )

    # Invoke cloning engine via start_cloning.py
    runner_script = os.path.join(workspace_dir, "start_cloning.py")
    venv_py = os.path.join(workspace_dir, ".venv", "Scripts", "python.exe")
    python_exe = venv_py if os.path.exists(venv_py) else sys.executable

    cmd = [python_exe, runner_script, video_path, "--fast"]
    print(f"\n[Telegram Bot] Launching: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        err_snippet = result.stderr[-400:] if result.stderr else result.stdout[-400:]
        bot.edit_message_text(
            f"❌ *Pipeline Error occurred:*\n```\n{err_snippet}\n```",
            chat_id=chat_id, message_id=status_msg.message_id
        )
        return

    # Check output videos
    out_lines_video = os.path.join(workspace_dir, "output", "videos", "mr_perfect_lines.mp4")
    out_color_video = os.path.join(workspace_dir, "output", "videos", "mr_perfect_color.mp4")

    deliverable = out_color_video if os.path.exists(out_color_video) else out_lines_video

    if not os.path.exists(deliverable):
        bot.edit_message_text("❌ Render complete but output video was not found.", chat_id=chat_id, message_id=status_msg.message_id)
        return

    # Upload deliverable to Cloudinary
    bot.edit_message_text("☁️ *Recreation Complete!* Uploading to Cloudinary CDN...", chat_id=chat_id, message_id=status_msg.message_id)
    cloud_deliverable = None
    try:
        cloud_deliverable = upload_video_to_cloud(deliverable, folder="2d_video_cloning/deliverables")
    except Exception as e:
        print(f"[Telegram Bot] Output Cloudinary upload warning: {e}")

    file_size_mb = os.path.getsize(deliverable) / (1024 * 1024)
    caption_text = (
        "🎬 *2D Video Recreation Complete!*\n"
        f"• Size: `{file_size_mb:.2f} MB`\n"
        "• Style: Authentic 2D Gapless Single-Line Art & Color\n"
        "• Audio: Synchronized 44.1kHz\n"
    )
    if cloud_deliverable:
        caption_text += f"\n🌐 *Cloud CDN Stream/Download:* [Click Here]({cloud_deliverable['secure_url']})"

    # Send directly via Telegram if <= 50MB
    if file_size_mb <= 50.0:
        bot.edit_message_text("🚀 Sending finished video to Telegram...", chat_id=chat_id, message_id=status_msg.message_id)
        with open(deliverable, "rb") as vid_file:
            bot.send_video(chat_id, vid_file, caption=caption_text)
        bot.delete_message(chat_id, status_msg.message_id)
    else:
        # File is > 50MB, deliver via Cloudinary CDN link
        bot.edit_message_text(
            f"🎬 *2D Video Recreation Complete!*\n\n"
            f"File is `{file_size_mb:.1f} MB` (Telegram limit is 50MB).\n\n"
            f"📥 *Download/Stream directly from Cloudinary CDN:*\n"
            f"{cloud_deliverable['secure_url'] if cloud_deliverable else 'Upload pending'}",
            chat_id=chat_id, message_id=status_msg.message_id
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. BOT RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def start_bot():
    bot_info = bot.get_me()
    print("=" * 60)
    print(f"TELEGRAM BOT ONLINE: @{bot_info.username} (ID: {bot_info.id})")
    print(f"Cloud Name:           {os.environ.get('CLOUDINARY_CLOUD_NAME')}")
    print("Listening for messages and videos on Telegram...")
    print("=" * 60)
    bot.infinity_polling(timeout=30, long_polling_timeout=30)


if __name__ == "__main__":
    start_bot()

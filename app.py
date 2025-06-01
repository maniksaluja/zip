## A Telegram bot to extract zip, tar, 7z, and rar archives
# Requirements: requirements.txt
# Author: AMI 
# License: MIT License
## Python Version: 3.10 or higher


import os
import json
import platform
import psutil
import shutil
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import zipfile
import tarfile
import py7zr
import rarfile


## --- ADD YOUR API ID, API HASH, and BOT TOKEN BELOW ---
# You can get these from https://my.telegram.org
API_ID= 21154846
API_HASH="ef320a14f6312ba733d1812e7129cbd8"
BOT_TOKEN = "8079860149:AAG7ffR2jSg1MlXN05ddVPRIM1VKBhU59Nk"
# --- END OF CONFIGURATION ---
DATA_DIR = Path("data")
USAGE_FILE = Path("usage.json")
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB Telegram limit

app = Client("zipbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def load_usage():
    if USAGE_FILE.exists():
        with open(USAGE_FILE, "r") as f:
            try:
                usage = json.load(f)
                # If usage is a list (old/invalid), reset to dict
                if isinstance(usage, list):
                    usage = {
                        "files_extracted": 0,
                        "archives_count": 0,
                        "archives_size": 0,
                        "users": set()
                    }
                # Ensure users is always a set
                if isinstance(usage.get("users", []), list):
                    usage["users"] = set(usage.get("users", []))
                else:
                    usage["users"] = set()
                return usage
            except Exception:
                pass
    return {
        "files_extracted": 0,
        "archives_count": 0,
        "archives_size": 0,
        "users": set()
    }

def save_usage(usage):
    usage["users"] = list(usage["users"])
    with open(USAGE_FILE, "w") as f:
        json.dump(usage, f)

def update_usage(user_id, archive_size, files_count):
    usage = load_usage()
    usage["files_extracted"] += files_count
    usage["archives_count"] += 1
    usage["archives_size"] += archive_size
    usage.setdefault("users", set())
    usage["users"].add(user_id)
    # Add a usage log entry for each extract
    log_entry = {
        "user_id": user_id,
        "files_extracted": files_count,
        "archive_size": archive_size,
        "timestamp": int(__import__('time').time())
    }
    # Save to usages.json (append or create)
    usages_path = Path("usages.json")
    if usages_path.exists():
        with open(usages_path, "r") as f:
            try:
                usages = json.load(f)
            except Exception:
                usages = []
    else:
        usages = []
    usages.append(log_entry)
    with open(usages_path, "w") as f:
        json.dump(usages, f)
    save_usage(usage)
@app.on_message(filters.command("settings"))
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text("👋 Welcome! Send me a zip/tar/7z/rar archive and I'll extract it for you.")

@app.on_message(filters.command("help"))
async def help_cmd(client, message: Message):
    await message.reply_text(
        "/start - Welcome message\n"
        "/help - Usage info\n"
        "/status - Server info\n"
        "/info - Bot usage stats\n"
        "Send me a zip/tar/7z/rar archive and I'll extract it for you!"
    )
@app.on_message(filters.command("stats"))
@app.on_message(filters.command("status"))
async def status(client, message: Message):
    info = (
        f"OS: {platform.system()} {platform.release()}\n"
        f"CPU: {psutil.cpu_count()} cores\n"
        f"RAM: {psutil.virtual_memory().total // (1024**2)} MB\n"
        f"Disk: {psutil.disk_usage('/').percent}% used"
    )
    await message.reply_text(info)

def human_readable_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes // 1024} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.2f} MB"
    else:
        return f"{size_bytes / 1024 ** 3:.2f} GB"

@app.on_message(filters.command("usage"))
@app.on_message(filters.command("info"))
async def info(client, message: Message):
    usage = load_usage()
    users_count = len(usage.get("users", []))
    total_size = usage.get('archives_size', 0)
    msg = (
        f"Archives extracted: {usage.get('archives_count', 0)}\n"
        f"Files extracted: {usage.get('files_extracted', 0)}\n"
        f"Total archives size: {human_readable_size(total_size)}\n"
        f"Users: {users_count}"
    )
    await message.reply_text(msg)

def get_file_type(filename):
    if filename.endswith(".zip"):
        return "zip"
    elif filename.endswith(".tar") or filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        return "tar"
    elif filename.endswith(".7z"):
        return "7z"
    elif filename.endswith(".rar"):
        return "rar"
    return "unknown"

def get_media_type(filename):
    ext = filename.lower().split('.')[-1]
    if ext in ["mp4", "mkv", "mov", "avi", "webm"]:
        return "video"
    elif ext in ["mp3", "wav", "ogg", "flac", "m4a"]:
        return "audio"
    elif ext == "pdf":
        return "document"
    else:
        return "document"

@app.on_message(filters.document)
async def handle_document(client, message: Message):
    doc = message.document
    file_type = get_file_type(doc.file_name)
    if file_type not in ["zip", "tar", "7z", "rar"]:
        await message.reply_text("Please send a zip, tar, 7z, or rar archive.")
        return
    file_size = doc.file_size
    if file_size > MAX_FILE_SIZE:
        await message.reply_text(f"File is too large! Max allowed size is {MAX_FILE_SIZE//1024//1024}MB.")
        return
    user_id = str(message.from_user.id)
    # Store archive info in a global dict instead of app.storage
    if not hasattr(app, "user_contexts"):
        app.user_contexts = {}
    app.user_contexts[user_id] = {
        "archive": {
            "file_id": doc.file_id,
            "file_name": doc.file_name,
            "file_size": file_size,
            "file_type": file_type
        }
    }
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("EXTRACT", callback_data=f"extract|{user_id}")]
    ])
    await message.reply_text(
        f"Hi,\nYou want me to extract {doc.file_name}\n"
        f"Size: {file_size//1024} KB\n"
        f"Type: {file_type}",
        reply_markup=kb
    )

@app.on_callback_query(filters.regex(r"^extract\|"))
async def extract_callback(client, callback_query):
    await callback_query.answer("Extracting file...\nWill take a few seconds.", show_alert=True)
    try:
        await callback_query.message.delete()
    except Exception:
        pass
    user_id = callback_query.data.split("|")[1]
    # Retrieve archive info from the global dict
    archive = getattr(app, "user_contexts", {}).get(user_id, {}).get("archive")
    if not archive:
        await client.send_message(callback_query.message.chat.id, "No archive found. Please send a file first.")
        return
    if archive["file_size"] > MAX_FILE_SIZE:
        await client.send_message(callback_query.message.chat.id, f"File is too large! Max allowed size is {MAX_FILE_SIZE//1024//1024}MB.")
        return
    user_dir = DATA_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / archive["file_name"]
    # Download file
    await client.download_media(archive["file_id"], file_name=str(file_path))
    # Extract
    files_sent = 0
    extracted_files = []
    try:
        if archive["file_type"] == "zip":
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(user_dir)
                extracted_files = zf.namelist()
        elif archive["file_type"] == "tar":
            with tarfile.open(file_path, "r:*") as tf:
                tf.extractall(user_dir)
                extracted_files = tf.getnames()
        elif archive["file_type"] == "7z":
            with py7zr.SevenZipFile(file_path, mode="r") as z:
                z.extractall(path=user_dir)
                extracted_files = z.getnames()
        elif archive["file_type"] == "rar":
            with rarfile.RarFile(file_path) as rf:
                rf.extractall(user_dir)
                extracted_files = rf.namelist()
        # Send files
        for fname in extracted_files:
            fpath = user_dir / fname
            if fpath.is_file():
                media_type = get_media_type(fname)
                if media_type == "video":
                    await client.send_video(callback_query.message.chat.id, fpath)
                elif media_type == "audio":
                    await client.send_audio(callback_query.message.chat.id, fpath)
                else:
                    await client.send_document(callback_query.message.chat.id, fpath)
                files_sent += 1
        await client.send_message(callback_query.message.chat.id, f"Extracted and sent {files_sent} files.")
        update_usage(user_id, archive["file_size"], files_sent)
    except Exception as e:
        await client.send_message(callback_query.message.chat.id, f"Extraction failed: {e}")
    finally:
        shutil.rmtree(user_dir, ignore_errors=True)

if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    app.run()

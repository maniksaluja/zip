import json import os import time import zipfile import shutil import asyncio import subprocess import logging from pyrogram import Client, filters from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton from pyrogram.errors import FloodWait, ChannelPrivate from pathlib import Path from PIL import Image

Logger setup

logging.basicConfig( filename="vps_log.txt", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s" )

API_ID = 20886865 API_HASH = "754d23c04f9244762390c095d5d8fe2b" BOT_TOKEN = "8108094028:AAHE8BfBW1KvOLb-zQmBe_pj2c_KgZrRWvo"

channel1_id = None channel2_id = None user_modes = {}

app = Client("zip_upload_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

state_file = "bot_state.json" if not os.path.exists(state_file): with open(state_file, "w") as f: json.dump({"downloads": []}, f)

def save_state(): state = load_state() if not isinstance(state.get("downloads"), list): state["downloads"] = [] with open(state_file, "w") as f: json.dump(state, f)

def load_state(): if os.path.exists(state_file): with open(state_file, "r") as f: state = json.load(f) if not isinstance(state.get("downloads"), list): state["downloads"] = [] return state else: return {"downloads": []}

async def safe_edit(message, text, delay=1.5): await asyncio.sleep(delay) try: await message.edit_text(text) except Exception as e: logging.warning(f"Edit text failed: {e}")

@app.on_message(filters.command("mode") & filters.private) async def mode_selector(client: Client, message: Message): keyboard = InlineKeyboardMarkup([ [InlineKeyboardButton("Direct", callback_data="mode_direct")], [InlineKeyboardButton("Channel 1", callback_data="mode_ch1")], [InlineKeyboardButton("Both", callback_data="mode_both")] ]) await message.reply_text("Select upload mode:", reply_markup=keyboard)

@app.on_callback_query(filters.regex("mode_")) async def mode_callback(client, callback_query): user_id = callback_query.from_user.id mode = callback_query.data.split("_")[1] user_modes[user_id] = mode await callback_query.answer(f"Mode set to: {mode.capitalize()}", show_alert=True)

@app.on_message(filters.private & filters.document) async def handle_zip(client: Client, message: Message): logging.info(f"Received ZIP from {message.from_user.id}")

if not message.document or not message.document.file_name.endswith(".zip"):
    return await message.reply_text("Please send a valid ZIP file.")

mode = user_modes.get(message.from_user.id, "both")

state = load_state()
if message.document.file_id in state["downloads"]:
    return await message.reply_text("This file has already been processed.")

status_message = await message.reply_text("Downloading... 0%")
zip_path = f"downloads/{message.document.file_id}.zip"
os.makedirs("downloads", exist_ok=True)

start_time = time.time()
current_percent = 0

async def sync_progress(current, total):
    nonlocal current_percent
    percent = int((current / total) * 100)
    if percent != current_percent:
        current_percent = percent
        await safe_edit(status_message, f"Downloading...\n{percent}% completed", delay=0.5)

await message.download(file_name=zip_path, progress=sync_progress)
state["downloads"].append(message.document.file_id)
save_state()

await safe_edit(status_message, "Download complete. Unzipping...")

extract_path = f"extracted/{message.document.file_id}"
os.makedirs(extract_path, exist_ok=True)

try:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
except zipfile.BadZipFile:
    await safe_edit(status_message, "Invalid ZIP archive.")
    os.remove(zip_path)
    return

await safe_edit(status_message, "Unzipped. Starting upload...")

file_paths = list(Path(extract_path).rglob("*.*"))
if not file_paths:
    await safe_edit(status_message, "No files found in ZIP.")
    os.remove(zip_path)
    shutil.rmtree(extract_path)
    return

if channel1_id:
    try:
        await app.get_chat(channel1_id)
    except Exception as e:
        logging.error(f"Channel 1 access error: {e}")
        await safe_edit(status_message, f"Channel 1 is not accessible.")
        return

if channel2_id:
    try:
        await app.get_chat(channel2_id)
    except Exception as e:
        logging.error(f"Channel 2 access error: {e}")
        await safe_edit(status_message, f"Channel 2 is not accessible.")
        return

for i, file in enumerate(file_paths, 1):
    file_path = str(file)

    if file_path.lower().endswith(('.avi', '.mov', '.flv', '.mkv', '.webm')):
        converted_path = f"{file.stem}.mp4"
        try:
            subprocess.run([
                "ffmpeg", "-i", file_path, "-c:v", "libx264", "-preset", "fast", "-crf", "23", converted_path
            ], check=True)
            file_path = converted_path
        except subprocess.CalledProcessError as e:
            await safe_edit(status_message, f"FFmpeg conversion failed: {e}")
            logging.error(f"Video conversion failed: {e}")
            continue

    if file_path.lower().endswith(('gif', 'bmp', 'tiff', 'webp')):
        converted_img_path = f"{file.stem}.png"
        try:
            img = Image.open(file_path)
            img.save(converted_img_path, "PNG")
            file_path = converted_img_path
        except Exception as e:
            await safe_edit(status_message, f"Image conversion failed: {e}")
            logging.error(f"Image conversion failed: {e}")
            continue

    try:
        if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.flv', '.mkv', '.webm')):
            if mode == "direct":
                await client.send_video(message.from_user.id, video=file_path)
            elif mode == "ch1" and channel1_id:
                await app.send_video(chat_id=channel1_id, video=file_path)
            elif mode == "both" and channel1_id and channel2_id:
                await app.send_video(chat_id=channel1_id, video=file_path)
                await asyncio.sleep(2)
                await app.send_video(chat_id=channel2_id, video=file_path)
        elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            if mode == "direct":
                await client.send_photo(message.from_user.id, photo=file_path)
            elif mode == "ch1" and channel1_id:
                await app.send_photo(chat_id=channel1_id, photo=file_path)
            elif mode == "both" and channel1_id and channel2_id:
                await app.send_photo(chat_id=channel1_id, photo=file_path)
                await asyncio.sleep(2)
                await app.send_photo(chat_id=channel2_id, photo=file_path)
    except FloodWait as e:
        logging.warning(f"FloodWait: Sleeping for {e.value}s")
        await asyncio.sleep(e.value)
    except ChannelPrivate as e:
        logging.error(f"Channel access error: {e}")
        await safe_edit(status_message, f"Channel access error: {e}")
        continue

    await safe_edit(status_message, f"Uploaded {i}/{len(file_paths)} files...")
    await asyncio.sleep(1.5)

total_time = time.time() - start_time
await safe_edit(status_message, f"Upload complete in {total_time:.2f}s. Deleting ZIP from VPS...")

os.remove(zip_path)
shutil.rmtree(extract_path)

await safe_edit(status_message, "All done! ZIP file deleted from VPS.")
logging.info(f"Upload completed for {message.from_user.id} in {total_time:.2f}s")

app.run()


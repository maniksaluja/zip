import json
import os
import time
import zipfile
import shutil
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from pathlib import Path
from moviepy.editor import VideoFileClip  # For video conversion
from PIL import Image  # For image conversion

API_ID = 20886865
API_HASH = "754d23c04f9244762390c095d5d8fe2b"
BOT_TOKEN = "8108094028:AAHE8BfBW1KvOLb-zQmBe_pj2c_KgZrRWvo"

channel1_id = -1002692719794
channel2_id = -1002638090230

# user_id : mode (direct/channel1/both)
user_modes = {}

app = Client("zip_upload_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

state_file = "bot_state.json"

# Initialize or load the state file
if not os.path.exists(state_file):
    with open(state_file, "w") as f:
        json.dump({"downloads": []}, f)

def save_state():
    with open(state_file, "w") as f:
        json.dump({
            "downloads": user_modes,  # Save current user mode or download state
        }, f)

def load_state():
    with open(state_file, "r") as f:
        return json.load(f)

@app.on_message(filters.command("mode") & filters.private)
async def mode_selector(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Direct", callback_data="mode_direct")],
        [InlineKeyboardButton("Channel 1", callback_data="mode_ch1")],
        [InlineKeyboardButton("Both", callback_data="mode_both")]
    ])
    await message.reply_text("Select upload mode:", reply_markup=keyboard)

@app.on_callback_query(filters.regex("mode_"))
async def mode_callback(client, callback_query):
    user_id = callback_query.from_user.id
    mode = callback_query.data.split("_")[1]
    user_modes[user_id] = mode
    await callback_query.answer(f"Mode set to: {mode.capitalize()}", show_alert=True)

@app.on_message(filters.private & filters.document)
async def handle_zip(client: Client, message: Message):
    if not message.document or not message.document.file_name.endswith(".zip"):
        return await message.reply_text("Please send a valid ZIP file.")

    mode = user_modes.get(message.from_user.id, "both")

    # Check if the file was already processed
    state = load_state()
    if message.document.file_id in state["downloads"]:
        return await message.reply_text("This file has already been processed.")

    status_message = await message.reply_text("Downloading... 0%")
    zip_path = f"downloads/{message.document.file_id}.zip"
    os.makedirs("downloads", exist_ok=True)

    start_time = time.time()
    current_percent = 0

    def sync_progress(current, total):
        nonlocal current_percent
        percent = int((current / total) * 100)
        if percent != current_percent:
            current_percent = percent
            try:
                asyncio.run_coroutine_threadsafe(
                    status_message.edit_text(f"Downloading...\n{percent}% completed"),
                    app.loop
                )
            except Exception as e:
                print(f"Error during progress update: {e}")

    await message.download(
        file_name=zip_path,
        progress=sync_progress
    )

    # Mark the file as downloaded in state
    state["downloads"].append(message.document.file_id)
    save_state()

    await status_message.edit_text("Download complete. Unzipping...")

    extract_path = f"extracted/{message.document.file_id}"
    os.makedirs(extract_path, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
    except zipfile.BadZipFile:
        await status_message.edit_text("Invalid ZIP archive.")
        os.remove(zip_path)
        return

    await status_message.edit_text("Unzipped. Starting upload...")

    file_paths = list(Path(extract_path).rglob("*.*"))
    if not file_paths:
        await status_message.edit_text("No files found in ZIP.")
        os.remove(zip_path)  # Delete zip immediately after processing
        shutil.rmtree(extract_path)  # Clean up extracted folder
        return

    for i, file in enumerate(file_paths, 1):
        file_path = str(file)

        # Check and convert video format to .mp4
        if file_path.lower().endswith(('.avi', '.mov', '.flv', '.mkv', '.webm')):
            converted_file_path = f"{file.stem}.mp4"
            try:
                clip = VideoFileClip(file_path)
                clip.write_videofile(converted_file_path, codec='libx264')
                file_path = converted_file_path
            except Exception as e:
                await status_message.edit_text(f"Error during video conversion: {e}")
                continue

        # Check and convert image formats (e.g., GIF, BMP, etc.) to PNG
        if file_path.lower().endswith(('gif', 'bmp', 'tiff', 'webp')):
            converted_image_path = f"{file.stem}.png"
            try:
                img = Image.open(file_path)
                img.save(converted_image_path, "PNG")
                file_path = converted_image_path
            except Exception as e:
                await status_message.edit_text(f"Error during image conversion: {e}")
                continue

        try:
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.flv', '.mkv', '.webm')):
                if mode == "direct":
                    await client.send_video(message.from_user.id, video=file_path)
                elif mode == "ch1":
                    await app.send_video(chat_id=channel1_id, video=file_path)
                elif mode == "both":
                    await app.send_video(chat_id=channel1_id, video=file_path)
                    await app.send_video(chat_id=channel2_id, video=file_path)
            elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                if mode == "direct":
                    await client.send_photo(message.from_user.id, photo=file_path)
                elif mode == "ch1":
                    await app.send_photo(chat_id=channel1_id, photo=file_path)
                elif mode == "both":
                    await app.send_photo(chat_id=channel1_id, photo=file_path)
                    await app.send_photo(chat_id=channel2_id, photo=file_path)

        except FloodWait as e:
            await asyncio.sleep(e.value)

        await status_message.edit_text(f"Uploaded {i}/{len(file_paths)} files...")

    total_time = time.time() - start_time
    await status_message.edit_text(f"Upload complete in {total_time:.2f}s.\nDeleting ZIP from VPS...")

    # Delete files after use
    os.remove(zip_path)
    shutil.rmtree(extract_path)

    await status_message.edit_text("All done! ZIP file deleted from VPS.")

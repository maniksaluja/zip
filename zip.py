import os
import time
import zipfile
import shutil
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from pathlib import Path

API_ID = 20886865
API_HASH = "754d23c04f9244762390c095d5d8fe2b"
BOT_TOKEN = "8108094028:AAHE8BfBW1KvOLb-zQmBe_pj2c_KgZrRWvo"

channel1_id = -1002692719794
channel2_id = -1002638090230

# user_id : mode (direct/channel1/both)
user_modes = {}

app = Client("zip_upload_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


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

    status = await message.reply_text("Downloading... 0%")
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
                    status.edit_text(f"Downloading...\n{percent}% completed"),
                    app.loop
                )
            except:
                pass

    await message.download(
        file_name=zip_path,
        progress=sync_progress
    )

    await status.edit_text("Download complete. Unzipping...")

    extract_path = f"extracted/{message.document.file_id}"
    os.makedirs(extract_path, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
    except zipfile.BadZipFile:
        await status.edit_text("Invalid ZIP archive.")
        os.remove(zip_path)
        return

    await status.edit_text("Unzipped. Starting upload...")

    file_paths = list(Path(extract_path).rglob("*.*"))
    if not file_paths:
        await status.edit_text("No files found in ZIP.")
        return

    for i, file in enumerate(file_paths, 1):
        file_path = str(file)
        try:
            if mode == "direct":
                await client.send_document(message.from_user.id, document=file_path)
            elif mode == "ch1":
                await app.send_document(chat_id=channel1_id, document=file_path)
            elif mode == "both":
                await app.send_document(chat_id=channel1_id, document=file_path)
                await app.send_document(chat_id=channel2_id, document=file_path)
        except FloodWait as e:
            await asyncio.sleep(e.value)

        await status.edit_text(f"Uploaded {i}/{len(file_paths)} files...")

    total_time = time.time() - start_time
    await status.edit_text(f"Upload complete in {total_time:.2f}s.\nDeleting ZIP from VPS...")

    os.remove(zip_path)
    shutil.rmtree(extract_path)

    await status.edit_text("All done! ZIP file deleted from VPS.")


app.run()

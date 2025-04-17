import os
import time
import zipfile
import shutil
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pathlib import Path

API_ID = 20886865  # apna API ID
API_HASH = "754d23c04f9244762390c095d5d8fe2b"
BOT_TOKEN = "8108094028:AAHE8BfBW1KvOLb-zQmBe_pj2c_KgZrRWvo"

# Username ke jagah channel IDs
CHANNELS = [-1002692719794, -1002638090230]  # yahan apne channel IDs daalein

app = Client("zip_upload_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def progress(current, total, message, action):
    percent = (current / total) * 100
    asyncio.create_task(message.edit_text(f"{action}...\n{percent:.2f}% completed"))

@app.on_message(filters.private & filters.document)
async def handle_zip(client: Client, message: Message):
    if not message.document or not message.document.file_name.endswith(".zip"):
        return await message.reply_text("Please send a ZIP file.")

    status = await message.reply_text("Downloading... 0%")

    zip_path = f"downloads/{message.document.file_id}.zip"
    os.makedirs("downloads", exist_ok=True)

    start_time = time.time()

    await message.download(
        file_name=zip_path,
        progress=lambda current, total: progress(current, total, status, "Downloading"),
        progress_args=()
    )

    await status.edit_text("Download complete. Unzipping...")

    extract_path = f"extracted/{message.document.file_id}"
    os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    unzip_time = time.time() - start_time
    await status.edit_text(f"Unzip complete in {unzip_time:.2f}s. Uploading...")

    file_paths = list(Path(extract_path).rglob("*.*"))
    total_files = len(file_paths)

    if total_files == 0:
        return await status.edit_text("No files found inside ZIP.")

    for i, file in enumerate(file_paths, 1):
        for channel_id in CHANNELS:
            try:
                await app.send_document(chat_id=channel_id, document=str(file))
            except FloodWait as e:
                await asyncio.sleep(e.value)

        await status.edit_text(
            f"Uploading...\nFile {i}/{total_files} uploaded."
        )

    total_time = time.time() - start_time
    await status.edit_text(f"All done in {total_time:.2f}s!")

    # Cleanup
    os.remove(zip_path)
    shutil.rmtree(extract_path)

app.run()

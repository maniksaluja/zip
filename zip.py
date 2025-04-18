import os
import asyncio
import logging
import json
import zipfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image
import moviepy
import moviepy.editor as mp

clip = mp.VideoFileClip("your_video.mp4")
# Load sensitive data from environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Channel IDs
channel1_id = None
channel2_id = None

# File to save the selected mode
state_file = "state.json"

# Initialize bot
app = Client("mode_select_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load the current state
def load_state():
    try:
        with open(state_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save the current state
def save_state(state):
    with open(state_file, "w") as f:
        json.dump(state, f)

# Upload helpers
async def upload_video(client, chat_id, path):
    await client.send_video(chat_id, video=path)

async def upload_photo(client, chat_id, path):
    await client.send_photo(chat_id, photo=path)

async def upload_document(client, chat_id, path):
    await client.send_document(chat_id, document=path)

# Mode selection command
@app.on_message(filters.command("mode") & filters.user(OWNER_ID))
async def select_mode(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Channel 1", callback_data="mode_channel1")],
        [InlineKeyboardButton("Channel 2", callback_data="mode_channel2")]
    ])
    await message.reply("Select the channel to upload files:", reply_markup=keyboard)

# Handle button press
@app.on_callback_query()
async def handle_callback_query(client, callback_query):
    global channel1_id, channel2_id

    user_id = callback_query.from_user.id
    data = callback_query.data
    state = load_state()

    if data == "mode_channel1":
        if channel1_id is None:
            await callback_query.answer("Channel 1 ID is not set.", show_alert=True)
            return
        state[str(user_id)] = {"mode": "channel1"}
    elif data == "mode_channel2":
        if channel2_id is None:
            await callback_query.answer("Channel 2 ID is not set.", show_alert=True)
            return
        state[str(user_id)] = {"mode": "channel2"}
    else:
        await callback_query.answer("Invalid mode selected.", show_alert=True)
        return

    save_state(state)
    await callback_query.answer("Mode selected successfully!")
    await callback_query.message.edit_text("Mode has been set. Now send a ZIP file.")

# Set Channel 1 ID
@app.on_message(filters.command("setchannel1") & filters.user(OWNER_ID))
async def set_channel1(client, message):
    global channel1_id
    try:
        channel1_id = int(message.text.split(None, 1)[1])
        await message.reply(f"Channel 1 set to: `{channel1_id}`")
    except Exception:
        await message.reply("Please provide a valid Channel 1 ID.")

# Set Channel 2 ID
@app.on_message(filters.command("setchannel2") & filters.user(OWNER_ID))
async def set_channel2(client, message):
    global channel2_id
    try:
        channel2_id = int(message.text.split(None, 1)[1])
        await message.reply(f"Channel 2 set to: `{channel2_id}`")
    except Exception:
        await message.reply("Please provide a valid Channel 2 ID.")

# Handle ZIP file
@app.on_message(filters.document & filters.user(OWNER_ID))
async def handle_zip_file(client, message):
    user_id = str(message.from_user.id)
    state = load_state()
    mode = state.get(user_id, {}).get("mode")

    if not mode:
        await message.reply("Please select a mode first using /mode command.")
        return

    channel_id = channel1_id if mode == "channel1" else channel2_id
    if channel_id is None:
        await message.reply("Channel ID not set.")
        return

    file_path = await message.download()
    extract_path = f"extracted_{user_id}"
    os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)

    os.remove(file_path)

    await message.reply("Uploading files...")

    # Separate files by type
    videos, images, documents = [], [], []

    for root, _, files in os.walk(extract_path):
        for file_name in sorted(files):
            file_path = os.path.join(root, file_name)
            ext = file_name.lower().split('.')[-1]

            if ext in ("mp4", "mkv", "avi", "mov"):
                videos.append(file_path)
            elif ext in ("jpg", "jpeg", "png", "gif", "bmp"):
                images.append(file_path)
            else:
                documents.append(file_path)

    # Upload files in categorized order
    for v in videos:
        await upload_video(client, channel_id, v)
    for img in images:
        await upload_photo(client, channel_id, img)
    for doc in documents:
        await upload_document(client, channel_id, doc)

    # Cleanup
    for path in [*videos, *images, *documents]:
        os.remove(path)
    os.rmdir(extract_path)

    await message.reply("All files uploaded successfully.")

# Run the bot
app.run()

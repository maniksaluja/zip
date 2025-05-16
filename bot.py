import json
import uuid
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# File to store messages and media
MESSAGE_FILE = "messages.json"

# Initialize JSON file if it doesn't exist
def init_storage():
    try:
        with open(MESSAGE_FILE, "x") as f:
            json.dump({}, f)
    except FileExistsError:
        pass

# Save message or media with unique ID
def save_message(unique_id, data):
    try:
        with open(MESSAGE_FILE, "r+") as f:
            db = json.load(f)
            db[unique_id] = data
            f.seek(0)
            f.truncate()
            json.dump(db, f, indent=4)
    except Exception as e:
        print(f"Error saving message: {e}")

# Load message or media by unique ID
def load_message(unique_id):
    try:
        with open(MESSAGE_FILE, "r") as f:
            db = json.load(f)
            return db.get(unique_id, None)
    except Exception as e:
        print(f"Error loading message: {e}")
        return None

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        unique_id = args[0]
        data = load_message(unique_id)
        if not data:
            await update.message.reply_text("Message or media not found or expired!")
            return

        content_type = data.get("type")
        content = data.get("content")
        caption = data.get("caption", "")

        if content_type == "text":
            await update.message.reply_text(content)
        elif content_type == "photo":
            await update.message.reply_photo(photo=content, caption=caption)
        elif content_type == "video":
            await update.message.reply_video(video=content, caption=caption)
        elif content_type == "audio":
            await update.message.reply_audio(audio=content, caption=caption)
        elif content_type == "document":
            await update.message.reply_document(document=content, caption=caption)
        else:
            await update.message.reply_text("Unsupported content type!")
    else:
        await update.message.reply_text(
            "Welcome to the bot! Send a message, photo, video, audio, or document with /generate to create a unique link."
        )

# /generate command handler for text
async def generate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a message: /generate <message>")
        return

    message = " ".join(context.args)
    unique_id = str(uuid.uuid4())
    data = {"type": "text", "content": message}
    save_message(unique_id, data)

    bot_username = "@YourBot"  # Replace with your bot's username
    link = f"https://t.me/{bot_username}?start={unique_id}"
    await update.message.reply_text(f"Here is your unique link:\n{link}")

# Handler for media (photo, video, audio, document)
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    unique_id = str(uuid.uuid4())
    bot_username = "@YourBot"  # Replace with your bot's username
    link = f"https://t.me/{bot_username}?start={unique_id}"
    caption = message.caption or ""

    if message.photo:
        file_id = message.photo[-1].file_id  # Get the highest resolution photo
        data = {"type": "photo", "content": file_id, "caption": caption}
    elif message.video:
        file_id = message.video.file_id
        data = {"type": "video", "content": file_id, "caption": caption}
    elif message.audio:
        file_id = message.audio.file_id
        data = {"type": "audio", "content": file_id, "caption": caption}
    elif message.document:
        file_id = message.document.file_id
        data = {"type": "document", "content": file_id, "caption": caption}
    else:
        await message.reply_text("Unsupported media type!")
        return

    save_message(unique_id, data)
    await message.reply_text(f"Here is your unique link:\n{link}")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("An error occurred. Please try again.")

def main():
    # Replace with your bot token from BotFather
    BOT_TOKEN = "7739730998:AAEB8i_2hItBOj9gNYs9bDgAsrDWACAUE7k"  # Add your bot token here

    # Initialize storage
    init_storage()

    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("generate", generate_text))
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL,
            handle_media
        )
    )

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

from telethon import TelegramClient, events
from telethon.tl.types import Document, Photo
import os

# Replace these with your actual values
api_id = 20886865
api_hash = '754d23c04f9244762390c095d5d8fe2b'
bot_token = '8145736202:AAEqjJa62tuj40TPaYehFkAJOVJiQk6doLw'
session_name = 'name'

# Initialize the Telegram client
client = TelegramClient(session_name, api_id, api_hash)

async def extract_file_data(message):
    """
    Extracts 7 data points from a Telegram message with media.
    """
    data = {
        "File ID": None,
        "Unique File ID": None,
        "Metadata": {},
        "File Content": None,
        "Chat/Context Info": {},
        "User Data": {},
        "Encryption Keys": None
    }

    if message.media:
        media = message.media

        if isinstance(media, (Document, Photo)):
            # File ID
            data["File ID"] = getattr(media, 'id', None)

            # Unique File ID
            data["Unique File ID"] = getattr(media, 'file_reference', None) or media.id

            # Metadata
            data["Metadata"] = {
                "File Type": type(media).__name__,
                "File Size": getattr(media, 'size', None),
                "File Name": getattr(media, 'file_name', None),
                "MIME Type": getattr(media, 'mime_type', None),
                "Resolution": f"{getattr(media, 'w', '')}x{getattr(media, 'h', '')}" if hasattr(media, 'w') and hasattr(media, 'h') else None,
                "Duration": getattr(media, 'duration', None),
                "Date": str(message.date)
            }

            # Download media
            file_name = data["Metadata"]["File Name"] or f"{message.id}.bin"
            file_path = os.path.join("downloads", f"{message.id}_{file_name}")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            downloaded_file = await client.download_media(message, file=file_path)
            data["File Content"] = downloaded_file if downloaded_file else "Download failed"

            # Chat/Context Info
            chat = await message.get_chat()
            data["Chat/Context Info"] = {
                "Chat ID": message.chat_id,
                "Message ID": message.id,
                "Chat Title": getattr(chat, 'title', None)
            }

            # User Data
            sender = await message.get_sender()
            data["User Data"] = {
                "User ID": sender.id if sender else None,
                "Username": getattr(sender, 'username', None),
                "First Name": getattr(sender, 'first_name', None)
            }

            # Encryption Keys (secret chat check placeholder)
            data["Encryption Keys"] = "End-to-end encrypted (Secret Chat)" if message.is_private and not message.via_bot else "Not applicable"

    return data

# Event handler
@client.on(events.NewMessage)
async def handle_new_message(event):
    message = event.message
    if message.media:
        file_data = await extract_file_data(message)
        print("\nExtracted File Data:")
        for key, value in file_data.items():
            print(f"{key}:")
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    print(f"  {sub_key}: {sub_val}")
            else:
                print(f"  {value}")

        await event.reply(str(file_data))

# Main entry point
async def main():
    await client.start(bot_token=bot_token)
    print("Bot is running...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

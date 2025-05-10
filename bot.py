from telethon import TelegramClient, events
from telethon.tl.types import Document, Photo, Video
import os

# Replace these with your own values
api_id = '20886865'
api_hash = '754d23c04f9244762390c095d5d8fe2b"'
bot_token = '8145736202:AAEqjJa62tuj40TPaYehFkAJOVJiQk6doLw'  # Optional, if using a bot
session_name = 'name'

# Initialize the Telegram client
client = TelegramClient(session_name, api_id, api_hash)

async def extract_file_data(message):
    """
    Extracts the 7 specified data points for a file in a Telegram message.
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

    # Check if the message contains a file (document, photo, video, etc.)
    if message.media:
        media = message.media

        # Handle different types of media
        if isinstance(media, (Document, Photo, Video)):
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
                "Resolution": getattr(media, 'w', None) and getattr(media, 'h', None) and f"{media.w}x{media.h}",
                "Duration": getattr(media, 'duration', None),
                "Date": str(message.date)
            }

            # File Content (Download the file)
            file_path = f"downloads/{message.id}_{data['Metadata']['File Name'] or 'file'}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            downloaded_file = await client.download_media(message.media, file=file_path)
            data["File Content"] = downloaded_file if downloaded_file else "Download failed"

            # Chat/Context Info
            data["Chat/Context Info"] = {
                "Chat ID": message.chat_id,
                "Message ID": message.id,
                "Chat Title": (await message.get_chat()).title if message.chat else None
            }

            # User Data
            sender = await message.get_sender()
            data["User Data"] = {
                "User ID": sender.id if sender else None,
                "Username": sender.username if sender and hasattr(sender, 'username') else None,
                "First Name": sender.first_name if sender and hasattr(sender, 'first_name') else None
            }

            # Encryption Keys (only for secret chats)
            if message.is_private and hasattr(message, 'via_bot') and message.via_bot is None:
                data["Encryption Keys"] = "End-to-end encrypted (Secret Chat)" if message.is_private else "Not applicable"
            else:
                data["Encryption Keys"] = "Not applicable (Regular Chat)"

    return data

# Event handler for new messages
@client.on(events.NewMessage)
async def handle_new_message(event):
    message = event.message
    if message.media:  # Process only messages with media
        file_data = await extract_file_data(message)
        
        # Pretty print the extracted data
        print("\nExtracted File Data:")
        for key, value in file_data.items():
            print(f"{key}:")
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            else:
                print(f"  {value}")
        
        # Optionally, send the data back to the chat
        await event.reply(str(file_data))

# Start the client
async def main():
    await client.start(bot_token=bot_token)  # Use bot_token for bot, or remove for user client
    print("Bot is running...")
    await client.run_until_disconnected()

# Run the client
if __name__ == '__main__':
    client.loop.run_until_complete(main())

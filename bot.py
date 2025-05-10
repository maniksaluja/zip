from telethon import TelegramClient, events
import os

# Replace these with your own values
api_id = 20886865
api_hash = '754d23c04f9244762390c095d5d8fe2b'
bot_token = '8145736202:AAEqjJa62tuj40TPaYehFkAJOVJiQk6doLw'
session_name = 'name'

# Initialize the Telegram client
client = TelegramClient(session_name, api_id, api_hash)

async def extract_file_data(message):
    data = {
        "File ID": None,
        "Unique File ID": None,
        "Metadata": {},
        "File Content": None,
        "Chat/Context Info": {},
        "User Data": {},
        "Encryption Keys": None
    }

    if not message.media or not message.file:
        return data

    file = message.file
    data["File ID"] = file.id

    # Fallback to file.id if file_reference is not available
    data["Unique File ID"] = getattr(file, 'file_reference', None) or file.id

    data["Metadata"] = {
        "File Type": file.mime_type or 'Unknown',
        "File Size": file.size,
        "File Name": file.name,
        "MIME Type": file.mime_type,
        "Resolution": f"{file.width}x{file.height}" if file.width and file.height else None,
        "Duration": file.duration,
        "Date": str(message.date)
    }

    file_name = file.name or f"{message.id}.bin"
    file_path = os.path.join("downloads", f"{message.id}_{file_name}")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    downloaded_file = await client.download_media(message, file=file_path)
    data["File Content"] = downloaded_file if downloaded_file else "Download failed"

    chat = await message.get_chat()
    data["Chat/Context Info"] = {
        "Chat ID": message.chat_id,
        "Message ID": message.id,
        "Chat Title": getattr(chat, 'title', None)
    }

    sender = await message.get_sender()
    data["User Data"] = {
        "User ID": sender.id if sender else None,
        "Username": getattr(sender, 'username', None),
        "First Name": getattr(sender, 'first_name', None)
    }

    data["Encryption Keys"] = "End-to-end encrypted (Secret Chat)" if message.is_private and not message.via_bot else "Not applicable"
    return data

# Event handler for new messages
@client.on(events.NewMessage)
async def handle_new_message(event):
    message = event.message
    if message.media:
        file_data = await extract_file_data(message)

        # Pretty print
        print("\nExtracted File Data:")
        for key, value in file_data.items():
            print(f"{key}:")
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            else:
                print(f"  {value}")

        await event.reply(str(file_data))

# Start the client
async def main():
    await client.start(bot_token=bot_token)
    print("Bot is running...")
    await client.run_until_disconnected()

# Run
if __name__ == '__main__':
    client.loop.run_until_complete(main())

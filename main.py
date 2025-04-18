import os
import zipfile
import patoolib
import json
from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
from datetime import datetime

# Config storage
CONFIG_FILE = 'config.json'
default_config = {
    'channel_1': '',
    'channel_2': '',
    'current_mode': 1
}

# Load or create config
def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f)
        return default_config

config = load_config()

API_ID=20886865
API_HASH="754d23c04f9244762390c095d5d8fe2b"
BOT_TOKEN="8108094028:AAHE8BfBW1KvOLb-zQmBe_pj2c_KgZrRWvo"

# Initialize Pyrogram client
app = Client(
    "zip_extractor_bot",
    api_id=API_ID,  # Get from my.telegram.org
    api_hash=API_HASH,  # Get from my.telegram.org
    bot_token=BOT_TOKEN
)


@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    await message.reply_text(
        "Welcome! Send me any zip file and I'll extract it.\n"
        "Commands:\n"
        "/mode - Set delivery mode (1: Direct, 2: Channel 1, 3: Both channels)\n"
        "/setchannel1 - Set Channel 1 ID\n"
        "/setchannel2 - Set Channel 2 ID"
    )

@app.on_message(filters.command("mode"))
async def mode_command(client, message: Message):
    try:
        mode = int(message.text.split()[1])
        if 1 <= mode <= 3:
            config['current_mode'] = mode
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            await message.reply_text(f"Mode set to {mode}")
        else:
            raise ValueError
    except:
        await message.reply_text("Please use: /mode [1-3]")

@app.on_message(filters.command("setchannel1"))
async def setchannel1_command(client, message: Message):
    try:
        channel_id = message.text.split()[1]
        try:
            await app.get_chat(channel_id)
        except:
            return await message.reply_text(f"Make sure that bot is added in this channel {channel_id}")
        config['channel_1'] = channel_id
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        await message.reply_text(f"channel_1 set to {channel_id}")
    except:
        await message.reply_text(f"Please use: /setchannel1 [channel_id]")

@app.on_message(filters.command("setchannel2"))
async def setchannel2_command(client, message: Message):
    try:
        channel_id = message.text.split()[1]
        try:
            await app.get_chat(channel_id)
        except:
            return await message.reply_text(f"Make sure that bot is added in this channel {channel_id}")
        config['channel_2'] = channel_id
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        await message.reply_text(f"channel_2 set to {channel_id}")
    except:
        await message.reply_text(f"Please use: /setchannel2 [channel_id]")


async def download_progress_callback(current, total, message):
    try:
        percent = (current * 100) / total
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        await message.edit_text(
            text=f"Downloading: {percent:.1f}%\n"
                 f"{current_mb:.2f}MB/{total_mb:.2f}MB"
        )
    except:
        pass

async def upload_progress_callback(current, total, message, text):
    try:
        percent = (current * 100) / total
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        text += f"\n\n Current file Uploading: {percent:.1f}%"
        text += f"{current_mb:.2f}MB/{total_mb:.2f}MB"
        await message.edit_text(text)
    except:
        pass

@app.on_message(filters.document)
async def handle_zip(client:Client, message: Message):
    status_message = await message.reply_text("Starting download...")
    
    # Validate mode and channels first
    current_mode = config['current_mode']
    if current_mode in [2, 3]:
        if current_mode == 2 and not config['channel_1']:
            return await status_message.edit_text("Please set channel 1 first using /setchannel1")
        if current_mode == 3 and (not config['channel_1'] or not config['channel_2']):
            return await status_message.edit_text("Please set both channels first using /setchannel1 and /setchannel2")
            
        # Check if bot has access to channels
        try:
            if config['channel_1']:
                await app.get_chat(int(config['channel_1']))
            if current_mode == 3 and config['channel_2']:
                await app.get_chat(int(config['channel_2']))
        except Exception as e:
            return await status_message.edit_text(f"Please make sure bot is added to all required channels: {str(e)}")
    
    # Download file
    zip_file_name = message.document.file_name
    download_path = f"downloads/{zip_file_name}"
    extract_path = f"extracted/{zip_file_name.rsplit('.', 1)[0]}"
    
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("extracted", exist_ok=True)
    
    try:
        await message.download(
            file_name=download_path,
            progress=download_progress_callback,
            progress_args=(status_message,)
        )
        
        await status_message.edit_text("Extracting files...")
        
        # Extract files
        if zip_file_name.endswith('.zip'):
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        else:
            patoolib.extract_archive(download_path, outdir=extract_path)

        # Send files
        total_files = sum([len(files) for _, _, files in os.walk(extract_path)])
        processed_files = 0
        err =False
        for root, _, files in os.walk(extract_path):
            for file in files:
                file_path = os.path.join(root, file)
                processed_files += 1
                
                progress = (processed_files / total_files) * 100
                TEXT = f"Uploading: {processed_files}/{total_files} files ({progress:.1f}%)"
                await status_message.edit_text(TEXT)

                try:
                    # Determine file type
                    mime_type = None
                    file_ext = file.lower().split('.')[-1] if '.' in file else ''
                    
                    # Check file type based on extension
                    if file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                        send_method = 'photo'
                    elif file_ext in ['mp4', 'avi', 'mkv', 'mov']:
                        send_method = 'video'
                    elif file_ext in ['mp3', 'wav', 'ogg', 'm4a']:
                        send_method = 'audio'
                    else:
                        send_method = 'document'

                    # Send file based on mode
                    if current_mode == 1:
                        if send_method == 'photo':
                            await message.reply_photo(
                                photo=file_path, 
                                quote=True,
                                progress=upload_progress_callback,
                                progress_args=(status_message,TEXT) 
                                )
                        elif send_method == 'video':
                            await message.reply_video(
                                video=file_path, 
                                quote=True,
                                progress=upload_progress_callback,
                                progress_args=(status_message,TEXT)
                                )
                        elif send_method == 'audio':
                            await message.reply_audio(
                                audio=file_path, 
                                quote=True,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                                )
                        else:
                            await message.reply_document(
                                document=file_path,
                                quote=True,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                            )
                    elif current_mode == 2:
                        if send_method == 'photo':
                            await client.send_photo(
                                chat_id=int(config['channel_1']), 
                                photo=file_path,
                                caption=zip_file_name,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                                )
                        elif send_method == 'video':
                            await client.send_video(
                                chat_id=int(config['channel_1']), 
                                video=file_path,
                                caption=zip_file_name,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                                )
                        elif send_method == 'audio':
                            await client.send_audio(
                                chat_id=int(config['channel_1']), 
                                audio=file_path,
                                caption=zip_file_name,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                                )
                        else:
                            await client.send_document(
                                chat_id=int(config['channel_1']), 
                                document=file_path,
                                caption=zip_file_name,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                                )
                    else:  # mode 3
                        for channel_id in [config['channel_1'], config['channel_2']]:
                            if send_method == 'photo':
                                await client.send_photo(
                                    chat_id=int(channel_id), 
                                    photo=file_path,
                                    caption=zip_file_name,
                                    progress=upload_progress_callback,
                                    progress_args=(status_message, TEXT)
                                    )
                            elif send_method == 'video':
                                await client.send_video(
                                    chat_id=int(channel_id), 
                                    video=file_path,
                                    caption=zip_file_name,
                                    progress=upload_progress_callback,
                                    progress_args=(status_message, TEXT)
                                    )
                            elif send_method == 'audio':
                                await client.send_audio(
                                    chat_id=int(channel_id), 
                                    audio=file_path,
                                    caption=zip_file_name,
                                    progress=upload_progress_callback,
                                    progress_args=(status_message, TEXT)
                                    )
                            else:
                                await client.send_document(
                                    chat_id=int(channel_id), 
                                    document=file_path,
                                    caption=zip_file_name,
                                    progress=upload_progress_callback,
                                    progress_args=(status_message, TEXT)
                                    )
                                
                except Exception as e:
                    print(f"Error sending {file_path}: {str(e)}")
                    await status_message.edit_text(f"Error sending {file}: {str(e)}")
                    err = True

        # Cleanup
        os.remove(download_path)
        for root, dirs, files in os.walk(extract_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(extract_path)

        if not err:
            await status_message.edit_text("All files processed successfully!")
        
    except Exception as e:
        print(e)
        await status_message.edit_text(f"Error: {str(e)}")

app.run()

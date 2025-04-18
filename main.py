import os
import zipfile
import patoolib
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors.exceptions import FloodWait
from collections import defaultdict

# Queue management
user_queues = defaultdict(asyncio.Queue)
user_tasks = {}

# Progress tracking
download_progress = {}
upload_progress = {}

async def process_user_queue(user_id: int):
    queue = user_queues[user_id]
    while True:
        try:
            message, status_message = await queue.get()
            try:
                await process_zip_file(message, status_message)
            except Exception as e:
                print(f"Error processing file for user {user_id}: {str(e)}")
            finally:
                queue.task_done()
        except asyncio.CancelledError:
            break

async def download_progress_callback(current, total, message:Message):
    try:
        message_id = f"{message.chat.id}_{message.id}"
        percent = (current * 100) / total
        last_percent = download_progress.get(message_id, 0)
        
        if percent - last_percent >= 5 or percent >= 100:
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            try:
                await message.edit_text(
                    text=f"Downloading: {percent:.1f}%\n"
                         f"{current_mb:.2f}MB/{total_mb:.2f}MB"
                )
                download_progress[message_id] = percent
            except FloodWait as x:
                await asyncio.sleep(int(x.value))
    except:
        pass

async def upload_progress_callback(current, total, message:Message, text):
    try:
        message_id = f"{message.chat.id}_{message.id}"
        percent = (current * 100) / total
        last_percent = upload_progress.get(message_id, 0)
        
        if percent - last_percent >= 10 or percent >= 100:
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            upload_text = text + f"\n\nCurrent file Uploading: {percent:.1f}%\n"
            upload_text += f"{current_mb:.2f}MB/{total_mb:.2f}MB"
            try:
                await message.edit_text(upload_text)
                upload_progress[message_id] = percent
            except FloodWait as x:
                await asyncio.sleep(int(x.value))
            
            # Cleanup when upload complete
            if percent >= 100:
                upload_progress.pop(message_id, None)
    except:
        pass

async def process_zip_file(message: Message, status_message: Message):
    current_mode = config['current_mode']
    if current_mode in [2, 3]:
        if current_mode == 2 and not config['channel_1']:
            return await status_message.edit_text("Please set channel 1 first using /setchannel1")
        if current_mode == 3 and (not config['channel_1'] or not config['channel_2']):
            return await status_message.edit_text("Please set both channels first using /setchannel1 and /setchannel2")
            
        try:
            if config['channel_1']:
                await app.get_chat(int(config['channel_1']))
            if current_mode == 3 and config['channel_2']:
                await app.get_chat(int(config['channel_2']))
        except Exception as e:
            return await status_message.edit_text(f"Please make sure bot is added to all required channels: {str(e)}")
    
    zip_file_name = message.document.file_name
    download_path = f"downloads/{zip_file_name}"
    extract_path = f"extracted/{zip_file_name.rsplit('.', 1)[0]}"
    
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("extracted", exist_ok=True)
    
    try:
        await retry_with_flood_wait(
            message.download,
            file_name=download_path,
            progress=download_progress_callback,
            progress_args=(status_message,)
        )
        
        try:
            await status_message.edit_text("Extracting files...")
        except:
            pass
        
        if zip_file_name.endswith('.zip'):
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        else:
            patoolib.extract_archive(download_path, outdir=extract_path)

        total_files = sum([len(files) for _, _, files in os.walk(extract_path)])
        processed_files = 0
        err = False
        for root, _, files in os.walk(extract_path):
            for file in files:
                file_path = os.path.join(root, file)
                processed_files += 1
                
                progress = (processed_files / total_files) * 100
                TEXT = f"Uploading: {processed_files}/{total_files} files ({progress:.1f}%)"
                
                if processed_files == 1 or processed_files == total_files or processed_files % max(1, total_files//10) == 0:
                    try:
                        await retry_with_flood_wait(status_message.edit_text, TEXT)
                    except:
                        pass

                try:
                    mime_type = None
                    file_ext = file.lower().split('.')[-1] if '.' in file else ''
                    
                    if file_ext in ['jpg', 'jpeg', 'png']:
                        send_method = 'photo'
                    elif file_ext in ['mp4', 'avi', 'mkv', 'mov', 'gif', 'webm', 'flv', 'wmv', 'm4v', '3gp', 'ts', 'f4v']:
                        send_method = 'video'
                    elif file_ext in ['mp3', 'wav', 'ogg', 'm4a']:
                        send_method = 'audio'
                    else:
                        send_method = 'document'

                    if current_mode == 1:
                        if send_method == 'photo':
                            await retry_with_flood_wait(
                                message.reply_photo,
                                photo=file_path,
                                quote=True,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                            )
                        elif send_method == 'video':
                            await retry_with_flood_wait(
                                message.reply_video,
                                video=file_path,
                                quote=True,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                            )
                        elif send_method == 'audio':
                            await retry_with_flood_wait(
                                message.reply_audio,
                                audio=file_path,
                                quote=True,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                            )
                        else:
                            await retry_with_flood_wait(
                                message.reply_document,
                                document=file_path,
                                quote=True,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT)
                            )
                    elif current_mode == 2:
                        if send_method == 'photo':
                            await retry_with_flood_wait(
                                app.send_photo,
                                chat_id=int(config['channel_1']), 
                                photo=file_path,
                                caption=zip_file_name,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT),
                                reply_to_message_id = message.id
                            )
                        elif send_method == 'video':
                            await retry_with_flood_wait(
                                app.send_video,
                                chat_id=int(config['channel_1']), 
                                video=file_path,
                                caption=zip_file_name,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT),
                                reply_to_message_id = message.id
                            )
                        elif send_method == 'audio':
                            await retry_with_flood_wait(
                                app.send_audio,
                                chat_id=int(config['channel_1']), 
                                audio=file_path,
                                caption=zip_file_name,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT),
                                reply_to_message_id = message.id
                            )
                        else:
                            await retry_with_flood_wait(
                                app.send_document,
                                chat_id=int(config['channel_1']), 
                                document=file_path,
                                caption=zip_file_name,
                                progress=upload_progress_callback,
                                progress_args=(status_message, TEXT),
                                reply_to_message_id = message.id
                            )
                    else:
                        for channel_id in [config['channel_1'], config['channel_2']]:
                            if send_method == 'photo':
                                await retry_with_flood_wait(
                                    app.send_photo,
                                    chat_id=int(channel_id), 
                                    photo=file_path,
                                    caption=zip_file_name,
                                    progress=upload_progress_callback,
                                    progress_args=(status_message, TEXT),
                                    reply_to_message_id = message.id
                                )
                            elif send_method == 'video':
                                await retry_with_flood_wait(
                                    app.send_video,
                                    chat_id=int(channel_id), 
                                    video=file_path,
                                    caption=zip_file_name,
                                    progress=upload_progress_callback,
                                    progress_args=(status_message, TEXT),
                                    reply_to_message_id = message.id
                                )
                            elif send_method == 'audio':
                                await retry_with_flood_wait(
                                    app.send_audio,
                                    chat_id=int(channel_id), 
                                    audio=file_path,
                                    caption=zip_file_name,
                                    progress=upload_progress_callback,
                                    progress_args=(status_message, TEXT),
                                    reply_to_message_id = message.id
                                )
                            else:
                                await retry_with_flood_wait(
                                    app.send_document,
                                    chat_id=int(channel_id), 
                                    document=file_path,
                                    caption=zip_file_name,
                                    progress=upload_progress_callback,
                                    progress_args=(status_message, TEXT),
                                    reply_to_message_id = message.id
                                )
                                
                except Exception as e:
                    print(f"Error sending {file_path}: {str(e)}")
                    err = True
                    continue

        os.remove(download_path)
        for root, dirs, files in os.walk(extract_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(extract_path)

        # Cleanup download progress after completion
        message_id = f"{status_message.chat.id}_{status_message.id}"
        download_progress.pop(message_id, None)

        if not err:
            await status_message.edit_text("All files processed successfully!")
        
    except FloodWait as x:
        await status_message.edit_text(f"Rate limited. Bot will resume in {int(x.value)} seconds.")
        await asyncio.sleep(int(x.value))
    except Exception as e:
        print(e)
        # Cleanup on error
        message_id = f"{status_message.chat.id}_{status_message.id}"
        download_progress.pop(message_id, None)
        upload_progress.pop(message_id, None)
        await status_message.edit_text(f"Critical Error: {str(e)}")

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

API_ID=26974987
API_HASH="449b9bb5b57b6f91410031c806036a27"
BOT_TOKEN="7825330030:AAGFl-VwMFonFqaJggVzL3Cs12URtuZy4lw"

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
        # Check if any tasks are running and get their progress
        active_tasks = []
        for user_id, task in user_tasks.items():
            if not task.done():
                queue_size = user_queues[user_id].qsize()
                # Get download progress if any
                download_status = next((f"{v:.1f}%" for k, v in download_progress.items() 
                                     if k.startswith(f"{user_id}_")), None)
                # Get upload progress if any
                upload_status = next((f"{v:.1f}%" for k, v in upload_progress.items() 
                                   if k.startswith(f"{user_id}_")), None)
                
                status = f"User {user_id}: Queue size: {queue_size}"
                if download_status:
                    status += f", Downloading: {download_status}"
                if upload_status:
                    status += f", Uploading: {upload_status}"
                active_tasks.append(status)

        if active_tasks:
            status_text = "Cannot change mode while tasks are running:\n" + "\n".join(active_tasks)
            await message.reply_text(status_text)
            return

        mode = int(message.text.split()[1])
        if 1 <= mode <= 3:
            config['current_mode'] = mode
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            await message.reply_text(f"Mode set to {mode}")
        else:
            raise ValueError
    except ValueError:
        await message.reply_text("Please use: /mode [1-3]")
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")

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


async def retry_with_flood_wait(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except FloodWait as x:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(int(x.value))
            continue
        except Exception as e:
            raise

@app.on_message(filters.document)
async def handle_zip(client: Client, message: Message):
    user_id = message.from_user.id
    status_message = await message.reply_text("Processing request...")
    
    # Add to user's queue
    if user_id not in user_tasks or user_tasks[user_id].done():
        # Start new queue processor for user
        user_tasks[user_id] = asyncio.create_task(process_user_queue(user_id))
    
    queue_size = user_queues[user_id].qsize()
    if queue_size > 0:
        await status_message.edit_text(f"Added to queue. Position: {queue_size + 1}")
    
    # Add to queue
    await user_queues[user_id].put((message, status_message))

@app.on_disconnect()
async def cleanup():
    # Cancel all running queue processors
    for task in user_tasks.values():
        if not task.done():
            task.cancel()
    # Wait for all tasks to complete
    await asyncio.gather(*user_tasks.values(), return_exceptions=True)

app.run()

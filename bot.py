from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChannelInvalid, ChannelPrivate, PeerIdInvalid
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import logging
import re
import time
from urllib.parse import quote

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
API_ID = "20886865"
API_HASH = "754d23c04f9244762390c095d5d8fe2b"
BOT_TOKEN = "8145736202:AAEqjJa62tuj40TPaYehFkAJOVJiQk6doLw"
SUDO_USERS = [7901884010]  # List of sudo user IDs
MONGO_URI = "mongodb+srv://shanaya:godfather11@cluster0.t3yd7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "telegram_bot"
COLLECTION_NAME = "links"

# Initialize Pyrogram client
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Initialize MongoDB client
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

# Store temporary data
temp_data = {}

async def create_link(sudo_id, channel_id, message_ids):
    """Generate a unique link for forwarded messages."""
    link_id = f"{sudo_id}_{channel_id}_{int(time.time())}"
    link = f"https://t.me/{(await app.get_me()).username}?start={quote(link_id)}"
    await collection.insert_one({
        "link_id": link_id,
        "sudo_id": sudo_id,
        "channel_id": channel_id,
        "message_ids": message_ids,
        "approved_users": [],
        "used_by": []
    })
    return link

async def get_existing_links(sudo_id):
    """Fetch all links created by a sudo user."""
    links = []
    async for doc in collection.find({"sudo_id": sudo_id}):
        links.append({"link_id": doc["link_id"], "link": f"https://t.me/{(await app.get_me()).username}?start={quote(doc['link_id'])}"})
    return links

async def extract_chat_id_from_link(link):
    """Extract chat ID from a Telegram link (public or private)."""
    # Match public channel: https://t.me/username
    public_match = re.match(r"https://t.me/(\w+)", link)
    if public_match:
        return public_match.group(1)
    
    # Match private channel: https://t.me/c/123456789/...
    private_match = re.match(r"https://t.me/c/(\d+)", link)
    if private_match:
        return f"-100{private_match.group(1)}"
    
    return None

@app.on_message(filters.command("make") & filters.user(SUDO_USERS))
async def make_command(client, message):
    """Handle /make command to show existing links and create new button."""
    sudo_id = message.from_user.id
    existing_links = await get_existing_links(sudo_id)
    
    buttons = [[InlineKeyboardButton("Create New", callback_data="create_new")]]
    if existing_links:
        for link in existing_links:
            buttons.append([InlineKeyboardButton(f"Link: {link['link_id']}", url=link['link'])])
    
    await message.reply("Existing links:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("create_new"))
async def create_new_button(client, callback_query):
    """Handle Create New button click."""
    sudo_id = callback_query.from_user.id
    if sudo_id not in SUDO_USERS:
        await callback_query.answer("Unauthorized", show_alert=True)
        return
    
    temp_data[sudo_id] = {"state": "waiting_for_channel"}
    await callback_query.message.reply(
        "Please provide the channel copy link (e.g., https://t.me/c/123456789/1) or forward messages from the channel. Use /done when finished."
    )

@app.on_message(filters.user(SUDO_USERS) & filters.text & filters.regex(r"https://t.me/"))
async def handle_channel_link(client, message):
    """Handle channel link provided by sudo user."""
    sudo_id = message.from_user.id
    if sudo_id not in temp_data or temp_data[sudo_id]["state"] != "waiting_for_channel":
        return
    
    channel_link = message.text.split()[0]  # Take the first link
    chat_id = await extract_chat_id_from_link(channel_link)
    
    if not chat_id:
        await message.reply("Invalid channel link format. Please provide a valid public (https://t.me/username) or private (https://t.me/c/123456789) link.")
        return
    
    try:
        # Attempt to get chat details
        channel = await client.get_chat(chat_id)
        temp_data[sudo_id]["channel_id"] = channel.id
        temp_data[sudo_id]["state"] = "waiting_for_done"
        await message.reply(
            f"Channel recognized: {channel.title or channel.id}. "
            "Please forward messages or use /done when ready."
        )
    except ChannelInvalid:
        logger.error(f"ChannelInvalid error for chat_id: {chat_id}")
        await message.reply("The channel is invalid or inaccessible. Ensure the bot is a member and has admin rights.")
    except ChannelPrivate:
        logger.error(f"ChannelPrivate error for chat_id: {chat_id}")
        await message.reply("The channel is private and the bot cannot access it. Please make the bot an admin.")
    except PeerIdInvalid:
        logger.error(f"PeerIdInvalid error for chat_id: {chat_id}")
        await message.reply("Invalid chat ID. Please check the link or ensure the bot is in the channel.")
    except Exception as e:
        logger.error(f"Unexpected error processing channel link: {e}")
        await message.reply(f"An error occurred: {str(e)}. Please try again or contact support.")

@app.on_message(filters.user(SUDO_USERS) & filters.forwarded)
async def handle_forwarded_messages(client, message):
    """Handle forwarded messages from sudo user."""
    sudo_id = message.from_user.id
    if sudo_id not in temp_data or temp_data[sudo_id]["state"] not in ["waiting_for_channel", "waiting_for_done"]:
        return
    
    if not message.forward_from_chat:
        await message.reply("This message does not appear to be forwarded from a channel. Please forward a message from the target channel.")
        return
    
    channel_id = message.forward_from_chat.id
    message_id = message.id
    
    if "message_ids" not in temp_data[sudo_id]:
        temp_data[sudo_id]["message_ids"] = []
        temp_data[sudo_id]["channel_id"] = channel_id
    
    temp_data[sudo_id]["message_ids"].append(message_id)
    await message.reply("Message forwarded. Continue forwarding or use /done.")

@app.on_message(filters.command("done") & filters.user(SUDO_USERS))
async def done_command(client, message):
    """Handle /done command to generate link."""
    sudo_id = message.from_user.id
    if sudo_id not in temp_data or "channel_id" not in temp_data[sudo_id]:
        await message.reply("No channel or messages provided.")
        return
    
    channel_id = temp_data[sudo_id]["channel_id"]
    message_ids = temp_data[sudo_id].get("message_ids", [])
    
    if not message_ids:
        await message.reply("No messages forwarded. Please forward messages or provide a channel link.")
        return
    
    # Generate and store link
    link = await create_link(sudo_id, channel_id, message_ids)
    del temp_data[sudo_id]
    
    await message.reply(f"Link created: {link}")

@app.on_message(filters.command("a") & filters.user(SUDO_USERS))
async def approve_command(client, message):
    """Handle /a command to approve a user for a link."""
    sudo_id = message.from_user.id
    try:
        user_id = int(message.command[1])
    except (IndexError, ValueError):
        await message.reply("Usage: /a <UserID>")
        return
    
    existing_links = await get_existing_links(sudo_id)
    if not existing_links:
        await message.reply("No links found.")
        return
    
    buttons = []
    for link in existing_links:
        buttons.append([InlineKeyboardButton(f"Link: {link['link_id']}", callback_data=f"approve_{link['link_id']}_{user_id}")])
    
    await message.reply("Select link to approve:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"approve_(.+)_(\d+)"))
async def approve_link(client, callback_query):
    """Handle approval button click."""
    sudo_id = callback_query.from_user.id
    if sudo_id not in SUDO_USERS:
        await callback_query.answer("Unauthorized", show_alert=True)
        return
    
    link_id, user_id = callback_query.data.split("_")[1], int(callback_query.data.split("_")[2])
    await collection.update_one(
        {"link_id": link_id},
        {"$addToSet": {"approved_users": user_id}}
    )
    await callback_query.message.reply(f"User {user_id} approved for link {link_id}.")
    await callback_query.answer()

@app.on_message(filters.command("start") & filters.regex(r"start (.+)"))
async def start_command(client, message):
    """Handle /start command with link ID."""
    link_id = message.matches[0].group(1)
    user_id = message.from_user.id
    
    link_doc = await collection.find_one({"link_id": link_id})
    if not link_doc:
        await message.reply("Invalid or expired link.")
        return
    
    if user_id not in link_doc["approved_users"]:
        await message.reply("You are not approved to access this content.")
        return
    
    if user_id in link_doc["used_by"]:
        await message.reply("Approval rejected: You have already used this link.")
        return
    
    # Mark link as used
    await collection.update_one(
        {"link_id": link_id},
        {"$addToSet": {"used_by": user_id}}
    )
    
    # Forward messages with flood control
    for msg_id in link_doc["message_ids"]:
        try:
            await client.forward_messages(
                chat_id=user_id,
                from_chat_id=link_doc["channel_id"],
                message_ids=msg_id
            )
            await asyncio.sleep(0.5)  # Flood control
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            await message.reply("Error forwarding some messages.")
            break
    
    await message.reply("All content forwarded successfully.")

# Run the bot
if __name__ == "__main__":
    app.run()

import logging
import warnings
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Suppress warnings
warnings.filterwarnings("ignore")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot start command"""
    await update.message.reply_text(
        "Bot started! Forward any message from a channel, and I'll try to get the channel link and uploader's username."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle forwarded messages"""
    message = update.message
    
    if not message.forward_from_chat:
        await update.message.reply_text("Please forward a message from a channel.")
        return

    # Extract channel information
    chat = message.forward_from_chat
    channel_type = chat.type
    channel_id = chat.id
    channel_title = chat.title or "Unknown Title"
    channel_username = chat.username if chat.username else None
    channel_link = f"https://t.me/{channel_username}" if channel_username else None

    # Initialize response
    response = f"<b>Channel Info</b>\nTitle: {channel_title}\nID: {channel_id}\n"

    # Check if channel is public or private
    if channel_type == "channel":
        if channel_username:
            response += f"Link: {channel_link} (Public)\n"
        else:
            response += "Link: Private Channel\n"
            # Try to generate an invite link if bot has admin permissions
            try:
                invite_link = await context.bot.export_chat_invite_link(chat_id=channel_id)
                response += f"Invite Link: {invite_link}\n"
            except TelegramError as e:
                response += f"Could not generate invite link: {str(e)}\n"

    # Try to get uploader's information
    uploader_info = "Uploader: Not available\n"
    if message.forward_from:
        # If message is forwarded from a user
        user = message.forward_from
        username = user.username if user.username else None
        user_id = user.id
        uploader_info = f"Uploader: {username if username else 'No username'} (ID: {user_id})\n"
    elif message.from_user and not message.from_user.is_bot:
        # If message is directly from the channel, check sender
        user = message.from_user
        username = user.username if user.username else None
        user_id = user.id
        uploader_info = f"Uploader: {username if username else 'No username'} (ID: {user_id})\n"

    response += uploader_info

    # Send response
    await update.message.reply_text(response, parse_mode="HTML")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if update.message:
        await update.message.reply_text(f"An error occurred: {context.error}")

def main():
    """Main function to run the bot"""
    # Your bot token
    BOT_TOKEN = "8145736202:AAEqjJa62tuj40TPaYehFkAJOVJiQk6doLw"

    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

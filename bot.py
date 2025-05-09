from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError

def start(update, context):
    """Bot start command"""
    update.message.reply_text(
        "Bot started! Forward any message from a channel, and I'll try to get the channel link and uploader's username."
    )

def handle_message(update, context):
    """Handle forwarded messages"""
    message = update.message
    
    if not message.forward_from_chat:
        update.message.reply_text("Please forward a message from a channel.")
        return

    # Extract channel information
    chat = message.forward_from_chat
    channel_type = chat.type
    channel_id = chat.id
    channel_title = chat.title or "Unknown Title"
    channel_username = chat.username if chat.username else None
    channel_link = f"https://t.me/{channel_username}" if channel_username else None

    # Initialize response
    response = f"**Channel Info**\nTitle: {channel_title}\nID: {channel_id}\n"

    # Check if channel is public or private
    if channel_type == "channel":
        if channel_username:
            response += f"Link: {channel_link} (Public)\n"
        else:
            response += "Link: Private Channel\n"
            # Try to generate an invite link if bot has admin permissions
            try:
                invite_link = context.bot.export_chat_invite_link(chat_id=channel_id)
                response += f"Invite Link: {invite_link}\n"
            except TelegramError as e:
                response += "Could not generate invite link (Bot needs admin permissions or channel is restricted).\n"

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
    update.message.reply_text(response, parse_mode="Markdown")

def error_handler(update, context):
    """Handle errors"""
    update.message.reply_text(f"An error occurred: {context.error}")

def main():
    """Main function to run the bot"""
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    BOT_TOKEN = "8145736202:AAEqjJa62tuj40TPaYehFkAJOVJiQk6doLw"
    
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.all & ~Filters.command, handle_message))
    dp.add_error_handler(error_handler)

    # Start the bot
    updater.start_polling()
    print("Bot is running...")
    updater.idle()

if __name__ == "__main__":
    main()

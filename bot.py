from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Replace with your bot token from BotFather
BOT_TOKEN = '8145736202:AAEqjJa62tuj40TPaYehFkAJOVJiQk6doLw'

# Function to handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me a Telegram invite link or forward a message from a channel. "
        "I'll extract the channel details and try to generate a join link."
    )

# Function to handle invite links or forwarded messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.text if message.text else None
    forwarded_chat = message.forward_from_chat if message.forward_from_chat else None

    try:
        # Case 1: Handle invite link
        if text and (text.startswith('https://t.me/') or text.startswith('t.me/')):
            await message.reply_text("Processing invite link...")
            try:
                # Fetch chat details from invite link
                chat_info = await context.bot.get_chat(text)
                chat_id = chat_info.id
                chat_type = chat_info.type
                chat_title = chat_info.title
                username = chat_info.username

                # Prepare response
                response = f"Chat Info:\nID: {chat_id}\nType: {chat_type}\nTitle: {chat_title}\n"
                
                if username:
                    normal_link = f"t.me/{username.lstrip('@')}"
                    response += f"Normal Link: {normal_link}"
                else:
                    response += "This is a private channel/group. No public username available.\n"
                    
                    # Try to generate invite link if bot is admin
                    try:
                        invite_link = await context.bot.export_chat_invite_link(chat_id)
                        response += f"Generated Invite Link: {invite_link}"
                    except TelegramError as e:
                        response += f"Cannot generate invite link: {str(e)} (Bot may not be admin)"

                await message.reply_text(response)
            
            except TelegramError as e:
                await message.reply_text(
                    f"Error processing link: {str(e)}\n"
                    "Possible reasons:\n"
                    "- Invalid link.\n"
                    "- Bot doesn't have access to the channel.\n"
                    "- Channel is private and restricted."
                )

        # Case 2: Handle forwarded message
        elif forwarded_chat:
            await message.reply_text("Processing forwarded message...")
            chat_id = forwarded_chat.id
            chat_type = forwarded_chat.type
            chat_title = forwarded_chat.title
            username = forwarded_chat.username

            # Prepare response
            response = f"Chat Info:\nID: {chat_id}\nType: {chat_type}\nTitle: {chat_title}\n"
            
            if username:
                normal_link = f"t.me/{username.lstrip('@')}"
                response += f"Normal Link: {normal_link}"
            else:
                response += "This is a private channel/group. No public username available.\n"
                
                # Try to generate invite link if bot is admin
                try:
                    invite_link = await context.bot.export_chat_invite_link(chat_id)
                    response += f"Generated Invite Link: {invite_link}"
                except TelegramError as e:
                    response += f"Cannot generate invite link: {str(e)} (Bot may not be admin)"

            await message.reply_text(response)

        else:
            await message.reply_text(
                "Please send a valid Telegram invite link or forward a message from a channel."
            )

    except Exception as e:
        await message.reply_text(f"Unexpected error: {str(e)}")

# Main function to set up the bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.FORWARDED, handle_message))

    # Start the bot
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()

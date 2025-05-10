import telebot

API_TOKEN = '8145736202:AAEqjJa62tuj40TPaYehFkAJOVJiQk6doLw'
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(content_types=['video'])
def handle_video(message):
    if message.video:
        file_id = message.video.thumb.file_id  # Thumbnail file ID
        file_info = bot.get_file(file_id)
        
        thumbnail_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_info.file_path}"
        bot.send_message(message.chat.id, f"📷 **Thumbnail Link:** {thumbnail_url}")

bot.polling()

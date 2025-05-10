import telebot

API_TOKEN = '8145736202:AAEqjJa62tuj40TPaYehFkAJOVJiQk6doLw'
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(content_types=['video'])
def handle_video(message):
    file_id = message.video.file_id  # Video file ID
    thumb_id = message.video.thumb.file_id if message.video.thumb else None  # Thumbnail file ID

    file_info = bot.get_file(file_id)
    video_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_info.file_path}"

    if thumb_id:
        thumb_info = bot.get_file(thumb_id)
        thumbnail_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{thumb_info.file_path}"
    else:
        thumbnail_url = "Thumbnail not available"

    bot.send_message(message.chat.id, f"📹 **Video Link:** {video_url}\n🖼 **Thumbnail Link:** {thumbnail_url}")

bot.polling()

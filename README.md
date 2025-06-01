# Telegram Unzipper Bot

A powerful Telegram bot to extract and send back files from zip, tar, 7z, and rar archives. Built with Pyrogram, supports large files (up to 2GB), and sends extracted media in the best format (video, audio, document).

---

## Features
- Extracts **zip**, **tar**, **7z**, and **rar** archives
- Handles large files (up to 2GB)
- Sends extracted files as video, audio, or document based on file type
- Tracks usage statistics and server info
- Simple, fast, and secure

---

## Commands
- `/start` — Welcome message
- `/help` — Usage information
- `/status` — Show server info (OS, CPU, RAM, Disk)
- `/info` — Show bot usage stats (archives extracted, files extracted, total size, users)

---

## Usage
1. **Send an archive** (zip, tar, 7z, rar) to the bot
2. The bot will reply with a confirmation and an **EXTRACT** button
3. Click **EXTRACT**
4. The bot will extract and send all files back to you in the best format

---

## Installation (VPS)

1. **Clone the repo**
   ```bash
   git clone <your-repo-url>
   cd unziptg
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Get your Telegram API credentials**
   - Go to https://my.telegram.org
   - Create an app to get `API_ID` and `API_HASH`
   - Set your `BOT_TOKEN` from BotFather
4. **Edit `app.py`**
   - Fill in your `API_ID`, `API_HASH`, and `BOT_TOKEN`
5. **Run the bot**
   ```bash
   python3 app.py
   ```

---

## Requirements
- Python 3.10+
- pip
- Telegram API credentials (API_ID, API_HASH, BOT_TOKEN)

---

## License
MIT License

---

**Author:** AMI
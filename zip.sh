#!/bin/bash

echo "Starting full setup for the ZIP Upload Telegram Bot..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv ffmpeg unzip zip libgl1 libsm6 libxext6 libxrender-dev

# Create and activate virtual environment
echo "Creating virtual environment..."
python3 -m venv zipbot_env
source zipbot_env/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python libraries
echo "Installing required Python packages..."
pip install pyrogram tgcrypto moviepy pillow

# Create folders if not exist
mkdir -p downloads extracted

# Create dummy JSON state file if missing
if [ ! -f bot_state.json ]; then
  echo '{"downloads": []}' > bot_state.json
  echo "Created default bot_state.json"
fi

echo "Setup complete!"
echo "To start the bot, run: source zipbot_env/bin/activate && python3 your_bot_script.py"

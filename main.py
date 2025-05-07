from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import asyncio
import threading
import re

# Flask app for Koyeb health checks
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Bot credentials
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
BOT_TOKEN = "7073579407:AAG-5z0cmNFYdNlUdlJQY72F8lTmDXmXy2I"

# Channels to monitor (with @ prefix)
CHANNELS = ["@stree2chaava2", "@chaava2025"]

# In-memory movie database
movie_db = {}

# Create bot client
bot = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Extract movie title from message text
def extract_title(text):
    match = re.search(r"🎬\s*Title\s*:\s*(.+?)(\n|$)", text, re.IGNORECASE)
    return match.group(1).strip().lower() if match else None

# Start command
@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hi! Send me a movie name and I'll find the link from the channels.")

# Movie search
@bot.on_message(filters.text & ~filters.command(["start"]))
async def search_movie(client, message: Message):
    query = message.text.lower()
    results = []
    for title, (channel, msg_id) in movie_db.items():
        if query in title:
            results.append(f"https://t.me/{channel.strip('@')}/{msg_id}")
    if results:
        await message.reply_text("Here are the matching movies:\n" + "\n".join(results))
    else:
        await message.reply_text("Sorry, no movie found.")

# Auto update on new posts (text or caption)
@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = message.text or message.caption
    if text and f"@{message.chat.username}" in CHANNELS:
        title = extract_title(text)
        if title:
            movie_db[title] = (f"@{message.chat.username}", message.message_id)
            print(f"Added: {title} -> @{message.chat.username}/{message.message_id}")
        else:
            print("No title found in post.")
    else:
        print("Message ignored (not from allowed channels or no text).")

# Run the bot in a thread
def run_bot():
    asyncio.run(start_bot())

async def start_bot():
    await bot.start()
    print("Bot is running.")
    await asyncio.Event().wait()

# Start everything
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8000)

from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import asyncio
import threading
import re

# Flask app for Koyeb health check
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"

# Bot credentials
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
BOT_TOKEN = "7073579407:AAG-5z0cmNFYdNlUdlJQY72F8lTmDXmXy2I"

# Channels to monitor (without @ for matching)
CHANNELS = ["stree2chaava2", "chaava2025"]

# Movie database
movie_db = {}

# Create bot client
bot = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Extract movie title from message
def extract_title(text):
    match = re.search(r"(?i)title\s*:\s*(.+?)(\n|$)", text)
    return match.group(1).strip().lower() if match else None

# /start command
@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hi! Send me a movie name and I'll find the link from the channels.")

# Search command
@bot.on_message(filters.text & ~filters.command(["start"]))
async def search_movie(client, message: Message):
    query = message.text.lower()
    results = []
    for title, (channel, msg_id) in movie_db.items():
        if query in title:
            results.append(f"https://t.me/{channel}/{msg_id}")
    if results:
        await message.reply_text("Matching results:\n" + "\n".join(results))
    else:
        await message.reply_text("Sorry, no movie found.")

# Monitor new posts in channels
@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = message.text or message.caption
    if text and message.chat.username in CHANNELS:
        title = extract_title(text)
        if title:
            movie_db[title] = (message.chat.username, message.message_id)
            print(f"Added to DB: {title} -> {message.chat.username}/{message.message_id}")
        else:
            print("No title found.")
    else:
        print("Ignored message.")

# Run bot in thread
def run_bot():
    bot.run()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8000)

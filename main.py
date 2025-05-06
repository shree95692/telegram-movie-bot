from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import asyncio
import threading

# Flask app for Koyeb health checks
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Bot credentials
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
BOT_TOKEN = "7073579407:AAE0ZnyAMKG1rtkYxMWwHwKOHtEBRQmsU3k"

# Channels to monitor
CHANNELS = ["stree2chaava2", "chaava2025"]

# In-memory movie database
movie_db = {}

# Create bot client
bot = Client("movie_search_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Update DB from all channels
async def update_db():
    global movie_db
    movie_db = {}
    for channel in CHANNELS:
        async for message in bot.iter_history(channel):
            if message.text:
                movie_db[message.text.lower()] = (channel, message.message_id)

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
            results.append(f"https://t.me/{channel}/{msg_id}")
    if results:
        await message.reply_text("Here are the matching movies:\n" + "\n".join(results))
    else:
        await message.reply_text("Sorry, no movie found.")

# Auto update on new posts
@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    if message.chat.username in CHANNELS and message.text:
        movie_db[message.text.lower()] = (message.chat.username, message.message_id)

# Manual refresh
@bot.on_message(filters.command("refresh"))
async def manual_refresh(client, message: Message):
    await update_db()
    await message.reply_text("Movie database refreshed.")

# Run the bot in a thread
def run_bot():
    asyncio.run(start_bot())

async def start_bot():
    await bot.start()
    await update_db()
    print("Bot is running.")
    await asyncio.Event().wait()

# Start everything
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8000)

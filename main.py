from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import asyncio
import threading
import re

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
BOT_TOKEN = "7073579407:AAG-5z0cmNFYdNlUdlJQY72F8lTmDXmXy2I"
CHANNELS = ["@stree2chaava2", "@chaava2025"]
movie_db = {}

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def extract_title(text):
    # Search entire text for "🎬 Title : Movie Name"
    match = re.search(r"🎬\s*Title\s*:\s*(.+)", text, re.IGNORECASE)
    if match:
        title_line = match.group(1).strip()
        title = title_line.split('\n')[0].strip().lower()
        return title
    return None

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hi! Send me a movie name and I'll find it for you.")

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

@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = message.text or message.caption
    if text and f"@{message.chat.username}" in CHANNELS:
        title = extract_title(text)
        if title:
            movie_db[title] = (f"@{message.chat.username}", message.message_id)
            print(f"Added: {title} -> {message.chat.username}/{message.message_id}")
        else:
            print("No title found.")
    else:
        print("Message skipped (no text or not from monitored channels)")

def run_bot():
    asyncio.run(start_bot())

async def start_bot():
    await bot.start()
    print("Bot is running.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8000)

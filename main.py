import json
import re
import os
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import time

# Telegram credentials
api_id = 25424751
api_hash = "a9f8c974b0ac2e8b5fce86b32567af6b"
session_string = "BQGD828AMUcvjUw-OoeEq9vsJglHO8FPUWRDh8MGHxV5wwvSLlpwC0_lve3qdVK-7b_0mGsKD87_-6eIS-vqD5prMNL7GjosptVTESutY3kSY3E3MYl9bq8A26SUVutyBze6xDjZP_vY_uRkXjTvEe9yu3EkGgVbndao4HAhkznY_8QIseapTYs6f8AwGXk_LkOOplSE-RJR-IuOlB3WKoaPehYOSjDRhiiKVAmt9fwzTDq1cDntoOcV6EBrzBVia1TQClWX1jPaZmNQQZ96C8mpvjMfWnFVRlM8pjmI9CPbfoNNB2tO4kuEDr2BRBdlB244CC83wV80IYO66pZ5yI7IWC7FqwAAAAEzyxzAAA"

client = Client(name="moviebot", api_id=api_id, api_hash=api_hash, session_string=session_string)

# Config
SOURCE_CHANNELS = ["stree2chaava2", "chaava2025"]
FORWARD_CHANNEL_ID = -1002512169097
ALERT_CHANNEL_ID = -1002661392627
OWNER_ID = 5163916480
DB_FILE = "movies.json"

# Load or initialize database
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        movie_db = json.load(f)
else:
    movie_db = {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(movie_db, f, indent=2)

def extract_title(text: str) -> str:
    try:
        title_match = re.search(r"[Tt]itle\s*[:\-–]*\s*(.+)", text)
        if title_match:
            title = title_match.group(1).strip().split('\n')[0]
            return title.lower()
        else:
            alt = re.findall(r"(?i)^(.+?)(?:\s*\|\s*|$|\n)", text.strip())
            return alt[0].strip().lower() if alt else None
    except:
        return None

async def process_message(msg: Message, channel_username: str):
    if not msg.text and not msg.caption:
        return
    text = msg.text or msg.caption
    title = extract_title(text)
    if not title:
        await client.send_message(ALERT_CHANNEL_ID, f"❗ Title extract fail in @{channel_username}/{msg.id}")
        return
    movie_db[title] = f"https://t.me/{channel_username}/{msg.id}"
    save_db()
    await client.send_message(FORWARD_CHANNEL_ID, f"✅ Saved: {title}\n🔗 {movie_db[title]}")

@client.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Hello! Movie bot ready hai. Kisi bhi movie ka naam bhejo.")

@client.on_message(filters.command("uploaded"))
async def uploaded(client, message):
    if not movie_db:
        await message.reply("Koi movie abhi tak upload nahi hui.")
    else:
        titles = "\n".join([f"- {title}" for title in list(movie_db.keys())[:100]])
        await message.reply(f"✅ Uploaded Movies:\n\n{titles}")

@client.on_message(filters.text & ~filters.private)
async def search_movie(client, message):
    query = message.text.strip().lower()
    result = None
    for title in movie_db:
        if query in title:
            result = movie_db[title]
            break
    if result:
        await message.reply(f"🎬 Movie Found:\n🔗 {result}")
    else:
        await message.reply("❌ Movie nahi mili!\n\n🕵️ Request receive ho gaya hai, 5-6 ghante mein upload ho jayegi.")
        await client.send_message(ALERT_CHANNEL_ID, f"❗ Movie not found: {query}\nFrom: {message.from_user.id}")

async def scan_all_old_posts():
    for channel in SOURCE_CHANNELS:
        try:
            async for msg in client.iter_history(channel):
                await process_message(msg, channel)
        except FloodWait as e:
            await asyncio.sleep(e.value)

@client.on_message(filters.chat(SOURCE_CHANNELS))
async def new_post_handler(client, message):
    await process_message(message, message.chat.username)

# Flask for healthcheck (Koyeb)
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Bot is running!", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

def start():
    Thread(target=run_flask).start()
    client.run()

if __name__ == "__main__":
    start()

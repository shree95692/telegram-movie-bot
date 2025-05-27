import os
import re
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread

# ---------------- CONFIG ----------------
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "1BV-YeLQmdFbhzT3WLO...aapka_actual_session_string..."  # Replace with your session string
CHANNEL_IDS = [-1002397054969, -1002526458211]  # Public and Private movie channels
ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
DB_FILE = "movie_db.json"
# ----------------------------------------

# Flask healthcheck
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is Alive"

def run_flask():
    app.run(host="0.0.0.0", port=8000)

Thread(target=run_flask).start()

# Load movie DB
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        movie_db = json.load(f)
else:
    movie_db = {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(movie_db, f, indent=2)

# Title extraction
def extract_title(text):
    patterns = [
        r"(?i)Title\s*[:\-]*\s*(.+)",
        r"(?i)Movie\s*Name\s*[:\-]*\s*(.+)",
        r"(?i)🎬\s*Title\s*[:\-]*\s*(.+)",
        r"(?i)^(.+)\s+\d{4}",
        r"(?i)^(.+)\s+(\d{4})",
        r"(?i)^(.+)$"
    ]
    for pattern in patterns:
        match = re.search(pattern, text.strip())
        if match:
            return match.group(1).strip()
    return None

# Pyrogram Client using session string
app_client = Client(
    name="movie_bot",
    session_string=SESSION_STRING,
    api_id=API_ID,
    api_hash=API_HASH
)

@app_client.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    await message.reply("Send me a movie name and I'll find it for you.")

@app_client.on_message(filters.command("check_movies") & filters.private)
async def check_movies(client, message: Message):
    if not movie_db:
        await message.reply("Database is empty.")
        return
    movies = "\n".join(sorted(movie_db.keys()))
    await message.reply_text(f"**Uploaded Movies:**\n\n{movies[:4000]}")

@app_client.on_message(filters.text & filters.private)
async def search_movie(client, message: Message):
    query = message.text.lower()
    for title, link in movie_db.items():
        if query in title.lower():
            await message.reply_text(f"**Found:** [{title}]({link})", disable_web_page_preview=True)
            return
    await message.reply_text("Movie not found. Upload will be done in 5–6 hours.")
    await client.send_message(ALERT_CHANNEL_ID, f"❌ Movie not found: `{query}`")

@app_client.on_message(filters.channel)
async def process_new_post(client, message: Message):
    if message.chat.id not in CHANNEL_IDS:
        return
    if not message.text:
        return

    title = extract_title(message.text)
    if not title:
        await client.send_message(ALERT_CHANNEL_ID, f"⚠️ Failed to extract title from post {message.id} in `{message.chat.id}`")
        return

    link = f"https://t.me/{message.chat.username or (await client.get_chat(message.chat.id)).username}/{message.id}"
    movie_db[title] = link
    save_db()
    await client.forward_messages(FORWARD_CHANNEL_ID, message.chat.id, message.id)

async def scan_old_posts():
    for channel_id in CHANNEL_IDS:
        async for message in app_client.iter_history(channel_id, reverse=True):
            if not message.text:
                continue
            title = extract_title(message.text)
            if title and title not in movie_db:
                link = f"https://t.me/{message.chat.username or (await app_client.get_chat(channel_id)).username}/{message.id}"
                movie_db[title] = link
    save_db()

async def main():
    await app_client.start()
    await scan_old_posts()
    print("Bot started!")
    await asyncio.get_event_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())

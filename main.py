import re
import json
import logging
from telethon import TelegramClient, events
from dotenv import load_dotenv
import os

# Load .env file if available
load_dotenv()

# Bot details
API_ID = 25424751
API_HASH = 'a9f8c974b0ac2e8b5fce86b32567af6b'
BOT_TOKEN = '7073579407:AAHk8xHQGaKv7xpvxgFq5_UGISwLl7NkaDM'
ADMIN_IDS = [5163916480]
ALERT_CHANNEL = 'alertchannel00'

# Channel list
SOURCE_CHANNELS = ['stree2chaava2', 'chaava2025']

# DB file
DB_FILE = 'db.json'

# Load or initialize DB
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w') as f:
        json.dump([], f)

with open(DB_FILE, 'r') as f:
    MOVIE_DB = json.load(f)

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump(MOVIE_DB, f)

def extract_movie_name(text):
    patterns = [
        r"🎬\s*Title\s*[:-]\s*(.+)",
        r"\*\*❇️\*\*\*+\s*𝐓𝐈𝐓𝐋𝐄\s*[:-]\s*(.+?)\*\*",
        r"🎬\s*(.+?)\n",
        r"Movie name hai\s+(.+?)\s+and"
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    lines = text.splitlines()
    for line in lines:
        if len(line.strip()) >= 4 and len(line.strip()) <= 60:
            return line.strip()
    return None

client = TelegramClient('my', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def add_movie(name, link):
    entry = {"name": name.lower(), "link": link}
    is_duplicate = any(x["name"] == name.lower() for x in MOVIE_DB)
    MOVIE_DB.append(entry)
    save_db()
    if is_duplicate:
        client.send_message(ALERT_CHANNEL, f"⚠️ Duplicate Movie: {name} already exists. Added again.")
    else:
        print(f"✅ New movie added: {name}")

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    movie_name = extract_movie_name(event.raw_text)
    if movie_name:
        add_movie(movie_name, event.message.link)
    else:
        await client.send_message(ALERT_CHANNEL, f"❌ Failed to extract movie name from:\n{event.message.link}")

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        "👋 Welcome to Movie Request Bot!\n\n"
        "🎞️ Send any movie name to search.\n"
        "📥 If not found, it'll be uploaded in 5–6 hours.\n"
        "🧾 Use /upload_db to get current movie list (admin only).\n"
        "📋 Use /uploaded_movies to check all uploaded movies.\n\n"
        "✅ Bot is online."
    )

@client.on(events.NewMessage(pattern='/upload_db'))
async def upload_db(event):
    if event.sender_id in ADMIN_IDS:
        with open(DB_FILE, 'r') as f:
            await event.respond(file=f, message="📁 Here's the movie database file.")
    else:
        await event.reply("❌ You are not authorized.")

@client.on(events.NewMessage(pattern='/uploaded_movies'))
async def uploaded_movies(event):
    names = [x["name"].title() for x in MOVIE_DB]
    chunk = "\n".join(names[-50:])
    await event.reply(f"🎬 Last 50 uploaded movies:\n\n{chunk}")

@client.on(events.NewMessage)
async def search_movie(event):
    if event.text.startswith('/'):
        return
    name = event.text.lower()
    match = next((x for x in MOVIE_DB if name in x['name']), None)
    if match:
        await event.reply(f"🎬 Found: [{match['name'].title()}]({match['link']})", link_preview=False)
    else:
        await event.reply(
            "❌ Movie Not Found\n\n"
            "Your request has been received.\n"
            "It'll be uploaded in 5–6 hours. Stay tuned!"
        )

print("Bot is running...")
client.run_until_disconnected()

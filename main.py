import os
import re
import json
import asyncio
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageIdInvalid
from flask import Flask

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_FILE = "movie_bot.session"

CHANNELS = ["stree2chaava2", "chaava2025"]
ALERT_CHANNEL = -1002661392627
FORWARD_CHANNEL = -1002512169097
DB_FILE = "movie_db.json"
GITHUB_REPO = "shree95692/movie-db-backup"

app = Flask(__name__)
bot = Client(SESSION_FILE, api_id=API_ID, api_hash=API_HASH)

db = {}

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    try:
        requests.put(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_FILE}",
            headers={
                "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={
                "message": "Backup movie DB",
                "content": requests.utils.quote(open(DB_FILE, "rb").read().decode("utf-8").encode("base64")),
                "sha": get_github_file_sha()
            }
        )
    except Exception as e:
        print("GitHub backup failed:", e)

def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)

def extract_title(text):
    lines = text.splitlines()
    for line in lines:
        if "title" in line.lower():
            cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", line.split(":")[-1]).strip().lower()
            if cleaned:
                return cleaned
    return None

async def process_post(channel, message):
    try:
        title = extract_title(message.text or "")
        if not title:
            await bot.send_message(ALERT_CHANNEL, f"❗ Unrecognized format:\nhttps://t.me/{channel}/{message.id}")
            return
        db[title] = f"https://t.me/{channel}/{message.id}"
        save_db()
    except Exception as e:
        await bot.send_message(ALERT_CHANNEL, f"❌ Error processing post {message.id}: {e}")

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(_, msg: Message):
    await msg.reply("Welcome to Movie Bot! Send a movie name to search.")

@bot.on_message(filters.private & ~filters.command("start"))
async def search_movie(_, msg: Message):
    text = msg.text.strip().lower()
    if text == "uploaded":
        if db:
            uploaded = "\n".join([f"• {k.title()}" for k in list(db.keys())[:50]])
            await msg.reply(f"✅ Uploaded Movies:\n\n{uploaded}")
        else:
            await msg.reply("No movies uploaded yet.")
        return

    link = db.get(text)
    if link:
        await msg.reply(f"🎬 Movie Found:\n{link}")
    else:
        await msg.reply("Movie not found. Upload in 5–6 hrs.")
        await bot.send_message(ALERT_CHANNEL, f"❓ Not found: `{text}`")

@bot.on_message(filters.channel)
async def auto_update(client, message: Message):
    if message.chat.username in CHANNELS:
        await process_post(message.chat.username, message)

@app.route("/")
def home():
    return "Bot Running"

async def update_all_old_posts():
    for channel in CHANNELS:
        async for msg in bot.get_chat_history(channel, limit=1000):
            await process_post(channel, msg)

async def main():
    load_db()
    await bot.start()
    await update_all_old_posts()
    print("Bot Started.")
    await asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8000)).start()
    asyncio.run(main())

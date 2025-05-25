import os
import re
import json
import asyncio
import logging
from datetime import datetime
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from git import Repo
import threading

# ==================== CONFIG ====================
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_NAME = "my_session"
CHANNELS = ["stree2chaava2", "chaava2025"]
ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
OWNER_ID = 5163916480
DB_FILE = "database.json"
GITHUB_REPO = "shree95692/movie-db-backup"
# ===============================================

app = Flask(__name__)
bot = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

movie_db = {}
logging.basicConfig(level=logging.INFO)

# ========== Utility Functions ==========
def load_db():
    global movie_db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            movie_db = json.load(f)
    else:
        movie_db = {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(movie_db, f, indent=2)

def extract_title(text):
    match = re.search(r"(?i)(?:title\s*[:\-]?\s*|\ud83c\udfac\s*)?([\w\s\-]+)", text)
    if match:
        return match.group(1).strip().lower()
    return None

async def backup_to_github():
    try:
        if not os.path.exists(".git"):
            Repo.init(".")
            repo = Repo(".")
            repo.create_remote("origin", f"https://github.com/{GITHUB_REPO}.git")
        repo = Repo(".")
        repo.git.add(DB_FILE)
        repo.index.commit(f"Backup on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        repo.remote().push("origin", "main")
    except Exception as e:
        logging.error(f"GITHUB BACKUP FAILED: {e}")

async def process_message(message: Message):
    if not message.text:
        return
    title = extract_title(message.text)
    if title:
        movie_db[title] = f"https://t.me/{message.chat.username}/{message.message_id}"
        save_db()
        await bot.forward_messages(FORWARD_CHANNEL_ID, message.chat.id, message.message_id)
        await backup_to_github()
    else:
        await bot.send_message(ALERT_CHANNEL_ID, f"\u2757 Title not found in post: https://t.me/{message.chat.username}/{message.message_id}")

# ========== Handlers ==========
@bot.on_message(filters.private & filters.text)
async def search_handler(client, message):
    query = message.text.strip().lower()
    if query in movie_db:
        await message.reply(f"\u2705 Movie Found:\n{movie_db[query]}")
    else:
        await message.reply("\u274C Movie not found.\n\nYour request has been received. We will upload this movie in 5–6 hours.")
        await bot.send_message(ALERT_CHANNEL_ID, f"\u274C Movie not found: {query} (requested by {message.from_user.id})")

@bot.on_message(filters.command("update") & filters.user(OWNER_ID))
async def manual_update(client, message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return await message.reply("Usage: /update <post_id>")
        post_id = int(parts[1])
        for ch in CHANNELS:
            try:
                msg = await bot.get_messages(ch, post_id)
                await process_message(msg)
                return await message.reply("\u2705 Post updated manually.")
            except:
                continue
        await message.reply("\u274C Failed to fetch post.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@bot.on_message(filters.command("add") & filters.user(OWNER_ID))
async def manual_add(client, message):
    try:
        parts = message.text.split(None, 2)
        if len(parts) != 3:
            return await message.reply("Usage: /add <title> <link>")
        title, link = parts[1].lower(), parts[2]
        movie_db[title] = link
        save_db()
        await backup_to_github()
        await message.reply(f"\u2705 Added manually: {title}\n{link}")
    except Exception as e:
        await message.reply(f"Error: {e}")

@bot.on_message(filters.command("uploaded") & filters.user(OWNER_ID))
async def uploaded_list(client, message):
    if not movie_db:
        return await message.reply("No movies found in database.")
    movies = "\n".join([f"\u2022 {title}" for title in movie_db.keys()])
    await message.reply(f"\ud83c\udfac Uploaded Movies ({len(movie_db)}):\n\n{movies[:4000]}")

@bot.on_message(filters.channel & filters.chat(CHANNELS))
async def channel_post_handler(client, message):
    await process_message(message)

# ========== Old Posts Update ==========
async def scan_old_posts():
    logging.info("\ud83d\udd00 Scanning old posts...")
    for ch in CHANNELS:
        try:
            async for msg in bot.get_chat_history(ch, limit=1000):
                await process_message(msg)
        except Exception as e:
            logging.error(f"Failed reading from {ch}: {e}")
    logging.info("\u2705 Old post scan complete.")

# ========== Flask Ping (Koyeb) ==========
@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080, use_reloader=False)

# ========== Start Everything ==========
async def main():
    await bot.start()
    load_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(backup_to_github, "interval", hours=3)
    scheduler.start()
    asyncio.create_task(scan_old_posts())
    threading.Thread(target=run_flask).start()
    print("\u2705 Bot running...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

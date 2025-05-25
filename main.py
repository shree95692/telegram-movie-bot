import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from git import Repo
import json
import re
from datetime import datetime

# Session-based login
SESSION_STRING = "BQGD828AMUcvjUw-OoeEq9vsJglHO8FPUWRDh8MGHxV5wwvSLlpwC0_lve3qdVK-7b_0mGsKD87_-6eIS-vqD5prMNL7GjosptVTESutY3kSY3E3MYl9bq8A26SUVutyBze6xDjZP_vY_uRkXjTvEe9yu3EkGgVbndao4HAhkznY_8QIseapTYs6f8AwGXk_LkOOplSE-RJR-IuOlB3WKoaPehYOSjDRhiiKVAmt9fwzTDq1cDntoOcV6EBrzBVia1TQClWX1jPaZmNQQZ96C8mpvjMfWnFVRlM8pjmI9CPbfoNNB2tO4kuEDr2BRBdlB244CC83wV80IYO66pZ5yI7IWC7FqwAAAAEzyxzAAA"

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
CHANNELS = ["stree2chaava2", "chaava2025"]
OWNER_ID = 5163916480
GIT_REPO = "https://github.com/shree95692/movie-db-backup.git"
DB_FILE = "movie_db.json"

bot = Client("movie_bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)

movie_db = {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(movie_db, f, indent=2)

def load_db():
    global movie_db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            movie_db = json.load(f)

def extract_title(text):
    patterns = [
        r"Title\s*[:\-]?\s*(.+)",
        r"Movie\s*[:\-]?\s*(.+)",
        r"🎬\s*(.+)",
        r"^(.+)\s+\d{4}",  # Title (2023)
        r"^(.+)\s+v",      # Title (v)
        r"^(.+)$"              # fallback
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            title = match.group(1).strip().split("\n")[0]
            return title.lower()
    return None

async def backup_to_github():
    if not os.path.exists(".git"):
        Repo.clone_from(GIT_REPO, ".")
    repo = Repo(".")
    repo.git.add(DB_FILE)
    repo.index.commit(f"Backup: {datetime.now()}")
    origin = repo.remote(name='origin')
    origin.push()

async def scan_old_posts():
    for channel in CHANNELS:
        async for msg in bot.iter_history(channel, limit=1000):
            if not msg.text:
                continue
            title = extract_title(msg.text)
            if not title:
                await bot.send_message(ALERT_CHANNEL_ID, f"❌ Title not found in post:\nhttps://t.me/{channel}/{msg.id}")
                continue
            movie_db[title] = f"https://t.me/{channel}/{msg.id}"
    save_db()
    await backup_to_github()

@bot.on_message(filters.chat(CHANNELS) & filters.text)
async def handle_new_post(_, msg: Message):
    title = extract_title(msg.text)
    if not title:
        await bot.send_message(ALERT_CHANNEL_ID, f"❌ Title not found in post:\nhttps://t.me/{msg.chat.username}/{msg.id}")
        return
    movie_db[title] = f"https://t.me/{msg.chat.username}/{msg.id}"
    save_db()
    await backup_to_github()
    await bot.send_message(FORWARD_CHANNEL_ID, f"✅ New movie added: **{title.title()}**")

@bot.on_message(filters.private & filters.text)
async def handle_search(_, msg: Message):
    query = msg.text.lower().strip()
    if query in movie_db:
        await msg.reply(f"🎬 Movie Found:\n{movie_db[query]}")
    else:
        await msg.reply(
            "❌ Movie not found.\n\n**Your request is noted. It will be uploaded in 5–6 hours.**"
        )
        await bot.send_message(ALERT_CHANNEL_ID, f"❗ Movie not found: **{query}** requested by [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})")

@bot.on_message(filters.command("uploaded") & filters.user(OWNER_ID))
async def show_uploaded(_, msg: Message):
    if movie_db:
        text = "\n".join([f"• {k.title()}" for k in sorted(movie_db.keys())])
        await msg.reply(f"🎬 Uploaded Movies:\n\n{text}")
    else:
        await msg.reply("No movies in the database yet.")

async def main():
    await bot.start()
    load_db()
    await scan_old_posts()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(save_db, "interval", minutes=10)
    scheduler.add_job(backup_to_github, "interval", hours=1)
    scheduler.start()

    print("Bot is running...")
    await idle()

from pyrogram.idle import idle

if __name__ == "__main__":
    asyncio.run(main())

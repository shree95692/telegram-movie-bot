
import asyncio
import json
import os
import re
import threading
from datetime import datetime

from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message
from github import Github
from difflib import SequenceMatcher

# ===== CONFIGURATION =====
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_NAME = "movie_bot_session"
CHANNELS = ["stree2chaava2", "chaava2025"]
ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "shree95692/movie-db-backup"
FILE_NAME = "movies.json"
OWNER_ID = 5163916480
# ==========================

app = Flask(__name__)
bot = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)
movie_db = {}

# ===== Smart Title Extractor =====
def extract_title(text):
    patterns = [
        r"🎬 *Title *: *(.+)",
        r"Title *: *(.+)",
        r"Movie *: *(.+)",
        r"Name *: *(.+)",
        r"(.+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            title = match.group(1).strip().lower()
            title = re.sub(r"[^\w\s]", "", title)
            return title
    return None

# ===== GitHub Sync =====
def upload_to_github():
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        content = json.dumps(movie_db, indent=2)
        try:
            file = repo.get_contents(FILE_NAME)
            repo.update_file(FILE_NAME, f"Update {datetime.now()}", content, file.sha)
        except:
            repo.create_file(FILE_NAME, f"Create {datetime.now()}", content)
    except Exception as e:
        print("GitHub upload error:", e)

# ===== Movie Search =====
@bot.on_message(filters.private & filters.text)
async def search_movie(client, message: Message):
    query = message.text.lower().strip()
    query = re.sub(r"[^\w\s]", "", query)

    results = []
    for title, link in movie_db.items():
        if query in title:
            results.append(link)

    if results:
        await message.reply_text(f"**Movie Found:** [Watch Now]({results[0]})", disable_web_page_preview=True)
    else:
        await message.reply_text("**Movie not found.** Your request has been received and will be uploaded within 5–6 hours.")
        await bot.send_message(ALERT_CHANNEL_ID, f"❌ Movie not found: `{query}` by {message.from_user.mention}")

# ===== Channel Scanner =====
async def scan_channels():
    print("Scanning channels...")
    found_titles = set()
    for channel in CHANNELS:
        async for msg in bot.get_chat_history(channel, limit=500):
            if msg.text:
                title = extract_title(msg.text)
                link = f"https://t.me/{channel}/{msg.message_id}"

                if title:
                    if title in movie_db and movie_db[title] != link:
                        await bot.send_message(ALERT_CHANNEL_ID, f"⚠️ Duplicate title detected: `{title}`\n{link}")
{link}")
                    movie_db[title] = link
                    found_titles.add(title)
                else:
                    await bot.send_message(ALERT_CHANNEL_ID, f"❌ Unrecognized post:
{link}")
                    await bot.forward_messages(ALERT_CHANNEL_ID, channel, msg.message_id)
    # Delete entries if message was deleted from Telegram
    to_delete = [t for t in movie_db if t not in found_titles]
    for t in to_delete:
        del movie_db[t]
    upload_to_github()

# ===== New Message Handler =====
@bot.on_message(filters.channel & filters.chat(CHANNELS))
async def handle_new_message(client, message: Message):
    if message.text:
        title = extract_title(message.text)
        link = f"https://t.me/{message.chat.username}/{message.message_id}"

        if title:
            if title in movie_db and movie_db[title] != link:
                await bot.send_message(ALERT_CHANNEL_ID, f"⚠️ Duplicate title in new post: `{title}`
{link}")
            movie_db[title] = link
            upload_to_github()
        else:
            await bot.send_message(ALERT_CHANNEL_ID, f"❌ New post unrecognized:
{link}")
            await bot.forward_messages(ALERT_CHANNEL_ID, message.chat.id, message.message_id)

# ===== Manual Scan Command =====
@bot.on_message(filters.command("scan_channel") & filters.user(OWNER_ID))
async def manual_scan(client, message: Message):
    await scan_channels()
    await message.reply_text("Scan complete. Movie DB synced.")

# ===== Flask Health Check =====
@app.route('/')
def home():
    return "Bot is running."

# ===== Bot Runner =====
def run_flask():
    app.run(host="0.0.0.0", port=8000)

async def main():
    threading.Thread(target=run_flask).start()
    await bot.start()
    await scan_channels()
    print("Bot is running...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

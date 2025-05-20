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

# ======= CONFIGURATION =======
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_NAME = "movie_bot_session"
CHANNELS = ["stree2chaava2", "chaava2025"]
ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set this in Koyeb secrets
REPO_NAME = "shree95692/movie-db-backup"
FILE_NAME = "movies.json"
# =============================

app = Flask(__name__)
bot = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)
movie_db = {}

# ====== Title Extractor ======
def extract_title(text):
    patterns = [
        r"🎬 *Title *: *(.+)",
        r"Title *: *(.+)",
        r"(.+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            return re.sub(r"[^A-Za-z0-9\s]", "", title).lower()
    return None

# ====== GitHub Backup ======
def upload_to_github():
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        content = json.dumps(movie_db, indent=2)
        try:
            file = repo.get_contents(FILE_NAME)
            repo.update_file(FILE_NAME, f"update {datetime.now()}", content, file.sha)
        except:
            repo.create_file(FILE_NAME, f"create {datetime.now()}", content)
    except Exception as e:
        print("GitHub upload error:", e)

# ====== Movie Search ======
@bot.on_message(filters.private & filters.text)
async def search_movie(client, message: Message):
    query = message.text.lower()
    results = [link for title, link in movie_db.items() if query in title]

    if results:
        for link in results:
            await message.reply_text(f"**Movie Found:** [Watch Now]({link})", disable_web_page_preview=True)
    else:
        await message.reply_text(
            "**Movie not found.**\n\nYour request has been received and will be uploaded within 5–6 hours."
        )
        await bot.send_message(ALERT_CHANNEL_ID, f"❌ Movie not found for search: `{query}` by {message.from_user.mention}")

# ====== Channel Scanner ======
async def scan_channels():
    print("Scanning channels...")
    for channel in CHANNELS:
        async for msg in bot.get_chat_history(channel, limit=300):
            if msg and msg.text and hasattr(msg, "message_id"):
                title = extract_title(msg.text)
                link = f"https://t.me/{channel}/{msg.message_id}"
                if title:
                    movie_db[title] = link
                else:
                    await bot.send_message(ALERT_CHANNEL_ID, f"Unrecognized post:\n{link}")
                    try:
                        await bot.forward_messages(ALERT_CHANNEL_ID, channel, msg.message_id)
                    except:
                        pass
    upload_to_github()

# ====== New Message Listener (Fixed) ======
@bot.on_message(filters.channel)
async def new_post_handler(client, message: Message):
    if message.chat.username in CHANNELS and message.text and hasattr(message, "message_id"):
        title = extract_title(message.text)
        link = f"https://t.me/{message.chat.username}/{message.message_id}"
        if title:
            movie_db[title] = link
            upload_to_github()
        else:
            await bot.send_message(ALERT_CHANNEL_ID, f"Unrecognized new post:\n{link}")
            try:
                await bot.forward_messages(ALERT_CHANNEL_ID, message.chat.id, message.message_id)
            except:
                pass

# ====== Manual Rescan Command ======
@bot.on_message(filters.command("scan_channel") & filters.user([5163916480]))
async def manual_scan(client, message):
    await scan_channels()
    await message.reply_text("Rescan complete and backup updated.")

# ====== Flask Healthcheck ======
@app.route('/')
def home():
    return "Bot is running."

# ====== Start Bot in Thread (Async Fix) ======
def run_bot():
    async def main():
        async with bot:
            await scan_channels()
            await asyncio.Event().wait()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8000)

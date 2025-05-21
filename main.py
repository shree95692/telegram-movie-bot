import os
import json
import re
import logging
import asyncio
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# Flask for Koyeb health check
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"

# Config
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_FILE = "movie_bot_session"
CHANNELS = ["stree2chaava2", "chaava2025"]
ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
BACKUP_REPO = "shree95692/movie-db-backup"
BACKUP_FILE = "movies.json"
MOVIE_DB_FILE = "movies.json"

movie_db = {}

# Load & Save DB
def load_movie_db():
    global movie_db
    if os.path.exists(MOVIE_DB_FILE):
        with open(MOVIE_DB_FILE, "r") as f:
            movie_db = json.load(f)
    else:
        movie_db = {}

def save_movie_db():
    with open(MOVIE_DB_FILE, "w") as f:
        json.dump(movie_db, f, indent=2)

# Title extractor
def extract_title(text):
    match = re.search(r"(?i)title\s*[:\-–]\s*(.+)", text)
    if match:
        return match.group(1).split("\n")[0].strip()
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line) > 2:
            return line
    return None

# GitHub backup
def backup_to_github():
    try:
        from github import Github
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            return
        g = Github(token)
        repo = g.get_repo(BACKUP_REPO)
        contents = repo.get_contents(BACKUP_FILE)
        with open(MOVIE_DB_FILE, "r") as f:
            data = f.read()
        repo.update_file(contents.path, "Update movie DB", data, contents.sha)
    except Exception as e:
        print(f"GitHub backup failed: {e}")

# Alert
async def alert(client, message):
    try:
        await client.send_message(ALERT_CHANNEL_ID, f"⚠️ {message}")
    except Exception as e:
        print(f"Alert send failed: {e}")

# Process post
async def process_post(client, message):
    try:
        if not message.text:
            return
        title = extract_title(message.text)
        if not title:
            await alert(client, f"Failed to extract title from message ID {message.id}")
            await client.forward_messages(ALERT_CHANNEL_ID, message.chat.id, message.id)
            return
        movie_db[title.lower()] = f"https://t.me/{message.chat.username}/{message.id}"
        save_movie_db()
        backup_to_github()
    except Exception as e:
        await alert(client, f"Processing error: {e}")

# Main bot logic
async def main():
    load_movie_db()
    app_client = Client(SESSION_FILE, api_id=API_ID, api_hash=API_HASH)

    @app_client.on_message(filters.text & filters.private)
    async def search_movie(client, message):
        query = message.text.strip().lower()
        result = None
        for title, link in movie_db.items():
            if query in title:
                result = f"🎬 **{title.title()}**\n🔗 {link}"
                break
        if result:
            await message.reply(result)
        else:
            await message.reply(
                "**Movie not found!**\n\nYour request has been received and will be uploaded in 5–6 hours."
            )
            await alert(client, f"❌ Movie not found: {message.text}")

    @app_client.on_message(filters.channel)
    async def channel_msg(client, message):
        if message.chat.username in CHANNELS:
            await process_post(client, message)

    await app_client.start()
    print("Bot is running...")
    await asyncio.Event().wait()  # replaces idle()

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8000)).start()
    asyncio.run(main())

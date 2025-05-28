import os
import asyncio
import json
import re
from datetime import datetime
import base64
import requests
from pyrogram import Client, filters, idle
from pyrogram.types import Message

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "BQGD828AMUcvjUw-OoeEq9vsJglHO8FPUWRDh8MGHxV5wwvSLlpwC0_lve3qdVK-7b_0mGsKD87_-6eIS-vqD5prMNL7GjosptVTESutY3kSY3E3MYl9bq8A26SUVutyBze6xDjZP_vY_uRkXjTvEe9yu3EkGgVbndao4HAhkznY_8QIseapTYs6f8AwGXk_LkOOplSE-RJR-IuOlB3WKoaPehYOSjDRhiiKVAmt9fwzTDq1cDntoOcV6EBrzBVia1TQClWX1jPaZmNQQZ96C8mpvjMfWnFVRlM8pjmI9CPbfoNNB2tO4kuEDr2BRBdlB244CC83wV80IYO66pZ5yI7IWC7FqwAAAAEzyxzAAA"
OWNER_ID = 5163916480

CHANNELS = ["@stree2chaava2", "@chaava2025"]
ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
BACKUP_REPO = "shree95692/movie-db-backup"
DB_FILE = "movie_db.json"

app = Client("movie-bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
db = {}

MOVIE_NOT_FOUND_REPLY = (
    "**❌ Movie Not Found!**\n\n"
    "**Aapki request mil gayi hai!**\n"
    "Movie 5–6 ghante me upload kar di jayegi.\n\n"
    "_Agar upload nahi hui toh admins ko alert kar diya jayega._"
)

# Load database
def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            db = json.load(f)
    else:
        db = {}

# Save database
def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

# Extract movie title
def extract_title(text):
    try:
        match = re.search(r"[Tt]itle\s*[:\-–]\s*(.+)", text)
        if match:
            return match.group(1).strip().lower()
        elif "(" in text:
            return text.split("(")[0].strip().lower()
        else:
            return text.strip().lower()[:50]
    except Exception:
        return None

# Backup DB to GitHub
def backup_to_github():
    try:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("GitHub token missing")
            return

        url = f"https://api.github.com/repos/{BACKUP_REPO}/contents/movie_db.json"
        with open(DB_FILE, "r") as f:
            content_raw = f.read()
        content_encoded = base64.b64encode(content_raw.encode()).decode()

        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json().get("sha")

        data = {
            "message": f"Backup at {datetime.now()}",
            "content": content_encoded,
            "branch": "main"
        }
        if sha:
            data["sha"] = sha

        headers = {"Authorization": f"token {token}"}
        response = requests.put(url, headers=headers, json=data)

        if response.status_code in [200, 201]:
            print("✅ GitHub Backup Done")
        else:
            print("❌ GitHub backup failed:", response.text)
    except Exception as e:
        print("Error during GitHub backup:", e)

# When new post arrives in monitored channels
@app.on_message(filters.channel)
async def channel_post_handler(client, message: Message):
    try:
        if message.chat.username not in [c[1:] for c in CHANNELS]:
            return
        if not message.text:
            return
        title = extract_title(message.text)
        if not title:
            await app.send_message(ALERT_CHANNEL_ID, f"❗ Title not found in post:\nhttps://t.me/{message.chat.username}/{message.id}")
            return
        db[title] = f"https://t.me/{message.chat.username}/{message.id}"
        save_db()
        backup_to_github()
        await app.forward_messages(FORWARD_CHANNEL_ID, message.chat.id, message.id)
    except Exception as e:
        print("Channel post error:", e)

# Handle movie search from users
@app.on_message(filters.private & filters.text)
async def user_query_handler(client, message: Message):
    query = message.text.strip().lower()
    if query.startswith("/"):
        return  # Ignore unknown commands
    if query in db:
        await message.reply(f"✅ Movie Found:\n{db[query]}")
    else:
        await message.reply(MOVIE_NOT_FOUND_REPLY)
        await app.send_message(ALERT_CHANNEL_ID, f"❗ Movie not found for query: `{query}` by user {message.from_user.id}")

# /refresh command for old posts
@app.on_message(filters.command("refresh") & filters.user(OWNER_ID))
async def refresh_handler(client, message: Message):
    msg = await message.reply("♻️ Scanning old posts...")
    count = 0
    for channel in CHANNELS:
        try:
            async for m in app.get_chat_history(channel, limit=400):
                if not m.text:
                    continue
                title = extract_title(m.text)
                if title:
                    db[title] = f"https://t.me/{channel[1:]}/{m.id}"
                    count += 1
                else:
                    await app.send_message(ALERT_CHANNEL_ID, f"❗ No title in: https://t.me/{channel[1:]}/{m.id}")
        except Exception as e:
            await app.send_message(ALERT_CHANNEL_ID, f"❌ Error scanning {channel}: {e}")
    save_db()
    backup_to_github()
    await msg.edit(f"✅ Done! {count} movies added.")

# /uploaded command to list movies
@app.on_message(filters.command("uploaded") & filters.user(OWNER_ID))
async def uploaded_handler(client, message: Message):
    if not db:
        await message.reply("❌ Koi movie uploaded nahi hai.")
    else:
        movie_list = "\n".join([f"• {title}" for title in sorted(db.keys())])
        await message.reply(f"✅ Uploaded Movies:\n\n{movie_list[:4000]}")

# /upload dummy command
@app.on_message(filters.command("upload") & filters.user(OWNER_ID))
async def upload_handler(client, message: Message):
    await message.reply("✅ Upload command received. Manually movie upload karo channel pe.")

# /start command
@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    await message.reply("👋 Welcome! Send any movie name to check if it's available.")

if __name__ == "__main__":
    load_db()
    app.run()

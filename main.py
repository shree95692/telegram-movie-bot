import os
import asyncio
import re
import json
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from datetime import datetime
import requests

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "BQGD828AMUcvjUw-OoeEq9vsJglHO8FPUWRDh8MGHxV5wwvSLlpwC0_lve3qdVK-7b_0mGsKD87_-6eIS-vqD5prMNL7GjosptVTESutY3kSY3E3MYl9bq8A26SUVutyBze6xDjZP_vY_uRkXjTvEe9yu3EkGgVbndao4HAhkznY_8QIseapTYs6f8AwGXk_LkOOplSE-RJR-IuOlB3WKoaPehYOSjDRhiiKVAmt9fwzTDq1cDntoOcV6EBrzBVia1TQClWX1jPaZmNQQZ96C8mpvjMfWnFVRlM8pjmI9CPbfoNNB2tO4kuEDr2BRBdlB244CC83wV80IYO66pZ5yI7IWC7FqwAAAAEzyxzAAA"
OWNER_ID = 5163916480
CHANNELS = ["stree2chaava2", "chaava2025"]
ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
BACKUP_REPO = "shree95692/movie-db-backup"

DB_FILE = "movie_db.json"
db = {}

MOVIE_NOT_FOUND_REPLY = (
    "**❌ Movie Not Found!**\n\n"
    "**Aapki request mil gayi hai!**\n"
    "Movie 5–6 ghante me upload kar di jayegi.\n\n"
    "_Agar upload nahi hui toh admins ko alert kar diya jayega._"
)

app = Client(name="movie-bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            db = json.load(f)

def extract_title(text):
    try:
        match = re.search(r"[Tt]itle\s*[:\-–]\s*(.+)", text)
        if match:
            return match.group(1).strip().lower()
        elif "(" in text:
            return text.split("(")[0].strip().lower()
    except:
        return None
    return None

def backup_to_github():
    try:
        repo_url = f"https://api.github.com/repos/{BACKUP_REPO}/contents/movie_db.json"
        with open(DB_FILE, "r") as f:
            content = f.read()
        import base64
        encoded = base64.b64encode(content.encode()).decode()
        res = requests.get(repo_url)
        sha = res.json().get("sha")
        headers = {"Authorization": f"token {os.environ.get('GITHUB_TOKEN')}"}
        data = {
            "message": f"Backup at {datetime.now()}",
            "content": encoded,
            "branch": "main"
        }
        if sha:
            data["sha"] = sha
        requests.put(repo_url, headers=headers, json=data)
    except Exception as e:
        print("GitHub backup failed:", e)

@app.on_message(filters.channel & filters.chat(CHANNELS))
async def handle_new_post(client, message: Message):
    if not message.text:
        return
    title = extract_title(message.text)
    if not title:
        await app.send_message(ALERT_CHANNEL_ID, f"❗ Movie title not found in post:\nhttps://t.me/{message.chat.username}/{message.id}")
        return
    db[title] = f"https://t.me/{message.chat.username}/{message.id}"
    save_db()
    backup_to_github()
    await app.forward_messages(FORWARD_CHANNEL_ID, message.chat.id, message.id)

@app.on_message(filters.private & filters.text & ~filters.command(["upload", "uploaded", "refresh"]))
async def handle_query(client, message: Message):
    query = message.text.strip().lower()
    if query in db:
        await message.reply(f"✅ Movie Found:\n{db[query]}")
    else:
        await message.reply(MOVIE_NOT_FOUND_REPLY)
        await app.send_message(ALERT_CHANNEL_ID, f"❗ Movie not found for query: `{query}` by user {message.from_user.id}")

@app.on_message(filters.command("uploaded") & filters.user(OWNER_ID))
async def uploaded_list(client, message: Message):
    if not db:
        await message.reply("❌ Movie list abhi empty hai.")
    else:
        await message.reply("✅ Uploaded Movies:\n" + "\n".join([f"• {x}" for x in db.keys()]))

@app.on_message(filters.command("refresh") & filters.user(OWNER_ID))
async def refresh_db(client, message: Message):
    msg = await message.reply("♻️ Updating database from old posts...")
    count = 0
    for channel in CHANNELS:
        try:
            async for m in app.get_chat_history(channel, limit=200):
                if not m.text:
                    continue
                title = extract_title(m.text)
                if title:
                    db[title] = f"https://t.me/{channel}/{m.id}"
                    count += 1
                else:
                    await app.send_message(ALERT_CHANNEL_ID, f"❗ Title not found in post: https://t.me/{channel}/{m.id}")
        except Exception as e:
            await message.reply(f"⚠️ Error reading channel {channel}: {e}")
    save_db()
    backup_to_github()
    await msg.edit(f"✅ Database refreshed with {count} movies.")

@app.on_message(filters.command("upload") & filters.user(OWNER_ID))
async def handle_upload_command(client, message: Message):
    await message.reply("✅ Upload command received. Aap manually movie upload kar sakte ho.")

if __name__ == "__main__":
    load_db()
    print("Bot is running...")
    app.start()
    idle()
    app.stop()

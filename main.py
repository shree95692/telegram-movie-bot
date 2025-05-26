import os
import asyncio
import json
import re
from datetime import datetime
import base64
import requests
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from flask import Flask
from threading import Thread

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "BQGD828AMUcvjUw-OoeEq9vsJglHO8FPUWRDh8MGHxV5wwvSLlpwC0_lve3qdVK-7b_0mGsKD87_-6eIS-vqD5prMNL7GjosptVTESutY3kSY3E3MYl9bq8A26SUVutyBze6xDjZP_vY_uRkXjTvEe9yu3EkGgVbndao4HAhkznY_8QIseapTYs6f8AwGXk_LkOOplSE-RJR-IuOlB3WKoaPehYOSjDRhiiKVAmt9fwzTDq1cDntoOcV6EBrzBVia1TQClWX1jPaZmNQQZ96C8mpvjMfWnFVRlM8pjmI9CPbfoNNB2tO4kuEDr2BRBdlB244CC83wV80IYO66pZ5yI7IWC7FqwAAAAEzyxzAAA"
OWNER_ID = 5163916480

# ✅ Updated with private channel IDs
CHANNELS = {
    -1002526458211: "https://t.me/c/1526458211",  # Channel 1
    -1002397054969: "https://t.me/c/1397054969"   # Channel 2
}

ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
DB_FILE = "movie_db.json"
BACKUP_REPO = "shree95692/movie-db-backup"

app = Client("movie-bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
db = {}

MOVIE_NOT_FOUND_REPLY = (
    "**❌ Movie nahi mili!**\n\n"
    "🕵️ Request receive ho gaya hai, 5-6 ghante mein upload ho jayegi.\n\n"
    "_Agar upload nahi hui toh admin ko alert chala jaayega._"
)

def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            db = json.load(f)
    else:
        db = {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

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

@app.on_message(filters.channel)
async def channel_post_handler(client, message: Message):
    try:
        if message.chat.id not in CHANNELS:
            return
        if not message.text:
            return
        title = extract_title(message.text)
        if not title:
            await app.send_message(ALERT_CHANNEL_ID, f"❗ Title not found:\nhttps://t.me/c/{str(message.chat.id)[4:]}/{message.id}")
            return
        link = f"{CHANNELS[message.chat.id]}\nhttps://t.me/c/{str(message.chat.id)[4:]}/{message.id}"
        db[title] = link
        save_db()
        backup_to_github()
        await app.forward_messages(FORWARD_CHANNEL_ID, message.chat.id, message.id)
    except Exception as e:
        await app.send_message(ALERT_CHANNEL_ID, f"❌ Error in post ID {message.id}:\n{e}")

@app.on_message(filters.private & filters.text)
async def user_query_handler(client, message: Message):
    try:
        query = message.text.strip().lower()
        if query.startswith("/"):
            return
        for title, link in db.items():
            if query in title:
                return await message.reply(f"✅ Movie Found:\n\n{link}")
        await message.reply(MOVIE_NOT_FOUND_REPLY)
        await app.send_message(ALERT_CHANNEL_ID, f"❗ Not found: `{query}` by user {message.from_user.id}")
    except Exception as e:
        print("Error in user_query_handler:", e)

@app.on_message(filters.command("refresh") & filters.user(OWNER_ID))
async def refresh_handler(client, message: Message):
    msg = await message.reply("♻️ Scanning all posts...")
    count = 0
    for channel_id in CHANNELS:
        try:
            async for m in app.get_chat_history(channel_id, limit=1000):
                if not m.text:
                    continue
                title = extract_title(m.text)
                if title:
                    link = f"{CHANNELS[channel_id]}\nhttps://t.me/c/{str(channel_id)[4:]}/{m.id}"
                    db[title] = link
                    count += 1
                else:
                    await app.send_message(ALERT_CHANNEL_ID, f"❗ No title: https://t.me/c/{str(channel_id)[4:]}/{m.id}")
        except Exception as e:
            await app.send_message(ALERT_CHANNEL_ID, f"❌ Error in {channel_id}: {e}")
    save_db()
    backup_to_github()
    await msg.edit(f"✅ Refreshed! {count} movies added.")

@app.on_message(filters.command("uploaded") & filters.user(OWNER_ID))
async def uploaded_handler(client, message: Message):
    if not db:
        await message.reply("❌ Koi movie uploaded nahi hai.")
    else:
        text = "\n".join([f"• {t}" for t in sorted(db.keys())])
        await message.reply(f"✅ Uploaded Movies:\n\n{text[:4000]}")

@app.on_message(filters.command("upload") & filters.user(OWNER_ID))
async def manual_upload(client, message: Message):
    try:
        parts = message.text.split(" ", 2)
        if len(parts) < 3:
            return await message.reply("❗ Format: /upload movie_name post_link")
        title = parts[1].strip().lower()
        link = parts[2].strip()
        db[title] = link
        save_db()
        backup_to_github()
        await message.reply("✅ Movie manually uploaded.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    await message.reply("👋 Hello! Movie bot ready hai. Movie ka naam bhejo aur link lo.")

# Flask server for Koyeb health check
flask_app = Flask("healthcheck")

@flask_app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    load_db()
    Thread(target=run_flask).start()
    app.run()

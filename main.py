from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import re
import json
import os
import difflib
import requests
import base64
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
BOT_TOKEN = "7073579407:AAHk8xHQGaKv7xpvxgFq5_UGISwLl7NkaDM"
CHANNELS = ["@stree2chaava2", "@chaava2025"]
FORWARD_CHANNEL = -1002512169097
ALERT_CHANNEL = -1002661392627

# Backup Config (fill your token below)
GITHUB_TOKEN = "your_github_personal_access_token_here"
GITHUB_REPO = "shree95692/movie-db-backup"
GITHUB_FILE_PATH = "movie_db.json"
GITHUB_COMMITTER = {
    "name": "MovieBot",
    "email": "moviebot@example.com"
}

DB_FILE = "movie_db.json"

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        movie_db = json.load(f)
else:
    movie_db = {}

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def upload_to_github():
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }

        with open(DB_FILE, "rb") as f:
            content = f.read()
        b64_content = base64.b64encode(content).decode("utf-8")

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            sha = response.json()["sha"]
        else:
            sha = None

        data = {
            "message": f"Backup on {datetime.utcnow().isoformat()}",
            "content": b64_content,
            "committer": GITHUB_COMMITTER
        }

        if sha:
            data["sha"] = sha

        requests.put(url, headers=headers, json=data)
        print("✅ Backup uploaded to GitHub.")
    except Exception as e:
        print("❌ GitHub backup failed:", e)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(movie_db, f)
    upload_to_github()

def extract_title(text):
    lines = [re.sub(r"[^\w\s]", "", line.strip().lower()) for line in text.splitlines() if line.strip()]
    keywords = ["title", "movie", "name", "film"]

    for line in lines:
        if any(k in line for k in keywords):
            parts = re.split(r"[:\-–]", line, maxsplit=1)
            if len(parts) > 1 and len(parts[1].strip()) >= 2:
                return parts[1].strip().lower()

    for line in lines:
        if 1 <= len(line.split()) <= 6:
            return line.lower()

    return None

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hi! Mujhe koi bhi movie ka naam bhejo, mai dhoondhne ki koshish karunga.")

@bot.on_message(filters.command("register_alert"))
async def register_alert(client, message: Message):
    try:
        await client.send_message(ALERT_CHANNEL, "✅ Alert channel registered with bot successfully!")
        await message.reply_text("Alert channel registered. Forwarding should now work.")
    except Exception as e:
        await message.reply_text(f"❌ Failed to register alert channel:\n{e}")

@bot.on_message(filters.command("init_channels"))
async def init_channels(client, message: Message):
    errors = []
    try:
        await client.send_message(FORWARD_CHANNEL, "✅ Forward channel connected.")
    except Exception as e:
        errors.append(f"❌ Forward channel error:\n{e}")
    try:
        await client.send_message(ALERT_CHANNEL, "✅ Alert channel connected.")
    except Exception as e:
        errors.append(f"❌ Alert channel error:\n{e}")

    if errors:
        await message.reply_text("\n\n".join(errors))
    else:
        await message.reply_text("✅ Both channels initialized successfully.")

@bot.on_message(filters.command("scan_channel"))
async def scan_channel(client, message: Message):
    await message.reply_text("Scanning channels... This may take a while.")
    count = 0
    skipped = 0

    for channel in CHANNELS:
        try:
            async for msg in client.get_chat_history(channel, limit=1000):
                text = (msg.text or msg.caption) or ""
                title = extract_title(text)
                if title and len(title.strip()) >= 2:
                    if title not in movie_db:
                        movie_db[title] = (channel, msg.id)
                        count += 1
                    else:
                        skipped += 1
        except Exception as e:
            await message.reply_text(f"Error scanning {channel}:\n{e}")

    save_db()
    await message.reply_text(f"Scan complete!\nAdded: {count}\nSkipped (already exists): {skipped}")

@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "register_alert", "init_channels", "scan_channel"]))
async def search_movie(client, message: Message):
    query = re.sub(r"[^\w\s]", "", message.text.lower())
    valid_results = []

    all_titles = list(movie_db.keys())
    matches = difflib.get_close_matches(query, all_titles, n=5, cutoff=0.5)

    for title in matches:
        channel, msg_id = movie_db[title]
        try:
            msg = await client.get_messages(channel, msg_id)
            if not msg or (not msg.text and not msg.caption):
                raise ValueError("Deleted or empty message")
            valid_results.append(f"https://t.me/{channel.strip('@')}/{msg_id}")
        except:
            movie_db.pop(title, None)
            save_db()

    if valid_results:
        await message.reply_text("Yeh rahe matching movies:\n" + "\n".join(valid_results))
    else:
        await message.reply_text("Sorry, koi movie nahi mili.")
        await client.send_message(
            ALERT_CHANNEL,
            f"❌ Movie nahi mili: **{query}**\nUser: [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        )

@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = (message.text or message.caption) or ""
    chat_username = f"@{message.chat.username}"

    if chat_username in CHANNELS:
        title = extract_title(text)
        if title and len(title.strip()) >= 2:
            movie_db[title] = (chat_username, message.id)
            save_db()
            print(f"Saved title in DB: {title} -> {chat_username}/{message.id}")
            try:
                await client.forward_messages(FORWARD_CHANNEL, message.chat.id, [message.id])
            except Exception as e:
                print("Forward failed:", e)
                await client.send_message(ALERT_CHANNEL, f"❗ Failed to forward post:\nhttps://t.me/{message.chat.username}/{message.id}\nError: {e}")
        else:
            print("No title extracted from post.")
            try:
                await client.forward_messages(ALERT_CHANNEL, message.chat.id, [message.id])
            except Exception as e:
                print("Alert forward failed:", e)
                await client.send_message(ALERT_CHANNEL, f"❗ Title missing and forward failed:\n\nhttps://t.me/{message.chat.username}/{message.id}\nError: {e}")
    else:
        print("Post is from unknown channel.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()

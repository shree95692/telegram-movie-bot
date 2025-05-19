from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import json
import os
import re
import difflib
import requests
import base64
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running with session login!"

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_NAME = "session"
CHANNELS = ["@stree2chaava2", "@chaava2025"]
FORWARD_CHANNEL = -1002512169097
ALERT_CHANNEL = -1005163916480  # <-- Fixed here

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
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

bot = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

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
        sha = response.json()["sha"] if response.status_code == 200 else None
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
    patterns = [
        r"(?i)title\s*[:\-–]?\s*\*{0,2}(.*?)\*{0,2}\n",
        r"^🎬\s*Title\s*[:\-–]?\s*\*{0,2}(.*?)\*{0,2}",
        r"(?i)^Title\s*[:\-–]?\s*(.*?)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return re.sub(r"[^\w\s]", "", match.group(1).strip().lower())
    lines = [re.sub(r"[^\w\s]", "", line.strip().lower()) for line in text.splitlines() if line.strip()]
    for line in lines:
        if 1 <= len(line.split()) <= 6:
            return line
    return None

@bot.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text("Hi! Mujhe koi bhi movie ka naam bhejo, mai dhoondhne ki koshish karunga.")

@bot.on_message(filters.command("scan_channel"))
async def scan_channels(client, message: Message):
    await message.reply_text("Scanning channels... please wait.")
    added, skipped = 0, 0
    for channel in CHANNELS:
        try:
            async for msg in client.get_chat_history(channel, limit=1000):
                text = (msg.text or msg.caption) or ""
                title = extract_title(text)
                if title and title not in movie_db:
                    movie_db[title] = (channel, msg.id)
                    added += 1
                else:
                    skipped += 1
        except Exception as e:
            await message.reply_text(f"❌ Error in {channel}:\n{e}")
    save_db()
    await message.reply_text(f"✅ Scan complete!\nAdded: {added}\nSkipped: {skipped}")

@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "scan_channel"]))
async def search_movie(client, message: Message):
    query = re.sub(r"[^\w\s]", "", message.text.lower())
    all_titles = list(movie_db.keys())
    matches = difflib.get_close_matches(query, all_titles, n=5, cutoff=0.5)
    valid_results = []

    for title in matches:
        channel, msg_id = movie_db[title]
        try:
            msg = await client.get_messages(channel, msg_id)
            if not msg or (not msg.text and not msg.caption):
                raise ValueError("Deleted")
            valid_results.append(f"https://t.me/{channel.strip('@')}/{msg_id}")
        except:
            movie_db.pop(title, None)
            save_db()

    if valid_results:
        await message.reply_text("Yeh rahe matching results:\n" + "\n".join(valid_results))
    else:
        await message.reply_text(
            "Sorry, movie nahi mili.\n\n"
            "Aapka request record ho gaya hai.\n"
            "**5–6 ghante me upload ho jaayega.**\n"
            "_Tab tak dubara visit kare!_"
        )
        await client.send_message(ALERT_CHANNEL, f"❌ Not found: **{query}** by [{message.from_user.first_name}](tg://user?id={message.from_user.id})")

@bot.on_message(filters.channel)
async def process_new_post(client, message: Message):
    text = (message.text or message.caption) or ""
    chat_username = f"@{message.chat.username}"

    if chat_username in CHANNELS:
        title = extract_title(text)
        if title:
            movie_db[title] = (chat_username, message.id)
            save_db()
            try:
                await client.forward_messages(FORWARD_CHANNEL, message.chat.id, [message.id])
            except Exception as e:
                await client.send_message(ALERT_CHANNEL, f"❗ Forward failed:\nhttps://t.me/{message.chat.username}/{message.id}\nError: {e}")
        else:
            await client.send_message(ALERT_CHANNEL, f"❗ Title not found in:\nhttps://t.me/{message.chat.username}/{message.id}")
    else:
        print("Post is from unknown source.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()

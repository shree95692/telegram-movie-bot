import os
import json
import time
import requests
from flask import Flask
from threading import Thread
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from datetime import datetime

# Session & API config
SESSION_NAME = "movie_bot_session"
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"

# Channels
SOURCE_CHANNELS = ["stree2chaava2", "chaava2025"]
FORWARD_CHANNEL_ID = -1002512169097
ALERT_CHANNEL_ID = -1002661392627

# GitHub
GITHUB_REPO = "shree95692/movie-db-backup"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Files
DB_FILE = "movies.json"

# Flask app
web = Flask(__name__)

@web.route("/")
def home():
    return "Movie bot is running."

# Pyrogram app
app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

movie_db = {}

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

def upload_to_github():
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        with open(DB_FILE, "r") as f:
            content = f.read()
        b64_content = content.encode("utf-8").decode("utf-8")
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_FILE}"
        get_req = requests.get(url, headers=headers).json()
        sha = get_req.get("sha", "")
        data = {
            "message": f"Backup {datetime.utcnow()}",
            "content": b64_content,
            "sha": sha if sha else None
        }
        requests.put(url, headers=headers, json=data)
    except Exception as e:
        print("GitHub backup error:", e)

def alert(text):
    try:
        app.send_message(ALERT_CHANNEL_ID, f"**Alert:** {text}")
    except:
        pass

def extract_title(text):
    lines = text.splitlines()
    for line in lines:
        if "title" in line.lower():
            title = line.split(":", 1)[-1].strip(" 🎬:-").strip()
            if title:
                return title.lower()
    return None

@app.on_message(filters.channel & filters.chat(SOURCE_CHANNELS))
def save_movie(client, message: Message):
    text = message.text or message.caption or ""
    title = extract_title(text)
    if not title:
        alert(f"❗ Title not found in post: https://t.me/{message.chat.username}/{message.id}")
        return
    movie_db[title] = f"https://t.me/{message.chat.username}/{message.id}"
    save_db()
    upload_to_github()

@app.on_message(filters.private & filters.text)
def handle_query(client, message: Message):
    query = message.text.strip().lower()
    for title, link in movie_db.items():
        if query in title:
            message.reply_text(f"**Found:** [{title.title()}]({link})", disable_web_page_preview=True)
            return
    alert(f"❌ Movie not found: {query}")
    message.reply_text("**Movie not found!**\n\nDon't worry, your request has been received and will be uploaded in 5–6 hours.")

# Start everything
def run_bot():
    app.start()
    load_db()
    print("Bot is running...")
    idle()
    app.stop()

def run_web():
    web.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_bot).start()
    run_web()

import os
import json
import time
import requests
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from datetime import datetime

# ==== Session Config ====
SESSION_NAME = "movie_bot_session"
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"

# ==== Channels ====
SOURCE_CHANNELS = ["stree2chaava2", "chaava2025"]
FORWARD_CHANNEL_ID = -1002512169097
ALERT_CHANNEL_ID = -1002661392627

# ==== GitHub Config ====
GITHUB_REPO = "shree95692/movie-db-backup"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Add token in koyeb secret

# ==== Files ====
DB_FILE = "movies.json"
LOG_FILE = "movie_db.json"

# ==== Start Flask App for Koyeb ====
web = Flask(__name__)

@web.route("/")
def home():
    return "Movie Bot Running"

# ==== Create Pyrogram App ====
app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

# ==== Utility Functions ====

def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def extract_title(text):
    lines = text.splitlines()
    for line in lines:
        if "title" in line.lower():
            clean = line.split(":", 1)[-1].strip(" 🎬:-").strip()
            if clean:
                return clean.lower()
    return None

def upload_to_github():
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        with open(DB_FILE, "r") as f:
            content = f.read()
        b64_data = content.encode("utf-8").decode("utf-8")
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_FILE}"
        sha = requests.get(url, headers=headers).json().get("sha", "")
        data = {
            "message": f"Backup: {datetime.utcnow()}",
            "content": b64_data.encode("utf-8").decode("utf-8"),
            "sha": sha
        }
        requests.put(url, headers=headers, json=data)
    except Exception as e:
        print("GitHub backup error:", e)

def alert(msg):
    try:
        app.send_message(ALERT_CHANNEL_ID, f"**Alert:** {msg}")
    except Exception as e:
        print("Failed to send alert:", e)

# ==== Main Movie DB ====
movie_db = load_json(DB_FILE)

# ==== On New Messages in Channel ====
@app.on_message(filters.channel & filters.chat(SOURCE_CHANNELS))
def update_db(client, message: Message):
    try:
        text = message.text or message.caption or ""
        title = extract_title(text)
        if not title:
            alert(f"Title not found in post {message.link}")
            return

        link = f"https://t.me/{message.chat.username}/{message.id}"
        movie_db[title.lower()] = link
        save_json(movie_db, DB_FILE)
        save_json(movie_db, LOG_FILE)
        upload_to_github()

    except Exception as e:
        alert(f"Failed to add post {message.link if message else 'unknown'}\n{str(e)}")

# ==== On Private Message (Search) ====
@app.on_message(filters.private & filters.text)
def search_movie(client, message: Message):
    query = message.text.lower().strip()
    if not query:
        return

    for title, link in movie_db.items():
        if query in title:
            message.reply_text(f"**Found:** [{title.title()}]({link})", disable_web_page_preview=True)
            return

    alert(f"Movie not found: {query}")
    message.reply_text(f"**Movie not found!**\n\nDon't worry, your request has been received and the movie will be uploaded within 5–6 hours.")

# ==== Start Bot ====
if __name__ == "__main__":
    app.start()
    print("Bot Started")
    web.run(host="0.0.0.0", port=8000)
    idle()
    app.stop()

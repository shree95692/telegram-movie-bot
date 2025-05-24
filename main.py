import os
import json
import requests
from flask import Flask, request
from pyrogram import Client, filters
from pyrogram.types import Message
from threading import Thread

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "BQGD828AMUcvjUw-OoeEq9vsJglHO8FPUWRDh8MGHxV5wwvSLlpwC0_lve3qdVK-7b_0mGsKD87_-6eIS-vqD5prMNL7GjosptVTESutY3kSY3E3MYl9bq8A26SUVutyBze6xDjZP_vY_uRkXjTvEe9yu3EkGgVbndao4HAhkznY_8QIseapTYs6f8AwGXk_LkOOplSE-RJR-IuOlB3WKoaPehYOSjDRhiiKVAmt9fwzTDq1cDntoOcV6EBrzBVia1TQClWX1jPaZmNQQZ96C8mpvjMfWnFVRlM8pjmI9CPbfoNNB2tO4kuEDr2BRBdlB244CC83wV80IYO66pZ5yI7IWC7FqwAAAAEzyxzAAA"
FORWARD_CHANNELS = ["stree2chaava2", "chaava2025"]
FORWARD_CHANNEL_IDS = [-1002512169097]
ALERT_CHANNEL_ID = -1002661392627

DB_FILE = "movies.json"
GITHUB_REPO = "shree95692/movie-db-backup"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

flask_app = Flask(__name__)
bot = Client("session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# --- DB UTILS ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def upload_to_github():
    with open(DB_FILE, "r") as f:
        content = f.read()
    path = "movies.json"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        sha = res.json()["sha"]
        data = {
            "message": "Update DB",
            "content": content.encode("utf-8").decode("utf-8"),
            "sha": sha
        }
        requests.put(url, headers=headers, json=data)
    else:
        data = {
            "message": "Initial upload",
            "content": content.encode("utf-8").decode("utf-8")
        }
        requests.put(url, headers=headers, json=data)

# --- TITLE EXTRACT ---
def extract_title(text):
    lines = text.splitlines()
    for line in lines:
        if "title" in line.lower():
            parts = line.split(":")
            if len(parts) > 1:
                return parts[1].strip()
            return line.strip()
    return None

# --- UPLOAD MESSAGE ---
def process_message(msg: Message, db):
    title = extract_title(msg.text or msg.caption or "")
    if not title:
        bot.send_message(ALERT_CHANNEL_ID, f"❌ Failed to extract title:\n{msg.link}")
        return
    db[title.lower()] = msg.link
    save_db(db)
    upload_to_github()

# --- SCAN OLD POSTS ---
def scan_all_messages():
    db = load_db()
    for ch in FORWARD_CHANNELS:
        for msg in bot.get_chat_history(ch):
            try:
                if msg.text or msg.caption:
                    process_message(msg, db)
            except Exception as e:
                print("Error scanning:", e)

# --- STARTUP SYNC ---
def startup():
    print("Syncing old messages...")
    scan_all_messages()

# --- BOT HANDLERS ---
@bot.on_message(filters.command("rescan"))
def handle_rescan(_, msg):
    msg.reply("Rescanning all messages...")
    scan_all_messages()
    msg.reply("✅ Rescan complete.")

@bot.on_message(filters.command("uploaded"))
def handle_uploaded(_, msg):
    db = load_db()
    if db:
        msg.reply("Uploaded Movies:\n\n" + "\n".join(db.keys()))
    else:
        msg.reply("Koi movie abhi tak upload nahi hui.")

@bot.on_message(filters.text & filters.private)
def search_movie(_, msg):
    query = msg.text.strip().lower()
    db = load_db()
    result = db.get(query)
    if result:
        msg.reply(f"✅ Movie mil gaya!\n\n**Link:** {result}")
    else:
        msg.reply(
            f"❌ Movie not found: **{msg.text}**\n"
            "Request received. Movie 5-6 ghante me upload kar diya jayega."
        )
        bot.send_message(ALERT_CHANNEL_ID, f"❌ Movie not found: {msg.text}")

# --- FLASK ROUTE ---
@flask_app.route('/')
def home():
    return "Bot is running."

# --- RUN ---
Thread(target=bot.run).start()
Thread(target=startup).start()
flask_app.run(host="0.0.0.0", port=8080)

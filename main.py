from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import os
import json
import requests

# --- CONFIG ---
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "BQGD828AMUcvjUw-OoeEq9vsJglHO8FPUWRDh8MGHxV5wwvSLlpwC0_lve3qdVK-7b_0mGsKD87_-6eIS-vqD5prMNL7GjosptVTESutY3kSY3E3MYl9bq8A26SUVutyBze6xDjZP_vY_uRkXjTvEe9yu3EkGgVbndao4HAhkznY_8QIseapTYs6f8AwGXk_LkOOplSE-RJR-IuOlB3WKoaPehYOSjDRhiiKVAmt9fwzTDq1cDntoOcV6EBrzBVia1TQClWX1jPaZmNQQZ96C8mpvjMfWnFVRlM8pjmI9CPbfoNNB2tO4kuEDr2BRBdlB244CC83wV80IYO66pZ5yI7IWC7FqwAAAAEzyxzAAA"
FORWARD_CHANNELS = ["stree2chaava2", "chaava2025"]
FORWARD_CHANNEL_IDS = [-1002527549477, -1002512169097]
ALERT_CHANNEL_ID = -1002661392627
DB_FILE = "movies.json"
GITHUB_REPO = "shree95692/movie-db-backup"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# --- FLASK ---
flask_app = Flask(__name__)

# --- DATABASE UTILS ---
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

    repo = GITHUB_REPO
    file_path = "movies.json"
    api_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    res = requests.get(api_url, headers=headers)
    if res.status_code == 200:
        sha = res.json()["sha"]
        data = {
            "message": "Update DB",
            "content": content.encode("utf-8").decode("utf-8"),
            "sha": sha
        }
    else:
        data = {
            "message": "Initial DB upload",
            "content": content.encode("utf-8").decode("utf-8")
        }

    requests.put(api_url, headers=headers, json=data)

# --- SMART TITLE EXTRACT ---
def extract_title(text):
    lines = text.splitlines()
    for line in lines:
        if "title" in line.lower():
            parts = line.split(":")
            if len(parts) > 1:
                return parts[1].strip()
            return line.strip()
    return None

# --- FLASK SERVER ---
@flask_app.route('/')
def home():
    return "Bot is running!", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

# --- START BOT ---
bot = Client("movie-bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
db = load_db()

@bot.on_message(filters.command("rescan"))
async def rescan(_, msg: Message):
    total = 0
    for channel in FORWARD_CHANNEL_IDS:
        async for message in bot.get_chat_history(channel, limit=300):
            if message.text:
                title = extract_title(message.text)
                if title:
                    db[title.lower()] = f"https://t.me/{(await bot.get_chat(channel)).username}/{message.message_id}"
                    total += 1
                else:
                    await bot.send_message(ALERT_CHANNEL_ID, f"Title not found in post: https://t.me/c/{str(channel)[4:]}/{message.message_id}")
    save_db(db)
    upload_to_github()
    await msg.reply(f"Scan completed! {total} movies added.")

@bot.on_message(filters.command("uploaded"))
async def uploaded(_, msg: Message):
    if not db:
        await msg.reply("Koi movie abhi tak upload nahi hui.")
    else:
        titles = list(db.keys())
        message = "**Uploaded Movies:**\n" + "\n".join([f"- {t.title()}" for t in titles])
        await msg.reply(message[:4000])

@bot.on_message(filters.command("add"))
async def add_movie(_, msg: Message):
    if len(msg.command) < 3:
        await msg.reply("Format: `/add MovieName https://t.me/channel/postid`")
        return
    title = msg.command[1].lower()
    link = msg.command[2]
    db[title] = link
    save_db(db)
    upload_to_github()
    await msg.reply("Movie manually added!")

@bot.on_message(filters.text & filters.private)
async def search(_, msg: Message):
    query = msg.text.lower()
    for title, link in db.items():
        if query in title:
            await msg.reply(f"**Movie mil gaya!**\n{link}")
            return
    await msg.reply("Movie nahi mili! Request receive ho gayi hai, 5-6 ghante me upload ho jayegi.")
    await bot.send_message(ALERT_CHANNEL_ID, f"Not found: {msg.text}")

# --- Run both bot and web server ---
Thread(target=run_flask).start()
bot.run()

import os
import json
import asyncio
import threading
import re
import subprocess
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import MessageIdInvalid, ChannelPrivate
from dotenv import load_dotenv

# === Load ENV ===
load_dotenv()

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "BQGD828Ai3p2VB1hxn-tQZMzP0KzDDsQeL3WmbfNJy-DRUbyWXwR6KlA1u0CurZNgpBhq91q3-mhXrGtf2_I8XrSzHlZ5-imxUbdI_F74ZQNnZqocw7VcJCF-j0YuoDhmQ7fREpOyFuU1LSbZcsZnwQt091ehbX0lAB8sdI8GcoBbnVgONMW9Hs5jYEYDZ5WB1lVBfb8uZYZHCFP9Z-eh8qe4US1jusUni2MJXrxf0ElUHz0F6dpe8B4jAxEqqRIElAj4LU9g51W_O8_u5DlHL9siAym_5tQD1cvcstAWZmix-h7hEuOk_-WuGENwx3Mf7eNt6haYaSk8fBzijR4XwWuKVSPlgAAAAEzyxzAAA"

MOVIE_CHANNELS = {
    "stree2chaava2": "https://t.me/stree2chaava2",
    "chaava2025": "https://t.me/chaava2025"
}

ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
MOVIE_DB_FILE = "movie_db.json"
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL")

# === Flask ===
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ Movie Bot is Live!"

def run_flask():
    app.run(host="0.0.0.0", port=8000)

# === DB ===
def load_db():
    if os.path.exists(MOVIE_DB_FILE):
        with open(MOVIE_DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(MOVIE_DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def backup_to_github():
    try:
        if not GITHUB_REPO_URL:
            print("❌ GITHUB_REPO_URL not set.")
            return
        subprocess.run(["rm", "-rf", ".git"], check=True)
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "remote", "add", "origin", GITHUB_REPO_URL], check=True)
        subprocess.run(["git", "config", "user.email", "moviebot@github.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Movie Bot"], check=True)
        subprocess.run(["git", "add", MOVIE_DB_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "🔄 Auto Backup movie_db.json"], check=True)
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        subprocess.run(["git", "push", "-u", "origin", "main", "--force"], check=True)
        print("✅ GitHub backup success")
    except Exception as e:
        print(f"❌ GitHub backup failed: {e}")

# === Title Extractor ===
def extract_title(text):
    text = text.replace("**", "").replace("__", "")
    pattern = r"[🎬🔊🆕🚀📥]?\s*(title|movie|film)?\s*[:\-]?\s*([A-Za-z0-9\s\-:().,']{2,50})"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        title = match.group(2).strip(" :-().,'").lower()
        if 2 <= len(title) <= 50:
            return title
    for line in text.splitlines():
        if 2 <= len(line) <= 50 and any(c.isalpha() for c in line):
            return line.strip().lower()
    return None

# === Pyrogram Bot ===
bot = Client(name="moviebot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
movie_db = load_db()

@bot.on_message(filters.command("start"))
async def start_cmd(_, msg):
    await msg.reply(
        "👋 Welcome to **Movie Request Bot**\n\n"
        "🎬 Type movie name to search.\n"
        "📥 If not found, it will be uploaded in 5–6 hours.\n"
        "🗂️ /upload_db for admin backup.\n"
        "📃 /uploaded_movies to view all movies."
    )

@bot.on_message(filters.command("upload_db"))
async def upload_db(_, msg):
    try:
        await msg.reply_document(MOVIE_DB_FILE, caption="📁 Movie DB backup file")
    except:
        await msg.reply("❌ DB file upload failed.")

@bot.on_message(filters.command("uploaded_movies"))
async def uploaded_movies(_, msg):
    movies = list(movie_db.keys())
    if not movies:
        await msg.reply("⚠️ No movies found in DB.")
        return
    movies.sort()
    txt = "**🎬 Uploaded Movies:**\n\n"
    for i, title in enumerate(movies, 1):
        txt += f"{i}. {title}\n"
        if len(txt) > 3500:
            await msg.reply(txt)
            txt = ""
    if txt:
        await msg.reply(txt)

@bot.on_message(filters.text & filters.private)
async def search_movie(_, msg):
    q = msg.text.lower()
    for title, data in movie_db.items():
        if q in title:
            try:
                await bot.get_messages(data["channel_id"], data["message_id"])
                for uname, link in MOVIE_CHANNELS.items():
                    try:
                        if await bot.get_chat(uname).id == data["channel_id"]:
                            await msg.reply(f"✅ **Movie Found:**\n👉 {link}/{data['message_id']}")
                            return
                    except:
                        continue
                fallback = f"https://t.me/c/{str(data['channel_id'])[4:]}/{data['message_id']}"
                await msg.reply(f"✅ **Movie Found:**\n👉 {fallback}")
                return
            except:
                await msg.reply("⚠️ Movie was in DB but the post was **deleted**.")
                return
    await msg.reply(
        "❌ **Movie Not Found**\n\n📩 Your request has been noted.\nMovie will be uploaded in 5–6 hours."
    )
    try:
        await bot.send_message(ALERT_CHANNEL_ID, f"❌ Not Found: `{q}`\nFrom: {msg.from_user.mention}")
    except:
        print("❌ Alert send failed")

@bot.on_message(filters.channel)
async def channel_post_handler(_, msg):
    if not msg.text:
        return
    title = extract_title(msg.text)
    if not title:
        try:
            await bot.forward_messages(ALERT_CHANNEL_ID, msg.chat.id, msg.id)
        except:
            print("⚠️ Failed to forward unrecognized post")
        return
    if title in movie_db:
        return
    movie_db[title] = {
        "channel_id": msg.chat.id,
        "message_id": msg.id
    }
    save_db(movie_db)
    backup_to_github()
    try:
        await bot.copy_message(FORWARD_CHANNEL_ID, msg.chat.id, msg.id)
    except:
        pass

async def update_from_channel(channel_id):
    async for msg in bot.get_chat_history(channel_id):
        if not msg.text:
            continue
        title = extract_title(msg.text)
        if not title or title in movie_db:
            continue
        movie_db[title] = {
            "channel_id": channel_id,
            "message_id": msg.id
        }
        try:
            await bot.copy_message(FORWARD_CHANNEL_ID, channel_id, msg.id)
        except:
            pass
    save_db(movie_db)
    backup_to_github()

async def remove_deleted_posts():
    to_del = []
    for title, data in movie_db.items():
        try:
            await bot.get_messages(data["channel_id"], data["message_id"])
        except (MessageIdInvalid, ChannelPrivate):
            to_del.append(title)
    for title in to_del:
        del movie_db[title]
    if to_del:
        save_db(movie_db)
        backup_to_github()

async def startup_tasks():
    try:
        await bot.send_message(ALERT_CHANNEL_ID, "🔄 Starting scan of movie channels...")
    except:
        print("⚠️ Startup alert failed.")
    for uname in MOVIE_CHANNELS:
        try:
            chat = await bot.get_chat(uname)
            await update_from_channel(chat.id)
        except Exception as e:
            try:
                await bot.send_message(ALERT_CHANNEL_ID, f"❌ Failed to scan @{uname}\n`{e}`")
            except:
                print("⚠️ Channel scan alert failed")
    await remove_deleted_posts()
    try:
        await bot.send_message(ALERT_CHANNEL_ID, "✅ All channels scanned. Bot is ready!")
    except:
        print("✅ Final startup alert failed")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    async def main():
        await bot.start()
        await startup_tasks()
        await idle()
    asyncio.run(main())

from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import re
import json
import os
import requests
import math
import base64

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

DB_FILE = "movie_db.json"
REPO = "shree95692/movie-db-backup"
BRANCH = "main"
GITHUB_FILE_PATH = "movie_db.json"
GITHUB_PAT = os.environ.get("GITHUB_PAT")

def restore_db_from_github():
    if not GITHUB_PAT:
        print("No GitHub PAT found, skipping restore.")
        return

    try:
        headers = {
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"https://api.github.com/repos/{REPO}/contents/{GITHUB_FILE_PATH}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json().get("content")
            if content:
                decoded = base64.b64decode(content)
                with open(DB_FILE, "wb") as f:
                    f.write(decoded)
                print("✅ movie_db.json restored from GitHub.")
        else:
            print("Failed to fetch from GitHub:", response.text)
    except Exception as e:
        print("Restore failed:", e)

# Replace this block:
# if os.path.exists(DB_FILE):
#     with open(DB_FILE, "r") as f:
#         movie_db = json.load(f)
# else:
#     movie_db = {}

# With this:
if not os.path.exists(DB_FILE):
    restore_db_from_github()

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        movie_db = json.load(f)
else:
    movie_db = {}

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(movie_db, f, indent=4, ensure_ascii=False)

    if GITHUB_PAT:
        try:
            with open(DB_FILE, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            push_to_github(content)
        except Exception as e:
            print("GitHub push failed:", e)

def push_to_github(content):
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{REPO}/contents/{GITHUB_FILE_PATH}"
    get_response = requests.get(url, headers=headers)
    sha = get_response.json().get("sha")

    data = {
        "message": "Update movie_db.json",
        "content": content,
        "branch": BRANCH
    }

    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data)
    print("GitHub push status:", response.status_code)

def extract_title(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    for line in lines:
        lower_line = line.lower()
        if any(k in lower_line for k in ["title", "movie", "name", "film"]):
            parts = re.split(r"[:\-–]", line, maxsplit=1)
            if len(parts) > 1 and len(parts[1].strip()) >= 2:
                return parts[1].strip().lower()

    if 1 <= len(lines[0].split()) <= 8:
        return lines[0].lower()

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
        await client.send_message(ALERT_CHANNEL, "✅ Alert channel registered successfully!")
        await message.reply_text("Alert channel registered.")
    except Exception as e:
        await message.reply_text(f"❌ Failed to register:\n{e}")

@bot.on_message(filters.command("init_channels"))
async def init_channels(client, message: Message):
    errors = []

    try:
        await client.send_message(FORWARD_CHANNEL, "✅ Forward channel connected.")
    except Exception as e:
        errors.append(f"❌ Forward error:\n{e}")

    try:
        await client.send_message(ALERT_CHANNEL, "✅ Alert channel connected.")
    except Exception as e:
        errors.append(f"❌ Alert error:\n{e}")

    await message.reply_text("\n\n".join(errors) if errors else "✅ Both channels initialized.")

@bot.on_message(filters.command("list_movies"))
async def list_movies(client, message: Message):
    page = 1
    try:
        args = message.text.split()
        if len(args) > 1:
            page = int(args[1])
    except:
        pass

    movies = sorted(movie_db.keys())
    total_pages = math.ceil(len(movies) / 20)

    if page < 1 or page > total_pages:
        await message.reply_text(f"❌ Page not found. Total pages: {total_pages}")
        return

    start = (page - 1) * 20
    end = start + 20
    page_movies = movies[start:end]
    text = f"📽️ **Movies (Page {page}/{total_pages})**\n\n"

    for i, title in enumerate(page_movies, start=start + 1):
        text += f"{i}. {title.title()}\n"

    await message.reply_text(text)

@bot.on_message(filters.command("add_movie"))
async def add_movie_cmd(client, message: Message):
    if message.from_user.id != 5163916480:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        _, data = message.text.split(" ", 1)
        title, link = data.split("|", 1)
        title = title.strip().lower()
        link = link.strip()
        match = re.search(r"t\.me/(.+)/(\d+)", link)
        if match:
            channel = "@" + match.group(1)
            msg_id = int(match.group(2))
            movie_db[title] = (channel, msg_id)
            save_db()
            await message.reply_text(f"✅ Added manually: {title}")
        else:
            await message.reply_text("❌ Invalid link format. Use /add_movie Movie Name | https://t.me/channel/123")
    except:
        await message.reply_text("❌ Usage: /add_movie Movie Name | https://t.me/channel/123")

@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "register_alert", "init_channels", "list_movies", "add_movie"]))
async def search_movie(client, message: Message):
    query = message.text.lower()
    valid_results = []

    to_remove = []
    for title, (channel, msg_id) in list(movie_db.items()):
        if query in title:
            try:
                msg = await client.get_messages(channel, msg_id)
                if msg and (msg.text or msg.caption):
                    valid_results.append(f"https://t.me/{channel.strip('@')}/{msg_id}")
                else:
                    to_remove.append(title)
            except:
                to_remove.append(title)

    for title in to_remove:
        movie_db.pop(title, None)

    if to_remove:
        save_db()

    if valid_results:
        await message.reply_text("🎬 Matching movies:\n" + "\n".join(valid_results))
    else:
        await message.reply_text(
            "❌ Movie nahi mili bhai 😔\n"
            "🔍 Ek baar naam ki spelling Google se check kar lo.\n"
            "📩 Request mil gayi hai!\n"
            "⏳ 5-6 ghante me upload ho jayegi.\n"
            "🍿 Tab tak popcorn leke chill maro!"
        )
        await client.send_message(ALERT_CHANNEL,
            text=f"❌ Movie not found: **{query}**\nUser: [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
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
            print(f"✅ Saved: {title} -> {chat_username}/{message.id}")
            try:
                await client.forward_messages(FORWARD_CHANNEL, message.chat.id, [message.id])
            except Exception as e:
                await client.send_message(ALERT_CHANNEL,
                    text=f"❗ Forward failed:\nhttps://t.me/{message.chat.username}/{message.id}\nError: {e}"
                )
        else:
            await client.forward_messages(ALERT_CHANNEL, message.chat.id, [message.id])
    else:
        print("⚠️ Unknown channel.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    print("🚀 Starting Flask server...")
    Thread(target=run_flask).start()

    print("🤖 Starting Telegram bot...")
    Thread(target=lambda: bot.run()).start()

    # Prevent Koyeb from sleeping by keeping main thread alive
    while True:
        time.sleep(10)

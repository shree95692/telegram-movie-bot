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
import time

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
    print("📤 GitHub push status:", response.status_code)

def extract_title(text):
    match = re.search(r'🎬\s*(?:Title\s*:)?\s*(.+)', text, re.IGNORECASE)
    if match:
        raw_title = match.group(1).strip()

        stop_words = ['480p', '720p', '1080p', 'HDRip', 'WEBRip', 'Download', 'Watch', 'Online', 'S01', 'S02', 'Complete']
        for stop in stop_words:
            if stop.lower() in raw_title.lower():
                raw_title = raw_title[:raw_title.lower().find(stop.lower())].strip()

        cleaned_title = re.sub(r'[^\w\s:\-()\'\"]+', '', raw_title)
        cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()

        return cleaned_title.lower() if cleaned_title else None

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
    text = f"📽️ Movies (Page {page}/{total_pages})\n\n"

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

@bot.on_message(filters.incoming & (filters.private | filters.group) & filters.text & ~filters.command(["start", "register_alert", "init_channels", "list_movies", "add_movie"]))
async def search_movie(client, message: Message):
    query = message.text.lower().strip()

    greetings = ["hi", "hello", "hii", "ok", "okay", "hey", "heyy"]
    if query in greetings:
        await message.reply_text("Hello 👋")
        return

    matches = []
    for title, data in movie_db.items():
        if not (isinstance(data, (list, tuple)) and len(data) == 2):
            continue
        channel, msg_id = data
        if query in title:
            match_score = title.count(query)
            matches.append((match_score, title, channel, msg_id))

    matches.sort(key=lambda x: (-x[0], x[1]))

    valid_results = []
    to_remove = []

    for _, title, channel, msg_id in matches[:5]:
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
        await client.send_message(
            ALERT_CHANNEL,
            text=f"❌ Movie not found: {query}\nUser: [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        )

@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = (message.text or message.caption) or ""
    chat_username = f"@{message.chat.username}"

    if chat_username in CHANNELS:
        title = extract_title(text)
        if title and len(title.strip()) >= 2:
            def normalize_title(title):
                title = title.lower()
                title = re.sub(r'\(\d{4}\)', '', title)  # remove (2023)
                title = re.sub(r'\d{4}', '', title)       # remove 2023
                title = re.sub(r'\s+', ' ', title).strip()
                return title

            normalized_new = normalize_title(title)
            matching_titles = [t for t in movie_db if normalize_title(t) == normalized_new]

            new_link = f"https://t.me/{chat_username.strip('@')}/{message.id}"

            valid_links = []
            updated_entry = []

            for t in matching_titles:
                data = movie_db.get(t)
                entries = []
                if isinstance(data, tuple):
                    entries = [data]
                elif isinstance(data, list):
                    entries = [entry for entry in data if isinstance(entry, tuple) and len(entry) == 2]

                for ch, msg_id in entries:
                    try:
                        msg = await client.get_messages(ch, msg_id)
                        if msg:
                            valid_links.append(f"https://t.me/{ch.strip('@')}/{msg_id}")
                            updated_entry.append((ch, msg_id))
                    except Exception as e:
                        print(f"⚠️ Fetch failed for {t}: {e}")

            valid_links.append(new_link)
            updated_entry.append((chat_username, message.id))

            if len(valid_links) > 1:
                alert_text = (
                    f"⚠️ Duplicate movie detected: {title.title()}\n\n"
                    f"🔁 All related posts:\n" + "\n".join(valid_links)
                )
                try:
                    await client.send_message(ALERT_CHANNEL, alert_text)
                except Exception as e:
                    print("⚠️ Duplicate alert send failed:", e)

            movie_db[title] = updated_entry
            save_db()
            print(f"✅ Saved: {title} -> {chat_username}/{message.id}")

            try:
                await client.send_message(FORWARD_CHANNEL, f"🎬 New Movie Added: {title.title()}")
            except Exception as e:
                await client.send_message(ALERT_CHANNEL,
                    text=f"❗ Message send failed:\n{new_link}\nError: {e}"
                )
        else:
            await client.send_message(
                ALERT_CHANNEL,
                f"⚠️ Title detect nahi hua for post: https://t.me/{message.chat.username}/{message.id}"
            )
    else:
        print("⚠️ Unknown channel.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    print("✅ movie_db.json restored from GitHub.")
    print("🚀 Starting Flask server...")
    Thread(target=run_flask).start()
    print("🤖 Starting Telegram bot...")
    bot.run()

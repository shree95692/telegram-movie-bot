# SAME IMPORTS
import os
import json
import asyncio
import threading
import re
import subprocess
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import MessageIdInvalid, ChannelPrivate, MessageNotModified, PeerIdInvalid

# === CONFIG ===
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_NAME = "my"

MOVIE_CHANNELS = {
    "stree2chaava2": "https://t.me/stree2chaava2",
    "chaava2025": "https://t.me/chaava2025"
}

ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
MOVIE_DB_FILE = "movie_db.json"
GITHUB_REPO = "shree95692/movie-db-backup"

# === FLASK ===
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ Movie Bot is running!"

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
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            print("[GitHub Backup Error] GITHUB_TOKEN not set.")
            return

        repo_url = f"https://{github_token}@github.com/{GITHUB_REPO}.git"

        subprocess.run(["git", "config", "--global", "user.name", "moviebot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "bot@example.com"], check=True)
        subprocess.run(["git", "config", "--global", "pull.rebase", "false"], check=True)

        subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=True)
        subprocess.run(["git", "add", MOVIE_DB_FILE], check=True)

        # 🔥 Resolve any conflict forcibly
        subprocess.run(["git", "checkout", "--ours", MOVIE_DB_FILE], check=True)
        subprocess.run(["git", "add", MOVIE_DB_FILE], check=True)

        subprocess.run(["git", "commit", "-m", "🔄 Forced update movie DB"], check=True)
        subprocess.run(["git", "push", "origin", "HEAD:main", "--force"], check=True)

    except Exception as e:
        print(f"[GitHub Backup Failed] {e}")

# === TITLE EXTRACTION ===
def extract_title(text):
    text = text.replace("**", "").replace("__", "")
    patterns = [r"[🎬🔊🆕🚀📥]?\s*(title|movie|film)?\s*[:\-]?\s*([A-Za-z0-9\s\-:().,']{2,50})"]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            title = match.group(2).strip(" :-().,'").lower()
            if 2 <= len(title) <= 50:
                return title
    for line in text.splitlines():
        line = line.strip()
        if 2 <= len(line) <= 50 and any(c.isalpha() for c in line):
            return line.lower()
    return None

# === BOT SETUP ===
bot = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)
movie_db = load_db()

@bot.on_message(filters.private & filters.command("start"))
async def start_command(client, message):
    await message.reply(
        "👋 **Welcome to Movie Request Bot!**\n\n"
        "🎞️ Send any movie name to search.\n"
        "📥 If not found, it'll be uploaded in 5–6 hours.\n"
        "🧾 Use /upload_db to get movie list (admin only).\n"
        "📋 Use /uploaded_movies to see all uploaded movies.\n\n"
        "✅ Bot is active."
    )

@bot.on_message(filters.private & filters.command("upload_db"))
async def upload_db(client, message):
    try:
        await message.reply_document(MOVIE_DB_FILE, caption="📁 Movie DB backup.")
    except:
        await message.reply("❌ Failed to upload movie DB file.")

@bot.on_message(filters.private & filters.command("uploaded_movies"))
async def uploaded_movies(client, message):
    movie_list = list(movie_db.keys())
    if not movie_list:
        await message.reply("⚠️ No movies in the database.")
        return
    movie_list.sort()
    text = "**🎬 Uploaded Movies:**\n\n"
    for i, title in enumerate(movie_list, start=1):
        text += f"{i}. {title}\n"
        if len(text) > 3500:
            await message.reply(text)
            text = ""
    if text:
        await message.reply(text)

@bot.on_message(filters.private & filters.text)
async def search_movie(client, message):
    query = message.text.lower()
    found = False
    for title, info in movie_db.items():
        if query in title:
            try:
                await bot.get_messages(info["channel_id"], info["message_id"])
                for uname, link in MOVIE_CHANNELS.items():
                    try:
                        if await bot.get_chat(uname).id == info["channel_id"]:
                            t_link = f"{link}/{info['message_id']}"
                            await message.reply(f"✅ **Movie Found:**\n👉 {t_link}")
                            found = True
                            return
                    except:
                        continue
                fallback_link = f"https://t.me/c/{str(info['channel_id'])[4:]}/{info['message_id']}"
                await message.reply(f"✅ **Movie Found:**\n👉 {fallback_link}")
                found = True
                break
            except:
                await message.reply("⚠️ Movie was found in DB but has been **deleted**.")
                found = True
                break
    if not found:
        await message.reply(
            "❌ **Movie Not Found**\n\n📩 Your request has been noted.\nThe movie will be uploaded in 5–6 hours."
        )
        try:
            await bot.send_message(ALERT_CHANNEL_ID, f"❌ Not Found: `{query}`\nFrom: {message.from_user.mention}")
        except PeerIdInvalid:
            print("❗ ALERT_CHANNEL_ID invalid ya access nahi hai.")
        except Exception as e:
            print(f"[Alert Failed] {e}")

@bot.on_message(filters.channel)
async def new_channel_post(client, message):
    if message.text:
        title = extract_title(message.text)
        if not title:
            try:
                await bot.forward_messages(ALERT_CHANNEL_ID, message.chat.id, message.id)
            except:
                print("⚠️ Failed to forward unknown title.")
            return
        if title in movie_db:
            return
        movie_db[title] = {
            "channel_id": message.chat.id,
            "message_id": message.id
        }
        save_db(movie_db)
        backup_to_github()
        try:
            await bot.copy_message(FORWARD_CHANNEL_ID, message.chat.id, message.id)
        except:
            pass

async def update_from_channel(channel_id):
    async for msg in bot.get_chat_history(channel_id):
        if msg.text:
            title = extract_title(msg.text)
            if not title:
                try:
                    await bot.forward_messages(ALERT_CHANNEL_ID, channel_id, msg.id)
                except:
                    print("⚠️ Forward failed during update.")
                continue
            if title in movie_db:
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
    to_delete = []
    for title, info in movie_db.items():
        try:
            await bot.get_messages(info["channel_id"], info["message_id"])
        except (MessageIdInvalid, ChannelPrivate):
            to_delete.append(title)
    for title in to_delete:
        del movie_db[title]
    if to_delete:
        save_db(movie_db)
        backup_to_github()

async def startup_tasks():
    try:
        await bot.send_message(ALERT_CHANNEL_ID, "🔄 Bot starting... scanning all channels.")
    except:
        print("[Startup] ALERT_CHANNEL_ID unavailable.")
    for uname in MOVIE_CHANNELS:
        try:
            chat = await bot.get_chat(uname)
            await update_from_channel(chat.id)
        except Exception as e:
            print(f"[Startup] Error loading @{uname}: {e}")
            try:
                await bot.send_message(ALERT_CHANNEL_ID, f"❌ Failed: @{uname}\n`{e}`")
            except:
                pass
    await remove_deleted_posts()
    try:
        await bot.send_message(ALERT_CHANNEL_ID, "✅ Startup complete!")
    except:
        print("[Startup] Final alert failed.")

# === MAIN ===
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    async def main():
        await bot.start()
        await startup_tasks()
        await idle()
    asyncio.run(main())

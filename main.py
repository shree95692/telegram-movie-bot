import os
import json
import asyncio
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import MessageIdInvalid, ChannelPrivate

# ========== CONFIGURATION ==========
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_NAME = "my"

MOVIE_CHANNELS = {
    -1002526458211: "https://t.me/+QBp_mXI0IT0zZmVl",
    -1002397054969: "https://t.me/+xrFyWUEU5MJiMWU1"
}

ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097

MOVIE_DB_FILE = "movie_db.json"

# GitHub backup config (dummy here – will add real push in future)
GITHUB_REPO = "shree95692/movie-db-backup"
DB_FILENAME_ON_GITHUB = "movie_db.json"

# ========== FLASK SETUP ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

# ========== HELPER FUNCTIONS ==========

def load_db():
    if os.path.exists(MOVIE_DB_FILE):
        with open(MOVIE_DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(MOVIE_DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def extract_title(text):
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "title" in line.lower() or "movie" in line.lower():
            title = line.split(":", 1)[-1].strip(" 🎬-")
            if len(title) >= 2:
                return title.lower()
    return None

# ========== BOT SETUP ==========
bot = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)
movie_db = load_db()

@bot.on_message(filters.private & filters.text)
async def search_movie(client, message):
    query = message.text.lower()
    found = False
    for title, info in movie_db.items():
        if query in title:
            channel_id = info["channel_id"]
            msg_id = info["message_id"]
            try:
                invite = MOVIE_CHANNELS.get(int(channel_id), "")
                link = f"{invite}/{msg_id}" if invite else f"https://t.me/c/{str(channel_id)[4:]}/{msg_id}"
                await message.reply(f"🎬 Movie Found:\n👉 {link}")
                found = True
                break
            except Exception as e:
                await message.reply("⚠️ Error generating link.")
                found = True
                break

    if not found:
        await message.reply(
            "❌ Movie Not Found\n\nYour request has been received.\nMovie will be uploaded in 5–6 hours.\nStay tuned!"
        )
        await bot.send_message(ALERT_CHANNEL_ID, f"❌ Movie Not Found:\n\n🔍 `{query}`\nFrom: {message.from_user.mention}")

@bot.on_message(filters.command("upload_db") & filters.private)
async def manual_upload(client, message):
    try:
        await message.reply_document(MOVIE_DB_FILE, caption="📁 Current movie database backup file.")
    except Exception as e:
        await message.reply("❌ Failed to upload DB file.")

async def update_from_channel(channel_id):
    try:
        async for msg in bot.iter_history(channel_id):
            if msg.text and msg.message_id:
                title = extract_title(msg.text)
                if not title:
                    await bot.forward_messages(ALERT_CHANNEL_ID, channel_id, msg.message_id)
                    continue
                movie_db[title.lower()] = {
                    "channel_id": channel_id,
                    "message_id": msg.message_id
                }
                await bot.copy_message(FORWARD_CHANNEL_ID, channel_id, msg.message_id)
        save_db(movie_db)
    except Exception as e:
        print(f"[ERROR] Failed to read channel {channel_id}: {e}")

@bot.on_message(filters.channel)
async def new_channel_post(client, message):
    channel_id = message.chat.id
    msg_id = message.message_id
    if message.text:
        title = extract_title(message.text)
        if not title:
            await bot.forward_messages(ALERT_CHANNEL_ID, channel_id, msg_id)
            return
        movie_db[title.lower()] = {
            "channel_id": channel_id,
            "message_id": msg_id
        }
        save_db(movie_db)
        await bot.copy_message(FORWARD_CHANNEL_ID, channel_id, msg_id)

async def remove_deleted_posts():
    to_remove = []
    for title, info in movie_db.items():
        try:
            await bot.get_messages(info["channel_id"], info["message_id"])
        except (MessageIdInvalid, MessageDeleted, ChannelPrivate):
            to_remove.append(title)
    for title in to_remove:
        del movie_db[title]
    if to_remove:
        save_db(movie_db)

async def startup_tasks():
    print("🔄 Loading all channel posts...")
    for channel in MOVIE_CHANNELS:
        await update_from_channel(channel)
    await remove_deleted_posts()
    print("✅ Startup tasks complete.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

# ========== STARTUP ==========
if __name__ == "__main__":
    import threading
    threading.Thread(target=run_flask).start()
    bot.run(startup_tasks())

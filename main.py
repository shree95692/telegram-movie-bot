import os
import json
import asyncio
import threading
import re
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.errors import MessageIdInvalid, ChannelPrivate

# ========== CONFIGURATION ==========
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

# ========== FLASK SETUP ==========
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ Bot is alive!"

def run_flask():
    app.run(host="0.0.0.0", port=8000)

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
    text = text.replace("**", "").replace("__", "")
    patterns = [
        r"[🎬🔊🆕🚀📥]?\s*(title|movie|film)?\s*[:\-]?\s*([A-Za-z0-9\s\-\.]{2,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            title = match.group(2).strip(" :-().").lower()
            if title and 2 <= len(title) <= 40:
                return title

    for line in text.splitlines():
        line = line.strip()
        if 2 <= len(line) <= 40 and any(c.isalpha() for c in line):
            return line.lower()
    return None

# ========== BOT SETUP ==========
bot = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)
movie_db = load_db()

@bot.on_message(filters.private & filters.command("start"))
async def start_command(client, message):
    await message.reply(
        "\ud83d\udc4b **Welcome to Movie Request Bot!**\n\n"
        "\ud83c\udf9e\ufe0f Send any movie name to search.\n"
        "\ud83d\udcc5 If not found, it'll be uploaded in 5–6 hours.\n"
        "\ud83e\uddfe Use /upload_db to get current movie list (admin only).\n"
        "\ud83d\udccb Use /uploaded_movies to check all uploaded movies.\n\n"
        "\u2705 Bot is online."
    )

@bot.on_message(filters.private & filters.command("upload_db"))
async def upload_db(client, message):
    try:
        await message.reply_document(MOVIE_DB_FILE, caption="\ud83d\udcc1 Movie DB backup.")
    except Exception as e:
        await message.reply(f"\u274c Failed to upload movie DB file: {e}")

@bot.on_message(filters.private & filters.command("uploaded_movies"))
async def uploaded_movies(client, message):
    movie_list = list(movie_db.keys())
    if not movie_list:
        await message.reply("\u26a0\ufe0f No movies in the database.")
        return

    movie_list.sort()
    text = "**\ud83c\udfac Uploaded Movies:**\n\n"
    for i, title in enumerate(movie_list, start=1):
        text += f"{i}. {title}\n"
        if len(text) > 3800:
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
                channel_link = next(
                    (link for uname, link in MOVIE_CHANNELS.items()
                     if await bot.get_chat(uname).id == info["channel_id"]),
                    None
                )
                link = f"{channel_link}/{info['message_id']}" if channel_link else f"https://t.me/c/{str(info['channel_id'])[4:]}/{info['message_id']}"
                await message.reply(f"\ud83c\udfac **Movie Found:**\n\ud83d\udc49 {link}")
                found = True
                break
            except Exception as e:
                await message.reply("\u26a0\ufe0f Error generating movie link.")
                print(f"[Error] Movie link: {e}")
                found = True
                break
    if not found:
        await message.reply(
            "\u274c **Movie Not Found**\n\n\ud83d\udce9 Your request has been received.\nThe movie will be uploaded in 5–6 hours. Stay tuned!"
        )
        try:
            await bot.send_message(ALERT_CHANNEL_ID, f"\u274c Movie Not Found:\n\ud83d\udd0d `{query}`\nFrom: {message.from_user.mention}")
        except Exception as e:
            print(f"[Alert Failed] Not Found Alert: {e}")

@bot.on_message(filters.channel)
async def new_channel_post(client, message):
    if message.text:
        title = extract_title(message.text)
        if not title:
            try:
                await bot.forward_messages(ALERT_CHANNEL_ID, message.chat.id, message.id)
            except Exception as e:
                print(f"[Alert Failed] Forward unknown title: {e}")
            return
        movie_db[title] = {
            "channel_id": message.chat.id,
            "message_id": message.id
        }
        save_db(movie_db)
        try:
            await bot.copy_message(FORWARD_CHANNEL_ID, message.chat.id, message.id)
        except Exception as e:
            print(f"[Forward Failed] {e}")

async def update_from_channel(channel_id):
    async for msg in bot.get_chat_history(channel_id):
        if msg.text:
            title = extract_title(msg.text)
            if not title:
                try:
                    await bot.forward_messages(ALERT_CHANNEL_ID, channel_id, msg.id)
                except Exception as e:
                    print(f"[Alert Failed] Forwarding during update: {e}")
                continue
            movie_db[title] = {
                "channel_id": channel_id,
                "message_id": msg.id
            }
            try:
                await bot.copy_message(FORWARD_CHANNEL_ID, channel_id, msg.id)
            except Exception as e:
                print(f"[Forward Failed] {e}")
    save_db(movie_db)

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

async def startup_tasks():
    try:
        await bot.send_message(ALERT_CHANNEL_ID, "\ud83d\udd04 Starting up... scanning channels...")
    except Exception as e:
        print(f"[Alert Failed] Startup message: {e}")
    for uname in MOVIE_CHANNELS:
        try:
            chat = await bot.get_chat(uname)
            await update_from_channel(chat.id)
        except Exception as e:
            try:
                await bot.send_message(ALERT_CHANNEL_ID, f"\u274c Failed to read @{uname}: `{e}`")
            except Exception as e2:
                print(f"[Alert Failed] Reading @{uname}: {e2}")
    await remove_deleted_posts()
    try:
        await bot.send_message(ALERT_CHANNEL_ID, "\u2705 Startup complete!")
    except Exception as e:
        print(f"[Alert Failed] Startup complete: {e}")

# ========== MAIN ==========
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()

    async def main():
        await bot.start()
        await startup_tasks()
        await idle()

    asyncio.run(main())

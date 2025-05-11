from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import re
import json
import os
from difflib import SequenceMatcher
from unidecode import unidecode

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
OWNER_ID = 5761333274  # <-- Replace with your Telegram user ID

DB_FILE = "movie_db.json"

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        movie_db = json.load(f)
else:
    movie_db = {}

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(movie_db, f)

def clean_text(text):
    return unidecode(re.sub(r'[^a-zA-Z0-9 ]', '', text.lower().strip()))

def extract_title(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if any(k in line.lower() for k in ["title", "movie", "name", "film"]):
            parts = re.split(r"[:\-–]", line, maxsplit=1)
            if len(parts) > 1 and len(parts[1].strip()) >= 2:
                return clean_text(parts[1])
    for line in lines:
        if 1 <= len(line.split()) <= 8:
            return clean_text(line)
    return None

def is_similar(a, b, threshold=0.65):
    return SequenceMatcher(None, clean_text(a), clean_text(b)).ratio() >= threshold

# ----- Bot Commands -----

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hi! Mujhe koi bhi movie ka naam bhejo, mai dhoondhne ki koshish karunga.")

@bot.on_message(filters.command("show_db"))
async def show_db(client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("⛔ You are not authorized.")
    if not movie_db:
        return await message.reply_text("Database is empty.")
    
    response = "📦 **Movie DB:**\n"
    for i, (title, data) in enumerate(movie_db.items()):
        if isinstance(data, dict):
            channel = data.get("channel", "").strip("@")
            msg_id = data.get("msg_id")
        elif isinstance(data, list) and len(data) == 2:
            channel, msg_id = data[0].strip("@"), data[1]
        else:
            continue
        url = f"https://t.me/{channel}/{msg_id}"
        response += f"• `{title}` → [link]({url})\n"
        if i >= 19:
            response += "\n...aur bhi entries hain."
            break
    await message.reply_text(response, disable_web_page_preview=True)

# ----- Channel Posts Handler -----

@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = message.text or message.caption or ""
    chat_username = f"@{message.chat.username}" if message.chat.username else None

    if chat_username in CHANNELS:
        title = extract_title(text)
        if title and len(title) >= 2:
            movie_db[title] = {
                "channel": chat_username,
                "msg_id": message.id
            }
            save_db()
            try:
                await client.forward_messages(
                    chat_id=FORWARD_CHANNEL,
                    from_chat_id=message.chat.id,
                    message_ids=[message.id]
                )
            except Exception as e:
                await client.send_message(
                    chat_id=ALERT_CHANNEL,
                    text=f"❌ Forward failed: https://t.me/{message.chat.username}/{message.id}\n{e}"
                )
        else:
            await client.send_message(ALERT_CHANNEL, f"❗ Title not found: https://t.me/{message.chat.username}/{message.id}")
    else:
        print("Ignored post from unknown channel")

# ----- Movie Search Handler -----

@bot.on_message(filters.private & filters.text & ~filters.command(["start", "show_db"]))
async def search_movie(client, message: Message):
    query = clean_text(message.text)
    results = []

    for title, data in movie_db.items():
        if is_similar(query, title):
            if isinstance(data, dict):
                channel = data.get("channel", "").strip("@")
                msg_id = data.get("msg_id")
            elif isinstance(data, list) and len(data) == 2:
                channel, msg_id = data[0].strip("@"), data[1]
            else:
                continue
            results.append(f"https://t.me/{channel}/{msg_id}")

    if results:
        await message.reply_text("Yeh rahe matching movies:\n" + "\n".join(results))
    else:
        await message.reply_text("Sorry, koi movie nahi mili.")
        await client.send_message(ALERT_CHANNEL, f"❌ Movie nahi mili: {message.text} by {message.from_user.mention}")

# ----- Run Flask + Bot -----

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()

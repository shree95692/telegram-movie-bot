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
    if not lines:
        return None
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

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hi! Mujhe koi bhi movie ka naam bhejo, mai dhoondhne ki koshish karunga.")

@bot.on_message(filters.command("register_alert"))
async def register_alert(client, message: Message):
    try:
        await client.send_message(ALERT_CHANNEL, "✅ Alert channel registered successfully!")
        await message.reply_text("Alert channel registered.")
    except Exception as e:
        await message.reply_text(f"❌ Failed to register alert channel:\n{e}")

@bot.on_message(filters.command("init_channels"))
async def init_channels(client, message: Message):
    errors = []
    try:
        await client.send_message(FORWARD_CHANNEL, "✅ Forward channel connected.")
    except Exception as e:
        errors.append(f"❌ Forward channel error:\n{e}")
    try:
        await client.send_message(ALERT_CHANNEL, "✅ Alert channel connected.")
    except Exception as e:
        errors.append(f"❌ Alert channel error:\n{e}")
    if errors:
        await message.reply_text("\n\n".join(errors))
    else:
        await message.reply_text("✅ Both channels initialized successfully.")

@bot.on_message(filters.command("show_db"))
async def show_db(client, message: Message):
    if not movie_db:
        await message.reply_text("Database is empty.")
    else:
        lines = []
        for title, (channel, msg_id) in movie_db.items():
            link = f"https://t.me/{channel.strip('@')}/{msg_id}"
            lines.append(f"• {title} → [Link]({link})")
        text = "\n".join(lines)
        for i in range(0, len(text), 4000):  # Telegram message limit
            await message.reply_text(text[i:i+4000], disable_web_page_preview=True)

@bot.on_message(filters.text & (filters.private | filters.group))
async def search_movie(client, message: Message):
    query = clean_text(message.text)
    results = []
    for title, (channel, msg_id) in list(movie_db.items()):
        try:
            if is_similar(query, title):
                results.append(f"https://t.me/{channel.strip('@')}/{msg_id}")
        except:
            movie_db.pop(title, None)
            save_db()
    if results:
        await message.reply_text("Yeh rahe matching movies:\n" + "\n".join(results))
    else:
        await message.reply_text("Sorry, koi movie nahi mili.")
        await client.send_message(
            chat_id=ALERT_CHANNEL,
            text=f"❌ Movie nahi mili: **{message.text}**\nUser: [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        )

@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = (message.text or message.caption or "")
    chat_username = f"@{message.chat.username}"
    if chat_username in CHANNELS:
        title = extract_title(text)
        print(f"[DEBUG] Extracted title: {title}")
        if title and len(title) >= 2:
            movie_db[title] = (chat_username, message.id)
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
                    text=f"❌ Save/forward failed for: https://t.me/{message.chat.username}/{message.id}\nError: {e}"
                )
        else:
            try:
                await client.forward_messages(
                    chat_id=ALERT_CHANNEL,
                    from_chat_id=message.chat.id,
                    message_ids=[message.id]
                )
                await client.send_message(
                    chat_id=ALERT_CHANNEL,
                    text=f"❗ Title extraction failed for post: https://t.me/{message.chat.username}/{message.id}"
                )
            except Exception as e:
                await client.send_message(
                    chat_id=ALERT_CHANNEL,
                    text=f"❗ Forward + alert failed: https://t.me/{message.chat.username}/{message.id}\nError: {e}"
                )
    else:
        print("Post is from unknown channel.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()

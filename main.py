from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import re
import json
import os
import emoji
from fuzzywuzzy import process
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
    with open(DB_FILE, "r", encoding="utf-8") as f:
        movie_db = json.load(f)
else:
    movie_db = {}

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(movie_db, f)

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = emoji.replace_emoji(text, replace="")
    text = unidecode(text)
    text = re.sub(r"[^\w\s\-:\.]", "", text)
    return text.strip()

def extract_title(text):
    if not isinstance(text, str):
        return None
    text = clean_text(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    for line in lines:
        lower_line = line.lower()
        if any(k in lower_line for k in ["title", "movie", "name", "film"]):
            parts = re.split(r"[:\-–]", line, maxsplit=1)
            if len(parts) > 1 and len(parts[1].strip()) >= 2:
                return parts[1].strip().lower()

    for line in lines:
        if 1 <= len(line.split()) <= 8:
            return line.lower()

    return None

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hi! Mujhe koi bhi movie ka naam bhejo, mai dhoondhne ki koshish karunga.")

@bot.on_message(filters.command("register_alert"))
async def register_alert(client, message: Message):
    try:
        await client.send_message(ALERT_CHANNEL, "✅ Alert channel registered!")
        await message.reply_text("Alert channel registered.")
    except Exception as e:
        await message.reply_text(f"❌ Failed:\n{e}")

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

    await message.reply_text("\n\n".join(errors) if errors else "✅ Both channels initialized.")

@bot.on_message(filters.command("scan_channel"))
async def scan_channel(client, message: Message):
    await message.reply_text("Scanning channels...")
    count = 0
    skipped = 0

    for channel in CHANNELS:
        try:
            async for msg in client.get_chat_history(channel, limit=1000):
                text = (msg.text or msg.caption) or ""
                title = extract_title(text)
                if title and title not in movie_db:
                    movie_db[title] = (channel, msg.id)
                    count += 1
                else:
                    skipped += 1
        except Exception as e:
            await message.reply_text(f"Error scanning {channel}:\n{e}")

    save_db()
    await message.reply_text(f"Scan complete!\nAdded: {count}\nSkipped: {skipped}")

@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "register_alert", "init_channels", "scan_channel"]))
async def search_movie(client, message: Message):
    query = clean_text(message.text.lower())
    matches = process.extract(query, movie_db.keys(), limit=5, scorer=process.WRatio)
    valid_results = []

    for match_title, score in matches:
        if score >= 65:
            channel, msg_id = movie_db[match_title]
            try:
                msg = await client.get_messages(channel, msg_id)
                if not msg or (not msg.text and not msg.caption):
                    raise ValueError("Message deleted")
                valid_results.append(f"https://t.me/{channel.strip('@')}/{msg_id}")
            except:
                movie_db.pop(match_title, None)
                save_db()

    if valid_results:
        await message.reply_text("Yeh rahe matching movies:\n" + "\n".join(valid_results))
    else:
        await message.reply_text("Sorry, koi movie nahi mili.")
        await client.send_message(
            ALERT_CHANNEL,
            f"❌ Movie nahi mili: **{query}**\nUser: [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        )

@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = (message.text or message.caption) or ""
    chat_username = f"@{message.chat.username}" if message.chat.username else None

    if chat_username in CHANNELS:
        title = extract_title(text)
        if title:
            movie_db[title] = (chat_username, message.id)
            save_db()
            print(f"Saved: {title} -> {chat_username}/{message.id}")
            try:
                await client.forward_messages(FORWARD_CHANNEL, message.chat.id, [message.id])
            except Exception as e:
                await client.send_message(ALERT_CHANNEL, f"❗ Forward failed: https://t.me/{chat_username[1:]}/{message.id}\nError: {e}")
        else:
            print("No title extracted.")
            try:
                await client.forward_messages(ALERT_CHANNEL, message.chat.id, [message.id])
            except Exception as e:
                await client.send_message(ALERT_CHANNEL, f"❗ Title missing + forward failed:\nhttps://t.me/{chat_username[1:]}/{message.id}\nError: {e}")
    else:
        print("Unknown channel.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()

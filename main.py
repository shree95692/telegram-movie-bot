from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import re
import json
import os
import difflib
import emoji
from fuzzywuzzy import process

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
    # Remove emojis and special characters
    text = emoji.replace_emoji(text, replace='')
    text = re.sub(r"[^\w\s]", " ", text)
    return text.strip().lower()

def extract_title(text):
    if not text:
        return None

    text = clean_text(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    for line in lines:
        if any(k in line.lower() for k in ["title", "movie", "name", "film"]):
            parts = re.split(r"[:\-–]", line, maxsplit=1)
            if len(parts) > 1:
                return clean_text(parts[1])

    for line in lines:
        if 1 <= len(line.split()) <= 8:
            return clean_text(line)

    return None

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hi! Mujhe koi bhi movie ka naam bhejo, mai dhoondhne ki koshish karunga.")

@bot.on_message(filters.command("register_alert"))
async def register_alert(client, message: Message):
    try:
        await client.send_message(chat_id=ALERT_CHANNEL, text="✅ Alert channel registered successfully!")
        await message.reply_text("Alert channel registered. Forwarding should now work.")
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

@bot.on_message(filters.command("scan_channel"))
async def scan_channel(client, message: Message):
    await message.reply_text("Scanning channels... Please wait.")
    count = 0
    skipped = 0

    for channel in CHANNELS:
        try:
            async for msg in client.get_chat_history(channel, limit=1000):
                text = (msg.text or msg.caption) or ""
                title = extract_title(text)
                if title and len(title) >= 2:
                    if title not in movie_db:
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
    query = clean_text(message.text)
    if not query:
        await message.reply_text("Please send a valid movie name.")
        return

    all_titles = list(movie_db.keys())
    match, score = process.extractOne(query, all_titles) if all_titles else (None, 0)

    if match and score > 65:
        channel, msg_id = movie_db[match]
        try:
            link = f"https://t.me/{channel.strip('@')}/{msg_id}"
            await message.reply_text(f"🎬 Movie mil gayi:\n{link}")
        except:
            movie_db.pop(match, None)
            save_db()
            await message.reply_text("Movie link delete ho gaya hai.")
    else:
        await message.reply_text("Sorry, koi movie nahi mili.")
        await client.send_message(
            chat_id=ALERT_CHANNEL,
            text=f"❌ Movie nahi mili: **{query}**\nUser: [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        )

@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = (message.text or message.caption) or ""
    chat_username = f"@{message.chat.username}"

    if chat_username in CHANNELS:
        title = extract_title(text)
        if title and len(title) >= 2:
            movie_db[title] = (chat_username, message.id)
            save_db()
            print(f"Saved: {title} -> {chat_username}/{message.id}")
            try:
                await client.forward_messages(FORWARD_CHANNEL, message.chat.id, [message.id])
            except Exception as e:
                await client.send_message(ALERT_CHANNEL, f"❗ Forward failed:\nhttps://t.me/{message.chat.username}/{message.id}\nError: {e}")
        else:
            try:
                await client.forward_messages(ALERT_CHANNEL, message.chat.id, [message.id])
            except Exception as e:
                await client.send_message(ALERT_CHANNEL, f"❗ Title missing and forward failed:\nhttps://t.me/{message.chat.username}/{message.id}\nError: {e}")
    else:
        print("Unknown channel.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()

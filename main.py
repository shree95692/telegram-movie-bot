from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import asyncio
import re

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
BOT_TOKEN = "7073579407:AAG-5z0cmNFYdNlUdlJQY72F8lTmDXmXy2I"
CHANNELS = ["@stree2chaava2", "@chaava2025"]
FORWARD_CHANNEL = -1002512169097  # Correct private channel ID
movie_db = {}

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def extract_title(text):
    title_keywords = ["title", "movie name"]
    for line in text.splitlines():
        clean_line = line.strip()
        lower_line = clean_line.lower()

        # Check for keywords
        if any(keyword in lower_line for keyword in title_keywords):
            parts = re.split(r"[:\-–]", clean_line, maxsplit=1)
            if len(parts) > 1:
                possible_title = parts[1].strip()
                if len(possible_title) >= 2:
                    return possible_title.lower()

        # If line starts with emoji + short title (like 🎥 Swades)
        if re.match(r"^[\W_]+\s*[A-Za-z0-9]", clean_line) and len(clean_line.split()) <= 5:
            return clean_line.strip().lower()

    # If message has only one non-empty line
    non_empty_lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(non_empty_lines) == 1:
        return non_empty_lines[0].strip().lower()

    return None

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hello! Send me any movie name, and I will find it for you.")

@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start"]))
async def search_movie(client, message: Message):
    query = message.text.lower()
    results = []
    for title, (channel, msg_id) in movie_db.items():
        if query in title:
            results.append(f"https://t.me/{channel.strip('@')}/{msg_id}")
    if results:
        await message.reply_text("Here are the matching movies:\n" + "\n".join(results))
    else:
        await message.reply_text("Sorry, no movie found.")

@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = (message.text or message.caption) or ""
    chat_username = f"@{message.chat.username}"
    if chat_username in CHANNELS:
        title = extract_title(text)
        if title:
            movie_db[title] = (chat_username, message.id)
            print(f"Added: {title} -> {chat_username}/{message.id}")
            try:
                await client.forward_messages(
                    chat_id=FORWARD_CHANNEL,
                    from_chat_id=message.chat.id,
                    message_ids=[message.id]
                )
            except Exception as e:
                print("Forward failed:", e)
        else:
            print("No valid title found.")
    else:
        print("Post from untracked channel.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()

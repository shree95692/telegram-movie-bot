from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
from threading import Thread
import re
import json
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
BOT_TOKEN = "7073579407:AAG-5z0cmNFYdNlUdlJQY72F8lTmDXmXy2I"
CHANNELS = ["@stree2chaava2", "@chaava2025"]
FORWARD_CHANNEL = -1002512169097
ALERT_CHANNEL = -1002661392627

DB_FILE = "movie_db.json"

# Load database from JSON
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        movie_db = json.load(f)
else:
    movie_db = {}

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(movie_db, f)

# Title extract karne ke liye
def extract_title(text):
    title_keywords = ["title", "movie name"]
    for line in text.splitlines():
        clean_line = line.strip()
        lower_line = clean_line.lower()

        if any(keyword in lower_line for keyword in title_keywords):
            parts = re.split(r"[:\-–]", clean_line, maxsplit=1)
            if len(parts) > 1:
                possible_title = parts[1].strip()
                if len(possible_title) >= 2:
                    return possible_title.lower()

        if re.match(r"^[\W_]+\s*[A-Za-z0-9]", clean_line) and len(clean_line.split()) <= 5:
            return clean_line.strip().lower()

    non_empty_lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(non_empty_lines) == 1:
        return non_empty_lines[0].strip().lower()

    return None

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply_text("Hi! Mujhe koi bhi movie ka naam bhejo, mai dhoondhne ki koshish karunga.")

@bot.on_message(filters.command("register_alert"))
async def register_alert(client, message: Message):
    try:
        await client.send_message(
            chat_id=ALERT_CHANNEL,
            text="✅ Alert channel registered with bot successfully!"
        )
        await message.reply_text("Alert channel registered. Forwarding should now work.")
    except Exception as e:
        await message.reply_text(f"❌ Failed to register alert channel:\n{e}")

@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start", "register_alert"]))
async def search_movie(client, message: Message):
    query = message.text.lower()
    valid_results = []

    for title, (channel, msg_id) in list(movie_db.items()):
        try:
            msg = await client.get_messages(channel, msg_id)
            if not msg or (not msg.text and not msg.caption):
                raise ValueError("Deleted or empty message")
            if query in title:
                valid_results.append(f"https://t.me/{channel.strip('@')}/{msg_id}")
        except:
            movie_db.pop(title, None)
            save_db()

    if valid_results:
        await message.reply_text("Yeh rahe matching movies:\n" + "\n".join(valid_results))
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
        if title:
            movie_db[title] = (chat_username, message.id)
            save_db()
            print(f"Added: {title} -> {chat_username}/{message.id}")
            try:
                await client.forward_messages(
                    chat_id=FORWARD_CHANNEL,
                    from_chat_id=message.chat.id,
                    message_ids=[message.id]
                )
            except Exception as e:
                print("Forward failed:", e)
                await client.send_message(
                    chat_id=ALERT_CHANNEL,
                    text=f"❗ Failed to forward post:\nhttps://t.me/{message.chat.username}/{message.id}\nError: {e}"
                )
        else:
            print("Koi valid title nahi mila.")
            try:
                await client.forward_messages(
                    chat_id=ALERT_CHANNEL,
                    from_chat_id=message.chat.id,
                    message_ids=[message.id]
                )
            except Exception as e:
                print("Forward to alert failed:", e)
                await client.send_message(
                    chat_id=ALERT_CHANNEL,
                    text=f"❗ Title missing and forward failed:\n\nhttps://t.me/{message.chat.username}/{message.id}\nError: {e}"
                )
    else:
        print("Post is from unknown channel.")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
    page = 0
    return await send_db_page(message.chat.id, client, page)

@bot.on_callback_query()
async def paginate_db(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    if data.startswith("db_page_"):
        page = int(data.split("_")[-1])
        await send_db_page(callback_query.message.chat.id, client, page, callback_query)

async def send_db_page(chat_id, client, page, callback_query=None):
    items = list(movie_db.items())
    items_per_page = 20
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    page = max(0, min(page, total_pages - 1))
    start = page * items_per_page
    end = start + items_per_page
    entries = items[start:end]
    
    if not entries:
        text = "❌ Movie DB is empty."
    else:
        text = "**Movie DB Page {} of {}**\n\n".format(page + 1, total_pages)
        for title, (channel, msg_id) in entries:
            text += f"[{title}](https://t.me/{channel.strip('@')}/{msg_id})\n"

    buttons = []
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"db_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"db_page_{page + 1}"))
        buttons.append(nav_buttons)

    if callback_query:
        await callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        await client.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

@bot.on_message(filters.text & ~filters.command(["start", "register_alert", "init_channels", "show_db"]))
async def search_movie(client, message: Message):
    if message.chat.type not in ["private", "group", "supergroup"]:
        return
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

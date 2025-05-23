from flask import Flask
from pyrogram import Client, filters, idle
import json, os, asyncio, nest_asyncio

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_FILE = "moviebot_session.session"
ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
CHANNELS = ["stree2chaava2", "chaava2025"]
MOVIE_DB = "movies.json"
BOT_USERNAME = "Movie_request_4k_group_bot"

app = Flask(__name__)
bot = Client("moviebot", api_id=API_ID, api_hash=API_HASH, session_string=open(SESSION_FILE, "rb").read())

movie_data = {}

def extract_title(text):
    for line in text.splitlines():
        line = line.strip()
        if "title" in line.lower():
            return line.split(":")[-1].strip(" :–👉|")
    return None

def load_db():
    global movie_data
    if os.path.exists(MOVIE_DB):
        with open(MOVIE_DB, "r") as f:
            movie_data = json.load(f)
    else:
        movie_data = {}

def save_db():
    with open(MOVIE_DB, "w") as f:
        json.dump(movie_data, f, indent=2)

async def scan_all_posts():
    for channel in CHANNELS:
        try:
            async for msg in bot.get_chat_history(channel):
                if msg.text:
                    title = extract_title(msg.text)
                    if title:
                        movie_data[title.lower()] = f"https://t.me/{channel}/{msg.message_id}"
                        await bot.forward_messages(FORWARD_CHANNEL_ID, channel, msg.message_id)
                    else:
                        await bot.forward_messages(ALERT_CHANNEL_ID, channel, msg.message_id)
        except Exception as e:
            print(f"Error reading {channel}: {e}")
    save_db()

@bot.on_message(filters.private & filters.text)
async def movie_search(client, message):
    query = message.text.strip().lower()
    link = movie_data.get(query)
    if link:
        await message.reply(f"**🎬 Movie Found:**\n{link}")
    else:
        await message.reply(
            "**❌ Movie Not Found**\nYour request has been received.\nMovie will be uploaded in 5–6 hours.\nStay tuned!"
        )
        await bot.send_message(ALERT_CHANNEL_ID, f"❌ Not Found: `{message.text}` by [{message.from_user.first_name}](tg://user?id={message.from_user.id})")

@app.route("/")
def index():
    return "Bot is running!"

async def main():
    load_db()
    await bot.start()
    await scan_all_posts()
    print("Bot is ready")
    await idle()

if __name__ == "__main__":
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    app.run(host="0.0.0.0", port=8000)

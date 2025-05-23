
import os
import json
import asyncio
import aiohttp
import nest_asyncio
from flask import Flask
from pyrogram import Client, filters, idle
from datetime import datetime

# Configurations (filled with user's values)
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "BQGD828AMUcvjUw-OoeEq9vsJglHO8FPUWRDh8MGHxV5wwvSLlpwC0_lve3qdVK-7b_0mGsKD87_-6eIS-vqD5prMNL7GjosptVTESutY3kSY3E3MYl9bq8A26SUVutyBze6xDjZP_vY_uRkXjTvEe9yu3EkGgVbndao4HAhkznY_8QIseapTYs6f8AwGXk_LkOOplSE-RJR-IuOlB3WKoaPehYOSjDRhiiKVAmt9fwzTDq1cDntoOcV6EBrzBVia1TQClWX1jPaZmNQQZ96C8mpvjMfWnFVRlM8pjmI9CPbfoNNB2tO4kuEDr2BRBdlB244CC83wV80IYO66pZ5yI7IWC7FqwAAAAEzyxzAAA"

ALERT_CHANNEL_ID = -1002661392627
FORWARD_CHANNEL_ID = -1002512169097
CHANNELS = ["stree2chaava2", "chaava2025"]
BOT_USERNAME = "Movie_request_4k_group_bot"
MOVIE_DB = "movies.json"

GITHUB_REPO = "shree95692/movie-db-backup"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/movies.json"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # set in koyeb as env variable

# Flask app for Koyeb keep-alive
app = Flask(__name__)

# Pyrogram client
bot = Client(":memory:", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
movie_data = {}

# Load DB from file
def load_db():
    global movie_data
    if os.path.exists(MOVIE_DB):
        with open(MOVIE_DB, "r") as f:
            movie_data = json.load(f)
    else:
        movie_data = {}

# Save DB to file and backup to GitHub
def save_db():
    with open(MOVIE_DB, "w") as f:
        json.dump(movie_data, f, indent=2)
    asyncio.create_task(backup_to_github())

# Upload to GitHub repo
async def backup_to_github():
    if not GITHUB_TOKEN:
        print("No GitHub token found in environment.")
        return
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            with open(MOVIE_DB, "rb") as f:
                content = f.read()
            import base64
            encoded = base64.b64encode(content).decode()
            data = {
                "message": f"Backup on {datetime.utcnow().isoformat()}",
                "content": encoded
            }
            # get sha if file exists
            async with session.get(GITHUB_API_URL, headers=headers) as r:
                if r.status == 200:
                    existing = await r.json()
                    data["sha"] = existing["sha"]
            async with session.put(GITHUB_API_URL, headers=headers, json=data) as r:
                if r.status in (200, 201):
                    print("Backup successful")
                else:
                    print("Backup failed", await r.text())
    except Exception as e:
        print("GitHub backup error:", e)

# Extract title smartly
def extract_title(text):
    for line in text.splitlines():
        line = line.strip()
        if "title" in line.lower():
            return line.split(":", 1)[-1].strip(" :–👉|")
    return None

# Scan all past posts
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

# Handle deleted posts
def clean_deleted_links():
    to_delete = []
    for title, link in movie_data.items():
        msg_id = int(link.split("/")[-1])
        chat = link.split("/")[-2]
        try:
            bot.get_messages(chat, msg_id)
        except:
            to_delete.append(title)
    for title in to_delete:
        del movie_data[title]
    if to_delete:
        save_db()

# Command to check uploaded movies
@bot.on_message(filters.private & filters.command("list"))
async def list_movies(client, message):
    if movie_data:
        msg = """**Uploaded Movies:**\n"""

" + "
".join(f"- {title}" for title in list(movie_data.keys())[:30])
        await message.reply(msg)
    else:
        await message.reply("No movies in database.")

# Movie search
@bot.on_message(filters.private & filters.text)
async def movie_search(client, message):
    query = message.text.strip().lower()
    link = movie_data.get(query)
    if link:
        await message.reply(f"**🎬 Movie Found:**
{link}")
    else:
        await message.reply(
            "**❌ Movie Not Found**
Your request has been received.
Movie will be uploaded in 5–6 hours.
Stay tuned!"
        )
        await bot.send_message(
            ALERT_CHANNEL_ID,
            f"❌ Not Found: `{message.text}` by [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        )

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

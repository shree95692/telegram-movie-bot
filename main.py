import asyncio
from pyrogram import Client, filters
from flask import Flask
import threading

# ====== CONFIG ======
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "yaha_apna_session_string_dalo"  # <-- CHANGE THIS!
# ====================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# Telegram bot
bot = Client(name="movie-bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@bot.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    await message.reply_text("Hello! I'm alive.")

# Flask run (in a thread)
def run_flask():
    app.run(host="0.0.0.0", port=8000)

# Run both Flask and Telegram
def main():
    threading.Thread(target=run_flask).start()
    bot.run()

if __name__ == "__main__":
    main()

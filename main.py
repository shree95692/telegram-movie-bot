from pyrogram import Client, filters
from flask import Flask
from threading import Thread

# Telegram credentials
api_id = 25424751
api_hash = "a9f8c974b0ac2e8b5fce86b32567af6b"
bot_token = "7073579407:AAHk8xHQGaKv7xpvxgFq5_UGISwLl7NkaDM"

# Pyrogram client
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Start command handler
@app.on_message(filters.command("start"))
def start_handler(client, message):
    message.reply_text("Bot chal gaya hai! Welcome!")

# Flask app for Koyeb health check
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running fine!", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

# Flask server ko background thread mein chalao
Thread(target=run_flask).start()

# Pyrogram bot start karo
app.run()

import asyncio
import nest_asyncio
from pyrogram import Client, filters
from flask import Flask
from pyrogram.types import Message

API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
SESSION_STRING = "BQGD828AMUcvjUw-OoeEq9vsJglHO8FPUWRDh8MGHxV5wwvSLlpwC0_lve3qdVK-7b_0mGsKD87_-6eIS-vqD5prMNL7GjosptVTESutY3kSY3E3MYl9bq8A26SUVutyBze6xDjZP_vY_uRkXjTvEe9yu3EkGgVbndao4HAhkznY_8QIseapTYs6f8AwGXk_LkOOplSE-RJR-IuOlB3WKoaPehYOSjDRhiiKVAmt9fwzTDq1cDntoOcV6EBrzBVia1TQClWX1jPaZmNQQZ96C8mpvjMfWnFVRlM8pjmI9CPbfoNNB2tO4kuEDr2BRBdlB244CC83wV80IYO66pZ5yI7IWC7FqwAAAAEzyxzAAA"

# Flask for keep-alive
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive"

# Pyrogram client
bot = Client(":memory:", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Reply to /start
@bot.on_message(filters.private & filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text("Hello! Bot is working.")

async def main():
    await bot.start()
    print("Bot started")
    await asyncio.Event().wait()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().create_task(main())
    app.run(host="0.0.0.0", port=8000)

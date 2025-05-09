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
FORWARD_CHANNEL = -1002512169097  # सुनिश्चित करें कि बॉट इस चैनल का सदस्य है
ALERT_CHANNEL = -1002661392627    # सुनिश्चित करें कि बॉट इस चैनल का सदस्य है
movie_db = {}

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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
    await message.reply_text("Hi! Send me any movie name and I will try to find it for you.")
@bot.on_message((filters.private | filters.group) & filters.text & ~filters.command(["start"]))
async def search_movie(client, message: Message):
    query = message.text.lower()
    valid_results = []

    for title, (channel, msg_id) in list(movie_db.items()):
    if query in title:
        try:
            for title, (channel, msg_id) in list(movie_db.items()):
    if query in title:
        try:
            await client.get_messages(channel, msg_id)
            valid_results.append(f"https://t.me/{channel.strip('@')}/{msg_id}")
        except:
            movie_db.pop(title, None)
    if valid_results:
        await message.reply_text("Here are the matching movies:\n" + "\n".join(valid_results))
    else:
        await message.reply_text("माफ़ कीजिए, कोई मूवी नहीं मिली।")
        await client.send_message(
            chat_id=ALERT_CHANNEL,
            text=f"❌ मूवी नहीं मिली: **{query}**\nउपयोगकर्ता: [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        )

@bot.on_message(filters.channel)
async def new_post(client, message: Message):
    text = (message.text or message.caption) or ""
    chat_username = f"@{message.chat.username}"

    if chat_username in CHANNELS:
        title = extract_title(text)
        if title:
            movie_db[title] = (chat_username, message.id)
            print(f"जोड़ा गया: {title} -> {chat_username}/{message.id}")
            try:
                await client.forward_messages(
                    chat_id=FORWARD_CHANNEL,
                    from_chat_id=message.chat.id,
                    message_ids=[message.id]
                )
                # पुष्टि संदेश भेजें
                await client.send_message(
                    chat_id=FORWARD_CHANNEL,
                    text=f"✅ नई मूवी जोड़ी गई: {title}\nलिंक: https://t.me/{message.chat.username}/{message.id}"
                )
            except Exception as e:
                print("अग्रेषण विफल:", e)
                await client.send_message(
                    chat_id=ALERT_CHANNEL,
                    text=f"❗ पोस्ट अग्रेषित करने में विफल:\nhttps://t.me/{message.chat.username}/{message.id}\nत्रुटि: {e}"
                )
        else:
            print("कोई वैध शीर्षक नहीं मिला।")
            await client.send_message(
                chat_id=ALERT_CHANNEL,
                text=f"❗ पोस्ट में शीर्षक नहीं मिला:\n\nhttps://t.me/{message.chat.username}/{message.id}"
            )
    else:
        print("अज्ञात चैनल से पोस्ट।")

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()

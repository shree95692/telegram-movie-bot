from pyrogram import Client, filters

api_id = 25424751  # <-- aapka sahi API ID
api_hash = "a9f8c974b0ac2e8b5fce86b32567af6b"  # <-- aapka sahi API Hash
bot_token = "7073579407:AAHk8xHQGaKv7xpvxgFq5_UGISwLl7NkaDM"

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

@app.on_message(filters.command("start"))
def start_handler(client, message):
    message.reply_text("Bot chal gaya hai! Welcome!")

app.run(host="0.0.0.0", port=8000)

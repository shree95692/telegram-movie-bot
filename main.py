from pyrogram import Client, filters

# Yahan apna bot token daalo
BOT_TOKEN = "7073579407:AAHk8xHQGaKv7xpvxgFq5_UGISwLl7NkaDM"

app = Client("simple_bot", bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
def start(client, message):
    message.reply_text("Bot chal raha hai! Aapka swagat hai.")

app.run()

import logging
from telethon.sync import TelegramClient, events

# Configuration
API_ID = 25424751
API_HASH = "a9f8c974b0ac2e8b5fce86b32567af6b"
BOT_TOKEN = "7073579407:AAE0ZnyAMKG1rtkYxMWwHwKOHtEBRQmsU3k"
CHANNEL_USERNAME = "@stree2chaava2"

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Start the bot client
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.respond("Welcome! Send me a movie name to search.")
    raise events.StopPropagation

@bot.on(events.NewMessage)
async def movie_search(event):
    query = event.raw_text.lower()
    async for message in bot.iter_messages(CHANNEL_USERNAME, search=query):
        await event.respond(f"Found:\n{message.text}")
        break
    else:
        await event.respond("No results found.")

def start_bot():
    logger.info("Bot is starting...")
    bot.run_until_disconnected()

if __name__ == "__main__":
    start_bot()


import logging
from telethon.sync import TelegramClient, events

# Configuration
API_ID = 12345678  # Replace with your actual API ID
API_HASH = "your_api_hash_here"  # Replace with your actual API hash
BOT_TOKEN = "your_bot_token_here"  # Replace with your bot token
CHANNEL_USERNAME = "@yourchannelusername"  # Replace with your channel username

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
        await event.respond(f"Found:
{message.text}")
        break
    else:
        await event.respond("No results found.")

def start_bot():
    logger.info("Bot is starting...")
    bot.run_until_disconnected()

if __name__ == "__main__":
    start_bot()


import logging
from telethon import TelegramClient, events

API_ID = 27024115
API_HASH = 'b2f6828b24c5f9a2f0bbd822f60f6e75'
BOT_TOKEN = '6591877193:AAH6B7jeHwV2OLRMhcGl0v_baOytnTuSKGI'
CHANNEL_USERNAME = 'stree2chaava2'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("Send a movie name to search!")

@bot.on(events.NewMessage)
async def search(event):
    query = event.raw_text
    async for message in bot.iter_messages(CHANNEL_USERNAME, search=query, limit=5):
        try:
            await event.reply(f"[Link to Post](https://t.me/stree2chaava2/{message.id})", link_preview=False)
        except Exception as e:
            logger.error(e)

logger.info("Bot is starting...")
bot.run_until_disconnected()


import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "7073579407:AAE0ZnyAMKG1rtkYxMWwHwKOHtEBRQmsU3k"
CHANNEL_USERNAME = "stree2chaava2"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Movie bot activated. Send a movie name to search.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.message.text.lower()
    # Dummy sample post IDs for example
    movie_data = {
        "saithan": 10,
        "sathan": 10,
        "saithan 2023": 10,
        "hindi saithan": 10
    }
    for key, post_id in movie_data.items():
        if key in query:
            await update.message.reply_text(f"https://t.me/jatt_kesari/{post_id}")
            return
    await update.message.reply_text("Movie not found.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

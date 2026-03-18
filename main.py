from telegram.ext import Application, CommandHandler, MessageHandler, filters as tg_filters
from bot.handlers import handle_start, handle_reset, handle_message
from bot.filters import OWNER_FILTER
from config import TELEGRAM_BOT_TOKEN
from utils.logger import logger

def main():
    logger.info("Starting agent...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start, filters=OWNER_FILTER))
    app.add_handler(CommandHandler("help",  handle_start, filters=OWNER_FILTER))
    app.add_handler(CommandHandler("reset", handle_reset, filters=OWNER_FILTER))
    app.add_handler(MessageHandler(OWNER_FILTER & tg_filters.TEXT, handle_message))

    logger.info("Bot polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

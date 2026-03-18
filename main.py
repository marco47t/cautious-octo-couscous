from telegram.ext import Application, CommandHandler, MessageHandler, filters as tg_filters
from bot.handlers import handle_start, handle_reset, handle_reminders, handle_message
from bot.filters import OWNER_FILTER
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scheduler.manager import init as init_scheduler, start as start_scheduler
from utils.logger import logger

async def post_init(app: Application):
    """Called after the event loop is running — safe to start AsyncIOScheduler here."""
    init_scheduler(app.bot, TELEGRAM_CHAT_ID)
    start_scheduler()
    logger.info("Scheduler initialized.")

def main():
    logger.info("Starting agent...")
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)        # ← scheduler starts here, inside the loop
        .build()
    )

    app.add_handler(CommandHandler("start",     handle_start,     filters=OWNER_FILTER))
    app.add_handler(CommandHandler("help",      handle_start,     filters=OWNER_FILTER))
    app.add_handler(CommandHandler("reset",     handle_reset,     filters=OWNER_FILTER))
    app.add_handler(CommandHandler("reminders", handle_reminders, filters=OWNER_FILTER))
    app.add_handler(MessageHandler(OWNER_FILTER & tg_filters.TEXT, handle_message))

    logger.info("Bot polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

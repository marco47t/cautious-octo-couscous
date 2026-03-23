import traceback
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters as tg_filters, ContextTypes
)
from bot.handlers import (
    handle_start, handle_reset, handle_reminders,
    handle_status, handle_message, handle_callback
)
from bot.media_handlers import handle_photo, handle_document, handle_voice
from bot.filters import OWNER_FILTER
from bot.proactive import init_proactive, register_proactive_jobs
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scheduler.manager import init as init_scheduler, start as start_scheduler
from utils.logger import logger

async def post_init(app: Application):
    init_scheduler(app.bot, TELEGRAM_CHAT_ID)
    init_proactive(app.bot)
    start_scheduler()
    register_proactive_jobs()
    logger.info("Scheduler + proactive jobs initialized.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {context.error}", exc_info=context.error)
    tb = "".join(traceback.format_exception(
        type(context.error), context.error, context.error.__traceback__
    ))
    if update and hasattr(update, "message") and update.message:
        await update.message.reply_text(
            f"❌ Error:\n<code>{tb[-1000:]}</code>", parse_mode="HTML"
        )

def main():
    logger.info("Starting agent...")
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start",     handle_start,     filters=OWNER_FILTER))
    app.add_handler(CommandHandler("help",      handle_start,     filters=OWNER_FILTER))
    app.add_handler(CommandHandler("reset",     handle_reset,     filters=OWNER_FILTER))
    app.add_handler(CommandHandler("reminders", handle_reminders, filters=OWNER_FILTER))
    app.add_handler(CommandHandler("status",    handle_status,    filters=OWNER_FILTER))

    # Text + media
    app.add_handler(MessageHandler(OWNER_FILTER & tg_filters.TEXT, handle_message))
    app.add_handler(MessageHandler(OWNER_FILTER & tg_filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(OWNER_FILTER & tg_filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(OWNER_FILTER & (tg_filters.VOICE | tg_filters.AUDIO), handle_voice))

    # Inline button callbacks (no user filter needed — callbacks include user info)
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.add_error_handler(error_handler)

    logger.info("Bot polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

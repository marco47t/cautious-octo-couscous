from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from agent.core import process_message
from agent.memory import clear_session
from utils.logger import logger

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Personal AI Agent Online*\n\n"
        "I can:\n🔍 Search the web\n📁 Find & send files from your PC\n"
        "📧 Read & send emails\n💬 Answer anything\n\n"
        "/reset — clear conversation memory",
        parse_mode="Markdown"
    )

async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_session(update.effective_user.id)
    await update.message.reply_text("🔄 Memory cleared. Fresh start!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    logger.info(f"[{user_id}] {text[:80]}")

    await context.bot.send_chat_action(chat_id, "typing")
    response_text, files = await process_message(user_id, text, chat_id)

    # Split long messages
    for i in range(0, max(len(response_text), 1), 4096):
        await update.message.reply_text(
            response_text[i:i+4096], parse_mode="Markdown"
        )

    # Send queued files
    for file_path in files:
        path = Path(file_path)
        try:
            await context.bot.send_chat_action(chat_id, "upload_document")
            await context.bot.send_document(
                chat_id, document=open(path, "rb"),
                filename=path.name, caption=f"📎 {path.name}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Could not send {path.name}: {e}")

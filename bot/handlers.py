import asyncio
from pathlib import Path
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from agent.core import process_message_stream, pop_pending_files
from agent.memory import clear_session
from tools.system_tool import get_system_info
from utils.md_to_html import md_to_html
from utils.logger import logger

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>🤖 Personal AI Agent Online</b>\n\n"
        "I can:\n🔍 Search the web\n📁 Find &amp; manage server files\n"
        "📧 Read &amp; send emails\n⏰ Schedule reminders\n"
        "🖼️ Analyze images &amp; documents\n🎤 Transcribe voice messages\n"
        "🖥️ Monitor server stats\n💻 Run whitelisted shell commands\n\n"
        "/reset — clear conversation memory\n"
        "/reminders — list pending reminders\n"
        "/status — server resource usage",
        parse_mode="HTML"
    )

async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_session(update.effective_user.id)
    await update.message.reply_text("🔄 Memory cleared. Fresh start!")

async def handle_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from tools.scheduler_tool import list_reminders
    await update.message.reply_text(md_to_html(list_reminders()), parse_mode="HTML")

async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(md_to_html(get_system_info()), parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    logger.info(f"[{user_id}] {text[:80]}")

    await context.bot.send_chat_action(chat_id, "typing")
    placeholder: Message = await update.message.reply_text("⏳ <i>Thinking...</i>", parse_mode="HTML")
    final_text = ""
    try:
        async for partial in process_message_stream(user_id, text, chat_id):
            final_text = partial
        await _safe_edit(placeholder, final_text or "✅ Done.")
    except Exception as e:
        logger.error(f"Handler error: {e}")
        await _safe_edit(placeholder, f"❌ Error: {e}")

    for file_path in pop_pending_files(chat_id):
        path = Path(file_path)
        try:
            await context.bot.send_chat_action(chat_id, "upload_document")
            await context.bot.send_document(
                chat_id, document=open(path, "rb"),
                filename=path.name, caption=f"📎 {path.name}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Could not send {path.name}: {e}")

async def _safe_edit(message: Message, text: str):
    try:
        await message.edit_text(md_to_html(text)[:4096], parse_mode="HTML")
    except BadRequest as e:
        if "can't parse" in str(e).lower():
            # Last resort: strip all tags and send plain
            import html
            try:
                await message.edit_text(text[:4096], parse_mode=None)
            except BadRequest as e2:
                if "not modified" not in str(e2).lower():
                    logger.warning(f"Edit failed: {e2}")
        elif "not modified" not in str(e).lower():
            logger.warning(f"Edit failed: {e}")

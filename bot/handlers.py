import asyncio
from pathlib import Path
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from agent.core import process_message_stream, pop_pending_files
from agent.memory import clear_session
from utils.logger import logger

EDIT_INTERVAL = 0.8  # seconds between Telegram message edits

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "🤖 *Personal AI Agent Online*\n\n"
            "I can:\n🔍 Search the web\n📁 Find & send files from your PC\n"
            "📧 Read & send emails\n⏰ Schedule reminders\n\n"
            "/reset — clear conversation memory\n"
            "/reminders — list pending reminders",
            parse_mode="Markdown"
        )
    except BadRequest:
        await update.message.reply_text(
            "🤖 Personal AI Agent Online\n\n"
            "Commands: /reset, /reminders"
        )


async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_session(update.effective_user.id)
    await update.message.reply_text("🔄 Memory cleared. Fresh start!")

async def handle_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from tools.scheduler_tool import list_reminders
    await update.message.reply_text(list_reminders(), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    logger.info(f"[{user_id}] {text[:80]}")

    await context.bot.send_chat_action(chat_id, "typing")

    # Send a placeholder message to edit in-place as stream arrives
    placeholder: Message = await update.message.reply_text("⏳ _Thinking..._", parse_mode="Markdown")

    last_edit = asyncio.get_event_loop().time()
    final_text = ""

    try:
        async for partial in process_message_stream(user_id, text, chat_id):
            final_text = partial
            now = asyncio.get_event_loop().time()
            if now - last_edit >= EDIT_INTERVAL:
                await _safe_edit(placeholder, partial + " ▌")
                last_edit = now

        # Final edit — clean, no cursor
        await _safe_edit(placeholder, final_text or "✅ Done.")

    except Exception as e:
        logger.error(f"Handler error: {e}")
        await _safe_edit(placeholder, f"❌ Error: {e}")

    # Send any files queued by the file_sender tool
    for file_path in pop_pending_files(chat_id):
        path = Path(file_path)
        try:
            await context.bot.send_chat_action(chat_id, "upload_document")
            await context.bot.send_document(
                chat_id,
                document=open(path, "rb"),
                filename=path.name,
                caption=f"📎 {path.name}",
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Could not send {path.name}: {e}")


async def _safe_edit(message: Message, text: str):
    try:
        await message.edit_text(text[:4096], parse_mode="Markdown")
    except BadRequest as e:
        if "can't parse" in str(e).lower() or "parse entities" in str(e).lower():
            # Fallback: send as plain text if markdown is malformed
            try:
                await message.edit_text(text[:4096], parse_mode=None)
            except BadRequest as e2:
                if "not modified" not in str(e2).lower():
                    logger.warning(f"Edit failed even without markdown: {e2}")
        elif "not modified" not in str(e).lower():
            logger.warning(f"Edit failed: {e}")

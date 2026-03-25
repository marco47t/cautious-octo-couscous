import re
import asyncio
from pathlib import Path
from telegram import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from agent.core import process_message_stream, pop_pending_files
from agent.memory import clear_session
from bot.confirmation import execute_action, cancel_action, cleanup_pending
from tools.system_tool import get_system_info
from utils.md_to_html import md_to_html
from utils.logger import logger
from tools.confirmation_handler import get_confirmation_keyboard, handle_tool_confirmation

CONFIRM_PATTERN = re.compile(r"CONFIRM_ID:([a-f0-9]+)")
TOOL_CONFIRM_PATTERN = re.compile(r"\|\|CONFIRMTOOLCREATION:(\d+)\|\|")
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>🤖 Personal AI Agent Online</b>\n\n"
        "I can:\n🔍 Search the web\n📁 Manage server files\n"
        "📧 Read &amp; send emails (with confirmation)\n"
        "⏰ Schedule reminders\n🖼️ Analyze images &amp; documents\n"
        "🎤 Transcribe voice messages\n🖥️ Monitor server stats\n"
        "💻 Run shell commands (with confirmation)\n\n"
        "/reset — clear conversation\n"
        "/reminders — list pending reminders\n"
        "/status — server health",
        parse_mode="HTML"
    )

async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_session(update.effective_user.id)
    cleanup_pending()
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
    placeholder: Message = await update.message.reply_text(
        "⏳ <i>Thinking...</i>", parse_mode="HTML"
    )

    final_text = ""
    try:
        async for partial in process_message_stream(user_id, text, chat_id):
            final_text = partial
    except Exception as e:
        logger.error(f"Handler error: {e}")
        await _safe_edit(placeholder, f"❌ Error: {e}")
        return

    # Check if response contains a confirmation request
    tool_match = TOOL_CONFIRM_PATTERN.search(final_text)
    confirm_match = CONFIRM_PATTERN.search(final_text)

    if tool_match:
        user_id_str = tool_match.group(1)
        display_text = TOOL_CONFIRM_PATTERN.sub("", final_text).strip()
        try:
            await placeholder.edit_text(
                display_text[:4096],
                parse_mode="HTML",
                reply_markup=get_confirmation_keyboard(int(user_id_str))
            )
        except BadRequest:
            await placeholder.edit_text(
                display_text[:4096],
                reply_markup=get_confirmation_keyboard(int(user_id_str)))

    elif confirm_match:
        action_id = confirm_match.group(1)
        display_text = CONFIRM_PATTERN.sub("", final_text).strip()
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Yes, proceed", callback_data=f"confirm:{action_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{action_id}"),
        ]])
        try:
            await placeholder.edit_text(
                md_to_html(display_text)[:4096],
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except BadRequest:
            await placeholder.edit_text(display_text[:4096], reply_markup=keyboard)

    else:
        await _safe_edit(placeholder, final_text or "✅ Done.")

    # Send queued files
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

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Yes/No button presses for confirmations."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("tool_confirm:"):
        await handle_tool_confirmation(update, context)

    elif data.startswith("confirm:"):
        action_id = data.split(":", 1)[1]
        result = execute_action(action_id)
        await query.edit_message_text(md_to_html(result)[:4096], parse_mode="HTML")

    elif data.startswith("cancel:"):
        action_id = data.split(":", 1)[1]
        result = cancel_action(action_id)
        await query.edit_message_text(md_to_html(result)[:4096], parse_mode="HTML")

async def _safe_edit(message: Message, text: str):
    try:
        await message.edit_text(md_to_html(text)[:4096], parse_mode="HTML")
    except BadRequest as e:
        if "can't parse" in str(e).lower():
            try:
                await message.edit_text(text[:4096], parse_mode=None)
            except BadRequest as e2:
                if "not modified" not in str(e2).lower():
                    logger.warning(f"Edit failed: {e2}")
        elif "not modified" not in str(e).lower():
            logger.warning(f"Edit failed: {e}")

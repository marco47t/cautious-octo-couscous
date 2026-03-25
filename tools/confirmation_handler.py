from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from tools.tool_builder import (
    _pending_confirmations, _write_and_load, DYNAMIC_DIR
)
from pathlib import Path
from utils.logger import logger


def get_confirmation_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yes, allow", callback_data=f"tool_confirm:yes:{user_id}"),
        InlineKeyboardButton("❌ No, cancel", callback_data=f"tool_confirm:no:{user_id}"),
    ]])


async def handle_tool_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, choice, user_id_str = query.data.split(":")
    user_id = int(user_id_str)

    if user_id not in _pending_confirmations:
        await query.edit_message_text("⚠️ This confirmation has expired.")
        return

    pending = _pending_confirmations.pop(user_id)
    function_name = pending["function_name"]
    task_description = pending["task_description"]
    code = pending["code"]

    if choice == "no":
        await query.edit_message_text(f"❌ Tool <code>{function_name}</code> creation cancelled.", parse_mode="HTML")
        return

    # User said yes — write and load
    tool_path = DYNAMIC_DIR / f"{function_name}.py"
    result = _write_and_load(function_name, task_description, code, tool_path)
    await query.edit_message_text(result, parse_mode="HTML")
    logger.info(f"[confirmation_handler] User {user_id} approved tool: {function_name}")

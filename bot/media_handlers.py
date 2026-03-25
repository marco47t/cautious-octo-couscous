import os
import html
import asyncio
import tempfile
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL
from agent.core import process_message_stream, pop_pending_files
from bot.handlers import _safe_edit, TOOL_CONFIRM_PATTERN
from tools.confirmation_handler import get_confirmation_keyboard
from utils.md_to_html import md_to_html
from utils.logger import logger


_client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_UNSUPPORTED = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
    "application/x-zip-compressed",
}

UNSUPPORTED_EXTENSIONS = {".pptx", ".ppt", ".xlsx", ".xls", ".zip"}

TEXT_EXTENSIONS = {".py", ".js", ".ts", ".md", ".csv", ".json", ".yaml", ".yml",
                   ".txt", ".html", ".css", ".sh"}


async def _download(bot, file_id: str, suffix: str, persistent: bool = False) -> str:
    """Download a Telegram file to disk.
    If persistent=True, saves to /tmp with a stable name (not deleted after use).
    """
    tg_file = await bot.get_file(file_id)
    if persistent:
        # Use file_unique_id-based name so it's stable and findable
        save_path = f"/tmp/{file_id}{suffix}"
        await tg_file.download_to_drive(save_path)
        return save_path
    else:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        await tg_file.download_to_drive(tmp.name)
        return tmp.name


async def _agent_reply(update, context, user_id, chat_id, message, status="⏳ <i>Thinking...</i>"):
    placeholder = await update.message.reply_text(status, parse_mode="HTML")
    final_text = ""
    async for partial in process_message_stream(user_id, message, chat_id):
        final_text = partial

    # Same pattern check as handle_message to avoid double HTML escaping
    tool_match = TOOL_CONFIRM_PATTERN.search(final_text)
    if tool_match:
        user_id_str = tool_match.group(1)
        display_text = TOOL_CONFIRM_PATTERN.sub("", final_text).strip()
        try:
            await placeholder.edit_text(
                display_text[:4096],
                parse_mode="HTML",
                reply_markup=get_confirmation_keyboard(int(user_id_str))
            )
        except Exception:
            await placeholder.edit_text(display_text[:4096],
                reply_markup=get_confirmation_keyboard(int(user_id_str)))
    else:
        await _safe_edit(placeholder, final_text or "✅ Done.")

    for fp in pop_pending_files(chat_id):
        p = Path(fp)
        try:
            await context.bot.send_document(chat_id, document=open(p, "rb"), filename=p.name)
        except Exception as e:
            await update.message.reply_text(f"❌ Could not send {p.name}: {e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    question = update.message.caption or "Describe this image in detail."
    await context.bot.send_chat_action(chat_id, "typing")
    path = None
    try:
        photo = update.message.photo[-1]
        path = await _download(context.bot, photo.file_id, ".jpg")
        uploaded = _client.files.upload(file=path, config={"mime_type": "image/jpeg"})
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[uploaded, question]
        )
        text = response.text or "Could not analyze image."
        await update.message.reply_text(md_to_html(text)[:4096], parse_mode="HTML")
    except Exception as e:
        logger.error(f"Photo handler error: {e}")
        await update.message.reply_text(f"❌ Could not process image: {e}")
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    doc = update.message.document
    caption = update.message.caption or ""
    suffix = Path(doc.file_name or "file").suffix.lower() or ".bin"
    mime = doc.mime_type or "application/octet-stream"

    await context.bot.send_chat_action(chat_id, "typing")

    is_unsupported = mime in GEMINI_UNSUPPORTED or suffix in UNSUPPORTED_EXTENSIONS

    # Persistent = file must survive after this function returns
    path = None
    try:
        path = await _download(
            context.bot, doc.file_id, suffix,
            persistent=is_unsupported   # ← key fix: don't use tempfile for these
        )
        logger.info(f"[media] Saved: {path} ({doc.file_name}, {mime})")

        if suffix in TEXT_EXTENSIONS or mime.startswith("text/"):
            content = Path(path).read_text(encoding="utf-8", errors="replace")[:8000]
            message = f"{caption}\n\nFile: `{doc.file_name}`\n\n```\n{content}\n```"
            await _agent_reply(update, context, user_id, chat_id, message,
                               "⏳ <i>Reading file...</i>")

        elif is_unsupported:
            if not caption:
                # No instruction given — just report the path, don't invoke agent
                await update.message.reply_text(
                    f"📎 <b>File saved</b>\n\n"
                    f"Path: <code>{path}</code>\n"
                    f"Name: {doc.file_name}\n\n"
                    f"What would you like me to do with it?",
                    parse_mode="HTML"
                )
            else:
                # User gave explicit instruction — pass to agent with path
                user_message = (
                    f"{caption}\n\n"
                    f"File saved at: {path}\n"
                    f"Original name: {doc.file_name}\n"
                    f"MIME type: {mime}"
                ).strip()
                await _agent_reply(update, context, user_id, chat_id, user_message,
                                   "⏳ <i>Processing document...</i>")

        else:
            uploaded = _client.files.upload(file=path, config={"mime_type": mime})
            response = _client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[uploaded, caption or "Summarize this document."]
            )
            await update.message.reply_text(
                md_to_html(response.text or "Could not process.")[:4096],
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Document handler error: {e}")
        await update.message.reply_text(f"❌ Could not process document: {e}")

    finally:
        # Only delete temp files — persistent files stay for agent tools to use
        if path and os.path.exists(path) and not is_unsupported:
            os.unlink(path)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    await context.bot.send_chat_action(chat_id, "typing")
    path = None
    try:
        voice = update.message.voice or update.message.audio
        path = await _download(context.bot, voice.file_id, ".ogg")
        uploaded = _client.files.upload(file=path, config={"mime_type": "audio/ogg"})
        transcription_resp = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[uploaded, "Transcribe this audio exactly as spoken. Return only the transcribed text, nothing else."]
        )
        transcription = (transcription_resp.text or "").strip()
        if not transcription:
            await update.message.reply_text("❌ Could not transcribe audio.")
            return
        await update.message.reply_text(
            f"🎤 <i>{html.escape(transcription)}</i>", parse_mode="HTML"
        )
        await _agent_reply(update, context, user_id, chat_id, transcription)
    except Exception as e:
        logger.error(f"Voice handler error: {e}")
        await update.message.reply_text(f"❌ Could not process voice message: {e}")
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

import os
import html
import tempfile
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL
from agent.core import process_message_stream, pop_pending_files
from bot.handlers import _safe_edit
from utils.md_to_html import md_to_html
from utils.logger import logger

_client = genai.Client(api_key=GEMINI_API_KEY)

async def _download(bot, file_id: str, suffix: str) -> str:
    tg_file = await bot.get_file(file_id)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    await tg_file.download_to_drive(tmp.name)
    return tmp.name

async def _agent_reply(update, context, user_id, chat_id, message: str, status: str = "⏳ <i>Thinking...</i>"):
    placeholder = await update.message.reply_text(status, parse_mode="HTML")
    final_text = ""
    async for partial in process_message_stream(user_id, message, chat_id):
        final_text = partial
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

TEXT_EXTENSIONS = {".py", ".js", ".ts", ".md", ".csv", ".json", ".yaml", ".yml", ".txt", ".html", ".css", ".sh"}

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    doc = update.message.document
    caption = update.message.caption or "Summarize this document."
    suffix = Path(doc.file_name or "file").suffix.lower() or ".bin"
    await context.bot.send_chat_action(chat_id, "typing")
    path = None
    try:
        path = await _download(context.bot, doc.file_id, suffix)
        if suffix in TEXT_EXTENSIONS or (doc.mime_type or "").startswith("text/"):
            content = Path(path).read_text(encoding="utf-8", errors="replace")[:8000]
            message = f"{caption}\n\nFile: `{doc.file_name}`\n\n```\n{content}\n```"
            await _agent_reply(update, context, user_id, chat_id, message, "⏳ <i>Reading file...</i>")
        else:
            mime = doc.mime_type or "application/octet-stream"
            uploaded = _client.files.upload(file=path, config={"mime_type": mime})
            response = _client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[uploaded, caption]
            )
            await update.message.reply_text(md_to_html(response.text or "Could not process.")[:4096], parse_mode="HTML")
    except Exception as e:
        logger.error(f"Document handler error: {e}")
        await update.message.reply_text(f"❌ Could not process document: {e}")
    finally:
        if path and os.path.exists(path):
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
        await update.message.reply_text(f"🎤 <i>{html.escape(transcription)}</i>", parse_mode="HTML")
        await _agent_reply(update, context, user_id, chat_id, transcription)
    except Exception as e:
        logger.error(f"Voice handler error: {e}")
        await update.message.reply_text(f"❌ Could not process voice message: {e}")
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

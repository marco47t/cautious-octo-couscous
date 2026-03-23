from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from telegram import Bot
from utils.logger import logger

jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///scheduler.db")}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")

_bot: Bot = None
_chat_id: int = 0

def init(bot: Bot, chat_id: int):
    global _bot, _chat_id
    _bot = bot
    _chat_id = chat_id

async def _fire_reminder(message: str):
    if _bot and _chat_id:
        await _bot.send_message(_chat_id, f"⏰ <b>Reminder:</b> {message}", parse_mode="HTML")

def start():
    scheduler.start()
    logger.info("Scheduler started")

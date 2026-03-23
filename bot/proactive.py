import psutil
import imaplib
import email
from email.header import decode_header as _dh
from datetime import datetime
from telegram import Bot
from config import (
    TELEGRAM_CHAT_ID,
    WATCHDOG_CPU_THRESHOLD, WATCHDOG_RAM_THRESHOLD, WATCHDOG_DISK_THRESHOLD,
    EMAIL_ADDRESS, EMAIL_APP_PASSWORD,
    BRIEFING_HOUR, BRIEFING_MINUTE, BRIEFING_TIMEZONE,
)
from scheduler.manager import scheduler
from utils.logger import logger
from utils.md_to_html import md_to_html

_bot: Bot = None

def init_proactive(bot: Bot):
    global _bot
    _bot = bot

async def _send(text: str):
    if _bot and TELEGRAM_CHAT_ID:
        await _bot.send_message(TELEGRAM_CHAT_ID, md_to_html(text), parse_mode="HTML")

# ── Watchdog ─────────────────────────────────────────────────────────────────

async def watchdog_check():
    """Runs every 5 minutes — alerts if any resource exceeds threshold."""
    try:
        alerts = []
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        if cpu > WATCHDOG_CPU_THRESHOLD:
            alerts.append(f"🔴 **CPU spike**: {cpu}% (threshold: {WATCHDOG_CPU_THRESHOLD}%)")
        if ram.percent > WATCHDOG_RAM_THRESHOLD:
            alerts.append(f"🔴 **RAM high**: {ram.percent}% used (threshold: {WATCHDOG_RAM_THRESHOLD}%)")
        if disk.percent > WATCHDOG_DISK_THRESHOLD:
            alerts.append(f"🔴 **Disk full**: {disk.percent}% used (threshold: {WATCHDOG_DISK_THRESHOLD}%)")

        if alerts:
            msg = "⚠️ **Server Alert**\n\n" + "\n".join(alerts)
            await _send(msg)
            logger.warning(f"[watchdog] Alerts sent: {alerts}")
    except Exception as e:
        logger.error(f"[watchdog] Error: {e}")

# ── Daily Briefing ───────────────────────────────────────────────────────────

def _unread_email_count() -> int:
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com")
        m.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        m.select("INBOX")
        _, data = m.search(None, "UNSEEN")
        m.logout()
        return len(data[0].split()) if data[0] else 0
    except Exception:
        return -1

async def daily_briefing():
    """Sends a morning briefing: server health, reminders, emails."""
    try:
        from scheduler.manager import scheduler as sched
        from tools.system_tool import get_system_info

        now = datetime.now()
        day = now.strftime("%A, %B %d, %Y")

        # Server health
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        server_status = "🟢 Healthy" if cpu < 60 and ram.percent < 75 else "🟡 Under load"

        # Pending reminders
        jobs = sched.get_jobs()
        reminder_count = len(jobs)

        # Unread emails
        unread = _unread_email_count()
        email_str = f"{unread} unread" if unread >= 0 else "unavailable"

        msg = (
            f"☀️ **Good morning! Daily Briefing — {day}**\n\n"
            f"🖥️ Server: {server_status} "
            f"(CPU: {cpu}% | RAM: {ram.percent}% | Disk: {disk.percent}%)\n"
            f"⏰ Pending reminders: {reminder_count}\n"
            f"📧 Emails: {email_str}\n\n"
            f"_Reply with anything to get started._"
        )
        await _send(msg)
        logger.info("[briefing] Daily briefing sent")
    except Exception as e:
        logger.error(f"[briefing] Error: {e}")

def register_proactive_jobs():
    """Register watchdog and briefing in the scheduler."""
    import zoneinfo

    # Watchdog: every 5 minutes
    scheduler.add_job(
        watchdog_check,
        trigger="interval",
        minutes=5,
        id="watchdog",
        replace_existing=True,
    )
    logger.info("[proactive] Watchdog registered (every 5 min)")

    # Daily briefing
    tz = zoneinfo.ZoneInfo(BRIEFING_TIMEZONE)
    scheduler.add_job(
        daily_briefing,
        trigger="cron",
        hour=BRIEFING_HOUR,
        minute=BRIEFING_MINUTE,
        timezone=tz,
        id="daily_briefing",
        replace_existing=True,
    )
    logger.info(f"[proactive] Daily briefing registered ({BRIEFING_HOUR:02d}:{BRIEFING_MINUTE:02d} {BRIEFING_TIMEZONE})")

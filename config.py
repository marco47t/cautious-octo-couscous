import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
PC_SEARCH_ROOTS = [p for p in os.getenv("PC_SEARCH_ROOTS", "").split(",") if p]
WATCHDOG_CPU_THRESHOLD = int(os.getenv("WATCHDOG_CPU_THRESHOLD", "80"))
WATCHDOG_RAM_THRESHOLD = int(os.getenv("WATCHDOG_RAM_THRESHOLD", "85"))
WATCHDOG_DISK_THRESHOLD = int(os.getenv("WATCHDOG_DISK_THRESHOLD", "90"))
BRIEFING_HOUR = int(os.getenv("BRIEFING_HOUR", "7"))
BRIEFING_MINUTE = int(os.getenv("BRIEFING_MINUTE", "0"))
BRIEFING_TIMEZONE = os.getenv("BRIEFING_TIMEZONE", "Africa/Cairo")

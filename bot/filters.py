from telegram.ext import filters
from config import TELEGRAM_ALLOWED_USER_ID

OWNER_FILTER = filters.User(user_id=TELEGRAM_ALLOWED_USER_ID)

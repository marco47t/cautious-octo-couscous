import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    logger = logging.getLogger("TelegramAgent")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)

    file_handler = RotatingFileHandler("agent.log", maxBytes=5*1024*1024, backupCount=3)
    file_handler.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    logger = logging.getLogger("TelegramAgent")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console — INFO and above only (keep terminal clean)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    # File — DEBUG and above (full detail)
    file_handler = RotatingFileHandler(
        "agent.log", maxBytes=10*1024*1024, backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

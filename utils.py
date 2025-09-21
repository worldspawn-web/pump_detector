import logging
import os
from datetime import datetime

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """Настройка логгера для записи в файл и консоль."""
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)

    return logger

# Создаём директорию логов, если не существует
os.makedirs("logs", exist_ok=True)

# Глобальный логгер
logger = setup_logger("pump_bot", f"logs/pump_bot_{datetime.now().strftime('%Y%m%d')}.log")
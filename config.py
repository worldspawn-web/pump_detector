import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# MEXC
MEXC_SYMBOL_FILTER = "USDT"
PUMP_THRESHOLD_PERCENT = 7.0
PUMP_WINDOW_MINUTES = 10  # последние 10 минут
MIN_VOLUME_USDT = 300_000  # игнорировать монеты с объёмом < 300K

# Paths
LOG_DIR = "logs"
PLOT_DIR = "plots"

# Blacklist
BLACKLIST_FILE = "blacklist.json"
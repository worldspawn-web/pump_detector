import requests
import os
from dotenv import load_dotenv

load_dotenv()


class TelegramAlert:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
        try:
            response = requests.post(url, data=payload)
            return response.json().get("result")
        except Exception as e:
            print(f"[!] Failed to send Telegram message: {e}")
            return None

    def delete_message(self, message_id):
        url = f"https://api.telegram.org/bot{self.bot_token}/deleteMessage"
        payload = {"chat_id": self.chat_id, "message_id": message_id}
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"[!] Failed to delete message: {e}")

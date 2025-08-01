import requests


class TelegramAlert:
    def __init__(self):
        self.bot_token = "8053760674:AAF1peKjF_1yMd07npJU20lw9Ai1sfNYcR0"
        self.chat_id = "-1002503106999"

    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"[!] Failed to send Telegram message: {e}")

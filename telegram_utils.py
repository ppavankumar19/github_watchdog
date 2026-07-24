"""
telegram_utils.py
Sends the report as a message via the Telegram Bot API.
Telegram messages are capped at 4096 characters, so long reports are chunked.
"""

import requests

TELEGRAM_API = "https://api.telegram.org"
MAX_LEN = 4000  # leave headroom under Telegram's 4096 limit


def send_telegram_report(report_text: str, bot_token: str, chat_id: str):
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"

    chunks = [report_text[i:i + MAX_LEN] for i in range(0, len(report_text), MAX_LEN)] or [report_text]

    for chunk in chunks:
        resp = requests.post(url, data={"chat_id": chat_id, "text": chunk}, timeout=15)
        resp.raise_for_status()

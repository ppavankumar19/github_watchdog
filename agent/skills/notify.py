"""
agent/skills/notify.py

NotifySkill: fires email + Telegram after report is approved.
Wraps email_utils and telegram_utils so the agent core stays clean.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from email_utils import send_email_report
from telegram_utils import send_telegram_report


class NotifySkill:
    def run(self, report: str):
        send_email_report(
            report,
            gmail_address=os.getenv("GMAIL_ADDRESS"),
            gmail_app_password=os.getenv("GMAIL_APP_PASSWORD"),
            recipient=os.getenv("REPORT_RECIPIENT_EMAIL"),
        )

        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if bot_token and chat_id and not bot_token.startswith("your_"):
            send_telegram_report(report, bot_token=bot_token, chat_id=chat_id)
        else:
            print("      [Telegram] skipped — bot token / chat ID not configured.")

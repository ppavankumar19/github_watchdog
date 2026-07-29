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
    def run(self, report: str, student_count: int = 0, ok_count: int = 0) -> dict:
        """Returns {"email": bool, "telegram": bool} indicating delivery results."""
        email_ok = True
        try:
            send_email_report(
                report,
                gmail_address=os.getenv("GMAIL_ADDRESS"),
                gmail_app_password=os.getenv("GMAIL_APP_PASSWORD"),
                recipient=os.getenv("REPORT_RECIPIENT_EMAIL"),
                student_count=student_count,
                ok_count=ok_count,
            )
        except Exception as exc:
            email_ok = False
            print(f"      [Email] FAILED: {exc}")

        telegram_ok = False
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if bot_token and chat_id and not bot_token.startswith("your_"):
            telegram_text = report
            if not email_ok:
                telegram_text = "[Note: Email delivery failed — Telegram only]\n\n" + report
            try:
                send_telegram_report(telegram_text, bot_token=bot_token, chat_id=chat_id)
                telegram_ok = True
            except Exception as exc:
                print(f"      [Telegram] FAILED: {exc}")
        else:
            print("      [Telegram] skipped — bot token / chat ID not configured.")

        return {"email": email_ok, "telegram": telegram_ok}

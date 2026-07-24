"""
email_utils.py
Sends the report via Gmail SMTP using an App Password.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date


def send_email_report(report_text: str, gmail_address: str, gmail_app_password: str, recipient: str):
    msg = MIMEMultipart()
    msg["From"] = gmail_address
    msg["To"] = recipient
    msg["Subject"] = f"GitHub Activity Report - {date.today().isoformat()}"

    msg.attach(MIMEText(report_text, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, recipient, msg.as_string())

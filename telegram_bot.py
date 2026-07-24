"""
telegram_bot.py — Telegram bot handler for GitHub Watchdog.

Supported interactions:
  /start, /help   — usage instructions
  /status         — last run time + student count
  /students       — list current students
  /run            — trigger an agent run (background thread)
  <CSV file>      — upload a .csv file to replace students.csv

Modes:
  Polling  — used locally (no public URL needed)
  Webhook  — used on Render/production (set APP_URL env var)
"""

import csv
import io
import json
import os
import threading
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent
TELEGRAM_API = "https://api.telegram.org"


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _csv_path() -> Path:
    return ROOT / os.getenv("STUDENTS_CSV_PATH", "students.csv")


def _data_dir() -> Path:
    return Path(os.getenv("DATA_DIR") or ROOT)


# ── outbound helpers ──────────────────────────────────────────────────────────

def send_message(chat_id, text: str):
    requests.post(
        f"{TELEGRAM_API}/bot{_token()}/sendMessage",
        data={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def set_webhook(app_url: str):
    """Register the webhook URL with Telegram. Call once on production startup."""
    token = _token()
    if not token or token.startswith("your_"):
        return
    url = f"{app_url.rstrip('/')}/telegram/webhook"
    r = requests.post(
        f"{TELEGRAM_API}/bot{token}/setWebhook",
        data={"url": url},
        timeout=10,
    )
    print(f"[bot] Webhook registered: {url} — {r.json().get('description')}")


def delete_webhook():
    """Remove webhook so polling can work (local dev)."""
    token = _token()
    if token and not token.startswith("your_"):
        requests.post(f"{TELEGRAM_API}/bot{token}/deleteWebhook", timeout=10)


# ── update handler ────────────────────────────────────────────────────────────

def handle_update(update: dict):
    """Entry point — called by both webhook route and polling thread."""
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return

    # CSV file upload
    document = message.get("document")
    if document:
        fname = document.get("file_name", "")
        if fname.lower().endswith(".csv"):
            _handle_csv(chat_id, document["file_id"])
        else:
            send_message(chat_id, "Please send a .csv file with columns: name, repo_url")
        return

    # Text commands
    text = (message.get("text") or "").strip()
    if text in ("/start", "/help"):
        send_message(chat_id, (
            "GitHub Watchdog Bot\n\n"
            "Commands:\n"
            "/status   — last run info\n"
            "/students — list tracked students\n"
            "/run      — trigger a report now\n\n"
            "To update students, send a CSV file:\n"
            "name,repo_url\n"
            "Alice,https://github.com/alice/repo"
        ))
    elif text == "/status":
        _handle_status(chat_id)
    elif text == "/students":
        _handle_students(chat_id)
    elif text == "/run":
        _handle_run(chat_id)
    else:
        send_message(chat_id, "Unknown command. Send /help for usage.")


# ── command handlers ──────────────────────────────────────────────────────────

def _handle_csv(chat_id, file_id: str):
    token = _token()
    # Get Telegram file path
    r = requests.get(f"{TELEGRAM_API}/bot{token}/getFile", params={"file_id": file_id}, timeout=10)
    file_path = r.json().get("result", {}).get("file_path")
    if not file_path:
        send_message(chat_id, "Could not download file.")
        return

    # Download content
    r = requests.get(f"{TELEGRAM_API}/file/bot{token}/{file_path}", timeout=15)
    try:
        content = r.content.decode("utf-8-sig")  # handle BOM from Excel exports
    except UnicodeDecodeError:
        content = r.content.decode("latin-1")

    # Validate columns
    reader = csv.DictReader(io.StringIO(content))
    fields = set(reader.fieldnames or [])
    if not {"name", "repo_url"}.issubset(fields):
        send_message(chat_id, "CSV must have 'name' and 'repo_url' columns.\nFound: " + ", ".join(fields or []))
        return

    # Parse rows
    students = [
        {"name": row["name"].strip(), "repo_url": row["repo_url"].strip()}
        for row in reader
        if row.get("name", "").strip() and row.get("repo_url", "").strip()
    ]

    if not students:
        send_message(chat_id, "No valid rows found in CSV.")
        return

    # Write students.csv
    with open(_csv_path(), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "repo_url"])
        writer.writeheader()
        writer.writerows(students)

    send_message(chat_id, f"✅ Updated! {len(students)} student(s) loaded.\nSend /students to confirm.")


def _handle_status(chat_id):
    state_file = _data_dir() / "state.json"
    if not state_file.exists():
        send_message(chat_id, "No runs recorded yet. Send /run to start.")
        return
    state = json.loads(state_file.read_text())
    last_run = state.get("last_run", "unknown")
    count = len(state.get("students", {}))
    send_message(chat_id, f"Last run: {last_run}\nTracking {count} student(s).")


def _handle_students(chat_id):
    csv_path = _csv_path()
    if not csv_path.exists():
        send_message(chat_id, "No students.csv found. Upload a CSV file.")
        return
    with open(csv_path, newline="", encoding="utf-8") as f:
        students = [r for r in csv.DictReader(f) if r.get("name")]
    if not students:
        send_message(chat_id, "students.csv is empty.")
        return
    lines = [f"{i+1}. {s['name']}\n   {s['repo_url']}" for i, s in enumerate(students)]
    send_message(chat_id, f"Tracking {len(students)} student(s):\n\n" + "\n\n".join(lines))


def _handle_run(chat_id):
    send_message(chat_id, "Starting agent run... this may take a minute.")

    def _run():
        try:
            from agent.core import GitHubWatchdogAgent
            from store import save_report
            agent = GitHubWatchdogAgent()
            result = agent.run()
            save_report(result["report"], result["student_count"], result["ok_count"])
            send_message(chat_id, f"✅ Run complete.\n{result['ok_count']}/{result['student_count']} students active.\n\nReport sent to email.")
        except Exception as exc:
            send_message(chat_id, f"❌ Run failed: {exc}")

    threading.Thread(target=_run, daemon=True).start()


# ── polling (local dev) ───────────────────────────────────────────────────────

def start_polling():
    """Run a long-poll loop in a background thread. Use for local dev only."""
    token = _token()
    if not token or token.startswith("your_"):
        print("[bot] No token — polling not started.")
        return

    delete_webhook()  # polling and webhook can't coexist

    def _loop():
        offset = 0
        print("[bot] Polling started.")
        while True:
            try:
                r = requests.get(
                    f"{TELEGRAM_API}/bot{token}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                    timeout=35,
                )
                for update in r.json().get("result", []):
                    handle_update(update)
                    offset = update["update_id"] + 1
            except Exception as e:
                print(f"[bot] Polling error: {e}")
                time.sleep(5)

    threading.Thread(target=_loop, daemon=True).start()

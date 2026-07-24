"""
app.py — Flask web application for GitHub Watchdog.

Routes:
  GET  /                   Dashboard
  GET  /reports            Report history
  GET  /reports/<id>       Single report
  GET  /students           Student management
  GET  /settings           Config / env status

API:
  GET  /api/status         Agent status + memory summary
  GET  /api/students       List students (JSON)
  POST /api/students       Add student
  DELETE /api/students     Remove student by name
  GET  /api/run/stream     SSE — runs agent live, streams logs
  GET  /api/reports        Report list (JSON)
  GET  /api/next-run       Next scheduled run time
"""

import csv
import json
import os
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    stream_with_context,
)

load_dotenv()

ROOT = Path(__file__).parent
STUDENTS_CSV = ROOT / os.getenv("STUDENTS_CSV_PATH", "students.csv")
_DATA_DIR = Path(os.getenv("DATA_DIR") or ROOT)
MEMORY_STATE = _DATA_DIR / "state.json"

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")

# ── run-lock: only one agent run at a time ──────────────────────────────────
_run_lock = threading.Lock()
_is_running = False

# ── scheduler ────────────────────────────────────────────────────────────────
from scheduler import init_scheduler, get_next_run

# ── helpers ──────────────────────────────────────────────────────────────────

REQUIRED_ENV = [
    "NVIDIA_API_KEY",
    "GMAIL_ADDRESS",
    "GMAIL_APP_PASSWORD",
    "REPORT_RECIPIENT_EMAIL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


OPTIONAL_ENV = ["GITHUB_TOKEN"]  # improves rate limits but not required for public repos

def _env_status() -> list[dict]:
    rows = []
    for key in REQUIRED_ENV:
        val = os.getenv(key, "")
        masked = val[:4] + "***" + val[-3:] if len(val) > 8 else ("***" if val else None)
        rows.append({"key": key, "set": bool(val), "masked": masked, "optional": False})
    for key in OPTIONAL_ENV:
        val = os.getenv(key, "")
        masked = val[:4] + "***" + val[-3:] if len(val) > 8 else ("***" if val else None)
        rows.append({"key": key, "set": bool(val), "masked": masked, "optional": True})
    return rows


def _load_memory_state() -> dict:
    if MEMORY_STATE.exists():
        with open(MEMORY_STATE) as f:
            return json.load(f)
    return {"last_run": None, "students": {}}


def _read_csv() -> list[dict]:
    if not STUDENTS_CSV.exists():
        return []
    with open(STUDENTS_CSV, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("name") and r.get("repo_url")]


def _write_csv(students: list[dict]):
    with open(STUDENTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "repo_url"])
        writer.writeheader()
        writer.writerows(students)


# ── Page routes ──────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    state = _load_memory_state()
    students_raw = _read_csv()

    # Enrich with memory data
    students = []
    for s in students_raw:
        mem = state.get("students", {}).get(s["name"], {})
        days = mem.get("days_since_commit")
        if days is None:
            status = "unknown"
        elif days == 0:
            status = "green"
        elif days <= 2:
            status = "yellow"
        else:
            status = "red"
        students.append({
            **s,
            "days_since": days,
            "streak": mem.get("streak_days", 0),
            "last_message": mem.get("last_message", "—"),
            "last_date": mem.get("last_date", "—"),
            "status": status,
        })

    from store import list_reports
    recent_reports = list_reports(limit=5)

    return render_template(
        "index.html",
        students=students,
        last_run=state.get("last_run"),
        next_run=get_next_run(),
        recent_reports=recent_reports,
        is_running=_is_running,
    )


@app.route("/reports")
def reports_page():
    from store import list_reports
    return render_template("reports.html", reports=list_reports())


@app.route("/reports/<report_id>")
def report_detail(report_id):
    from store import get_report
    report = get_report(report_id)
    if not report:
        return "Report not found", 404
    return render_template("report_detail.html", report=report)


@app.route("/students")
def students_page():
    return render_template("students.html", students=_read_csv())


@app.route("/settings")
def settings_page():
    return render_template(
        "settings.html",
        env_status=_env_status(),
        schedule_time=os.getenv("SCHEDULE_TIME", "08:00"),
        next_run=get_next_run(),
        model=os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b"),
    )


# ── API routes ────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    state = _load_memory_state()
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    return jsonify({
        "ready": len(missing) == 0,
        "missing_env": missing,
        "last_run": state.get("last_run"),
        "next_run": get_next_run(),
        "is_running": _is_running,
        "student_count": len(_read_csv()),
    })


@app.route("/api/students", methods=["GET"])
def api_students_get():
    return jsonify(_read_csv())


@app.route("/api/students", methods=["POST"])
def api_students_add():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    repo_url = (data.get("repo_url") or "").strip()
    if not name or not repo_url:
        return jsonify({"error": "name and repo_url required"}), 400
    students = _read_csv()
    if any(s["name"] == name for s in students):
        return jsonify({"error": "Student already exists"}), 409
    students.append({"name": name, "repo_url": repo_url})
    _write_csv(students)
    return jsonify({"ok": True}), 201


@app.route("/api/students", methods=["DELETE"])
def api_students_delete():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    students = [s for s in _read_csv() if s["name"] != name]
    _write_csv(students)
    return jsonify({"ok": True})


@app.route("/api/reports")
def api_reports():
    from store import list_reports
    return jsonify(list_reports())


@app.route("/api/next-run")
def api_next_run():
    return jsonify({"next_run": get_next_run()})


@app.route("/api/students/upload", methods=["POST"])
def api_students_upload():
    """Accept a CSV file upload and replace students.csv."""
    f = request.files.get("file")
    if not f or not f.filename.endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file"}), 400

    try:
        content = f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        content = f.read().decode("latin-1")

    import io as _io
    reader = csv.DictReader(_io.StringIO(content))
    fields = set(reader.fieldnames or [])
    if not {"name", "repo_url"}.issubset(fields):
        return jsonify({"error": f"CSV must have 'name' and 'repo_url' columns. Found: {', '.join(fields)}"}), 400

    students = [
        {"name": row["name"].strip(), "repo_url": row["repo_url"].strip()}
        for row in reader
        if row.get("name", "").strip() and row.get("repo_url", "").strip()
    ]
    if not students:
        return jsonify({"error": "No valid rows found in CSV"}), 400

    _write_csv(students)
    return jsonify({"ok": True, "count": len(students)})


EDITABLE_ENV_KEYS = [
    "NVIDIA_API_KEY", "NVIDIA_MODEL",
    "GITHUB_TOKEN",
    "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "REPORT_RECIPIENT_EMAIL",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "SCHEDULE_TIME", "SECRET_KEY",
]

def _read_env_file() -> dict:
    env_path = ROOT / ".env"
    vals = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, _, v = s.partition("=")
                    vals[k.strip()] = v.strip()
    return vals

def _write_env_file(updates: dict):
    env_path = ROOT / ".env"
    lines = []
    written = set()
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k = s.split("=", 1)[0].strip()
                    if k in updates:
                        lines.append(f"{k}={updates[k]}\n")
                        written.add(k)
                        continue
                lines.append(line if line.endswith("\n") else line + "\n")
    for k, v in updates.items():
        if k not in written:
            lines.append(f"{k}={v}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
    for k, v in updates.items():
        os.environ[k] = v


@app.route("/api/env", methods=["GET"])
def api_env_get():
    current = _read_env_file()
    SECRET_KEYS = {"NVIDIA_API_KEY", "GMAIL_APP_PASSWORD", "TELEGRAM_BOT_TOKEN", "SECRET_KEY"}
    result = []
    for key in EDITABLE_ENV_KEYS:
        val = current.get(key, "")
        result.append({
            "key": key,
            "value": val,
            "secret": key in SECRET_KEYS,
        })
    return jsonify(result)


@app.route("/api/env", methods=["POST"])
def api_env_update():
    data = request.get_json(force=True) or {}
    updates = {k: v for k, v in data.items() if k in EDITABLE_ENV_KEYS and isinstance(v, str)}
    if not updates:
        return jsonify({"error": "No valid keys provided"}), 400
    _write_env_file(updates)
    return jsonify({"ok": True, "updated": list(updates.keys())})


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    """Receives updates from Telegram when webhook is active (production)."""
    from telegram_bot import handle_update
    handle_update(request.get_json(force=True) or {})
    return "ok"


@app.route("/api/run/stream")
def api_run_stream():
    """SSE endpoint — runs the agent and streams log lines to the browser."""
    global _is_running

    def generate():
        global _is_running

        if _is_running:
            yield "data: Agent is already running. Refresh in a moment.\n\n"
            yield "event: done\ndata: busy\n\n"
            return

        if not _run_lock.acquire(blocking=False):
            yield "data: Could not acquire run lock.\n\n"
            yield "event: done\ndata: locked\n\n"
            return

        _is_running = True
        log_q: queue.Queue = queue.Queue()
        result_box: list[dict] = []

        def agent_thread():
            try:
                from agent.core import GitHubWatchdogAgent
                agent = GitHubWatchdogAgent()
                result = agent.run(log_fn=lambda msg: log_q.put(msg))
                result_box.append(result)
            except Exception as exc:
                log_q.put(f"ERROR: {exc}")
            finally:
                log_q.put(None)  # sentinel

        t = threading.Thread(target=agent_thread, daemon=True)
        t.start()

        try:
            while True:
                try:
                    msg = log_q.get(timeout=120)
                except queue.Empty:
                    yield "data: [timeout — agent took too long]\n\n"
                    break
                if msg is None:
                    break
                # Escape SSE: replace newlines within a message
                safe = msg.replace("\n", " ↵ ")
                yield f"data: {safe}\n\n"

            # Save report if we got one
            if result_box:
                from store import save_report
                r = result_box[0]
                rid = save_report(r["report"], r["student_count"], r["ok_count"])
                yield f"event: report_id\ndata: {rid}\n\n"

        finally:
            _is_running = False
            _run_lock.release()

        yield "event: done\ndata: complete\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ── startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    is_debug = os.getenv("FLASK_ENV") != "production"

    # Flask debug reloader forks 2 processes; only start background threads in the real one.
    # WERKZEUG_RUN_MAIN=true is set in the child (actual server) process.
    in_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    should_start_bg = (not is_debug) or in_reloader_child

    if should_start_bg:
        init_scheduler()
        app_url = os.getenv("APP_URL") or os.getenv("RENDER_EXTERNAL_URL")
        if app_url:
            from telegram_bot import set_webhook
            set_webhook(app_url)
        else:
            from telegram_bot import start_polling
            start_polling()

    app.run(host="0.0.0.0", port=port, debug=is_debug)

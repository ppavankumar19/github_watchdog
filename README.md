# GitHub Watchdog Agent

Reads a CSV of students + their public GitHub repos, checks each one's latest commit,
uses an LLM to turn that into a readable report, and sends it by **email** and **Telegram**.
Can run as a scheduled CLI job or via the built-in **web UI** (Flask).

---

## Quick Start

```bash
cd github_watchdog
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then fill in your values
```

## Environment Variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `NVIDIA_API_KEY` | Yes | NVIDIA NIM API key |
| `NVIDIA_MODEL` | No | Model to use (default: `nvidia/nemotron-3-ultra-550b-a55b`) |
| `GITHUB_TOKEN` | Recommended | GitHub personal access token — raises rate limit from 60 to 5000 req/hour |
| `GMAIL_ADDRESS` | Yes | Gmail address to send reports from |
| `GMAIL_APP_PASSWORD` | Yes | Gmail App Password (requires 2FA enabled) |
| `REPORT_RECIPIENT_EMAIL` | Yes | Where to send the daily report |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Optional | Your Telegram chat ID |
| `SECRET_KEY` | Yes (web) | Flask session secret |
| `PORT` | No | Web UI port (default: 5000) |
| `SCHEDULE_TIME` | No | Daily run time in HH:MM UTC (default: 08:00) |
| `DATA_DIR` | No | Directory for state.json, memory.md, reports/ (default: project root) |

**Get a GITHUB_TOKEN:** https://github.com/settings/tokens — classic token, no scopes needed for public repos.
**Get GMAIL_APP_PASSWORD:** Enable 2FA on Google, then: https://myaccount.google.com/apppasswords

## Add Students (`students.csv`)

```csv
name,repo_url
Alice Sharma,https://github.com/alice/my-project
Bob Verma,https://github.com/bob/my-project
```

You can also manage students via the web UI or by sending a CSV file to your Telegram bot.

---

## Run Options

### Option A — CLI (one-off or cron)

```bash
venv/bin/python main.py
```

Cron example (daily 8 AM):
```
0 8 * * * cd /path/to/github_watchdog && venv/bin/python main.py >> run.log 2>&1
```

### Option B — Web UI

```bash
venv/bin/python app.py
# Open http://localhost:5000
```

Features: dashboard, live agent run with log stream, report history, student management, settings editor.
The scheduler runs the agent automatically at `SCHEDULE_TIME` each day.

### Option C — Render (production)

Deploy via `render.yaml`. Set secrets in the Render dashboard Environment tab. A persistent disk at `/data` stores state.json, memory.md, and reports.

---

## Project Structure

```
github_watchdog/
├── main.py                  # CLI entrypoint
├── app.py                   # Flask web UI + API
├── scheduler.py             # APScheduler daily job
├── store.py                 # saves/reads report JSON files
├── telegram_bot.py          # Telegram bot (polling + webhook)
│
├── agent/
│   ├── core.py              # 6-step agent loop
│   ├── memory_manager.py    # state.json + memory.md management
│   └── skills/
│       ├── fetch.py         # reads students.csv + calls GitHub API
│       ├── report.py        # generates report via NVIDIA NIM
│       ├── reflect.py       # self-QA pass before sending
│       └── notify.py        # sends email + Telegram
│
├── github_utils.py          # GitHub API helper
├── email_utils.py           # Gmail SMTP helper
├── telegram_utils.py        # Telegram Bot API helper
│
├── memory/
│   ├── soul.md              # agent identity (edit to change personality)
│   ├── behaviors.md         # edge-case rules
│   └── memory.md            # auto-generated run log (human-readable)
│
├── prompts/
│   ├── report.md            # report generation prompt (edit for style changes)
│   └── reflect.md           # QA prompt
│
├── students.csv             # student list
├── state.json               # machine-readable run state (auto-generated)
├── requirements.txt
├── render.yaml              # Render deployment config
└── .env                     # secrets (never commit)
```

## Agent Loop (6 steps)

1. **Fetch** — reads `students.csv`, pulls latest commit from GitHub for each student
2. **Context** — loads prior run history from `state.json`
3. **Report** — sends data to NVIDIA NIM LLM, generates formatted plain-text report
4. **Reflect** — LLM self-QA pass; flags hallucinations or missing data before sending
5. **Notify** — sends report via Gmail + Telegram (email failure still tries Telegram)
6. **Remember** — updates `state.json` and regenerates `memory.md`

## Notes

- `GITHUB_TOKEN` is optional but strongly recommended — unauthenticated calls are capped at 60/hour (2 calls per student = 30 students max before hitting the limit).
- To change the report style, edit `prompts/report.md` — no Python changes needed.
- To change agent personality or decision rules, edit `memory/soul.md` and `memory/behaviors.md`.
- `llm_utils.py` is a legacy file kept for reference — it is not used by the agent.

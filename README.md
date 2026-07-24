# GitHub Watchdog Agent

Reads a CSV of students + their public GitHub repos, checks each one's latest commit,
uses Claude to turn that into a readable report, and sends it to you by **email** and
**Telegram**. Meant to run on a schedule (cron).

## 1. Setup

```bash
cd github_watchdog
python3 -m venv venv
source venv/bin/activate          # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Now edit `.env` and fill in:

| Variable | How to get it |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |
| `GITHUB_TOKEN` (optional but recommended) | https://github.com/settings/tokens — classic token, no scopes needed for public repos. Avoids GitHub's low rate limit for unauthenticated requests. |
| `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` | Enable 2FA on your Google account, then create an App Password: https://myaccount.google.com/apppasswords |
| `REPORT_RECIPIENT_EMAIL` | Usually the same as `GMAIL_ADDRESS` (send to yourself) |
| `TELEGRAM_BOT_TOKEN` | Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` |
| `TELEGRAM_CHAT_ID` | Message your new bot once, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser — your chat id is in the JSON response under `message.chat.id` |

## 2. Fill in students.csv

```csv
name,repo_url
Alice Sharma,https://github.com/octocat/Hello-World
Bob Verma,https://github.com/octocat/Spoon-Knife
```

## 3. Run it manually to test

```bash
python3 main.py
```

You should see the report printed to console, an email land in your inbox, and a
Telegram message from your bot.

## 4. Schedule it with cron (daily at 8 AM example)

```bash
crontab -e
```

Add this line (adjust the path):

```
0 8 * * * cd /full/path/to/github_watchdog && /full/path/to/github_watchdog/venv/bin/python3 main.py >> run.log 2>&1
```

- `0 8 * * *` = every day at 08:00. For weekly (e.g. every Monday 9 AM): `0 9 * * 1`
- Use `venv/bin/python3` (or your venv's python) so it runs with installed dependencies.
- `>> run.log 2>&1` keeps a log file so you can debug if a run fails silently.

## Project structure

```
github_watchdog/
├── main.py             # orchestrator — run this
├── github_utils.py     # fetches latest commit from GitHub API
├── llm_utils.py        # Claude turns raw commit data into a report
├── email_utils.py       # sends report via Gmail SMTP
├── telegram_utils.py    # sends report via Telegram Bot API
├── students.csv         # your input: name, repo_url
├── requirements.txt
├── .env.example          # copy to .env and fill in secrets
└── README.md
```

## Notes / things you may want to extend later

- Currently reports the **latest commit only**. To report "commits since last run",
  you'd store the last-seen SHA per student (e.g. in a small JSON/SQLite file) and
  diff against it each run.
- `GITHUB_TOKEN` is optional but strongly recommended — unauthenticated GitHub API
  calls are capped at 60 requests/hour per IP, which you'll hit fast with a large class.
- Model used is `claude-sonnet-4-6` in `llm_utils.py` — change `MODEL` there if you want
  a different one.
- Secrets live only in `.env` (already gitignored via convention) — never commit that file.

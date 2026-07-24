"""
agent/core.py

GitHubWatchdogAgent — the agent's main loop.

Run order:
  1. Load soul (identity) + memory (prior context)
  2. Fetch: pull latest commits for all students
  3. Report: generate plain-text report grounded in soul + memory
  4. Reflect: self-QA the report before sending
  5. Notify: email + Telegram
  6. Remember: update memory with today's data
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
MEMORY_DIR = ROOT / "memory"

REQUIRED_ENV = [
    "NVIDIA_API_KEY",
    "GMAIL_ADDRESS",
    "GMAIL_APP_PASSWORD",
    "REPORT_RECIPIENT_EMAIL",
]
# Telegram is optional — if either var is missing, notifications are skipped
TELEGRAM_ENV = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]


class GitHubWatchdogAgent:
    def __init__(self):
        self._check_env()
        self._load_identity()
        self._init_skills()

    # ------------------------------------------------------------------ #
    # Initialisation                                                       #
    # ------------------------------------------------------------------ #

    def _check_env(self):
        missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
        if missing:
            print(f"[agent] Missing env vars: {', '.join(missing)}", file=sys.stderr)
            print("[agent] Copy .env.example to .env and fill in the values.", file=sys.stderr)
            sys.exit(1)

    def _load_identity(self):
        from agent.memory_manager import SOUL_FILE, BEHAVIORS_FILE
        if not SOUL_FILE.exists():
            raise FileNotFoundError(f"Soul file not found: {SOUL_FILE}")
        self.soul = SOUL_FILE.read_text()
        if BEHAVIORS_FILE.exists():
            self.soul += "\n\n---\n\n## Behavior Rules\n\n" + BEHAVIORS_FILE.read_text()

    def _init_skills(self):
        from agent.memory_manager import MemoryManager
        from agent.skills.fetch import FetchSkill
        from agent.skills.report import ReportSkill
        from agent.skills.reflect import ReflectSkill
        from agent.skills.notify import NotifySkill

        self.memory = MemoryManager()
        self.fetch_skill = FetchSkill()
        self.report_skill = ReportSkill(api_key=os.getenv("NVIDIA_API_KEY"))
        self.reflect_skill = ReflectSkill(api_key=os.getenv("NVIDIA_API_KEY"))
        self.notify_skill = NotifySkill()

    # ------------------------------------------------------------------ #
    # Main loop                                                            #
    # ------------------------------------------------------------------ #

    def run(self, log_fn=None) -> dict:
        """
        Run the full agent loop.
        log_fn: optional callable(str) — receives each log line (used by web SSE stream).
        Returns: { "report": str, "student_count": int, "ok_count": int, "verdict": str }
        """

        def log(msg: str):
            print(msg)
            if log_fn:
                log_fn(msg)

        csv_path = os.getenv("STUDENTS_CSV_PATH", str(ROOT / "students.csv"))
        github_token = os.getenv("GITHUB_TOKEN")

        # 1. FETCH
        log("[1/5] Fetching student commits ...")
        results = self.fetch_skill.run(csv_path, github_token)
        if not results:
            msg = "No students configured. Add students via Telegram (/students) or the web UI."
            log(f"      {msg}")
            return {"report": msg, "student_count": 0, "ok_count": 0, "verdict": "SKIPPED"}
        ok = sum(1 for r in results if r.get("commit", {}).get("has_commits"))
        log(f"      {ok}/{len(results)} students have commits.")

        # 2. CONTEXT
        log("[2/5] Loading memory context ...")
        memory_context = self.memory.get_context()

        # 3. REPORT
        log("[3/5] Generating report ...")
        report = self.report_skill.run(results, self.soul, memory_context)

        # 4. REFLECT
        log("[4/5] Reflecting on report quality ...")
        verdict = self.reflect_skill.run(report, self.soul)
        log(f"      Verdict: {verdict}")

        if verdict.startswith("REVISE"):
            log("      Report flagged — prepending warning and sending anyway.")
            report = f"[Agent QA flag: {verdict}]\n\n{report}"

        # 5. NOTIFY
        log("[5/5] Sending notifications ...")
        self.notify_skill.run(report)
        log("      Email + Telegram sent.")

        # 6. REMEMBER
        self.memory.update(results)
        log("      Memory updated.")

        log("\n--- REPORT ---\n" + report + "\n--- END ---\n")
        log("Done.")

        return {
            "report": report,
            "student_count": len(results),
            "ok_count": ok,
            "verdict": verdict,
        }

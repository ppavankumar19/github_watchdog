"""
agent/memory_manager.py

Manages persistent agent state across runs.
- state.json  : machine-readable structured data (parsed/written by this module)
- memory.md   : human-readable run log (auto-generated after each run for mentor inspection)
"""

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

# soul.md lives in the repo (read-only, committed).
# state.json + memory.md are runtime-written and go under DATA_DIR on Render.
_REPO_ROOT = Path(__file__).parent.parent
SOUL_FILE      = _REPO_ROOT / "memory" / "soul.md"       # agent identity
BEHAVIORS_FILE = _REPO_ROOT / "memory" / "behaviors.md"  # edge-case rules

_DATA_DIR = Path(os.getenv("DATA_DIR") or _REPO_ROOT)
STATE_FILE = _DATA_DIR / "state.json"
MEMORY_MD = _DATA_DIR / "memory.md"


class MemoryManager:
    def __init__(self):
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self) -> dict:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {"last_run": None, "students": {}}

    # ------------------------------------------------------------------ #
    # Public: read                                                         #
    # ------------------------------------------------------------------ #

    def get_context(self) -> str:
        """
        Returns a plain-text memory summary for injection into LLM prompts.
        Called by core.py before report generation.
        """
        if not self.state["last_run"]:
            return "This is the first run — no prior commit history is available."

        lines = [f"Last run: {self.state['last_run']}", ""]
        students = self.state.get("students", {})

        if not students:
            return "\n".join(lines) + "\nNo student history recorded yet."

        for name, data in students.items():
            days = data.get("days_since_commit")
            streak = data.get("streak_days", 0)
            last_msg = data.get("last_message") or "no message"
            last_date = data.get("last_date") or "unknown"

            if days is None:
                recency = "unknown last commit date"
            elif days == 0:
                recency = "committed today"
            elif days == 1:
                recency = "committed yesterday"
            else:
                recency = f"last committed {days} days ago"

            streak_note = f", {streak}-day streak" if streak > 1 else ""
            lines.append(f'- {name}: {recency}{streak_note} — "{last_msg}" ({last_date})')

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Public: write                                                        #
    # ------------------------------------------------------------------ #

    def update(self, student_results: list[dict]):
        """
        Called after a successful run. Updates state.json and regenerates memory.md.
        student_results: list of dicts from FetchSkill (name, repo_url, commit?, error?)
        """
        today = date.today()
        self.state["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        for entry in student_results:
            name = entry["name"]
            commit = entry.get("commit") or {}

            prev = self.state["students"].get(name, {})

            if not commit.get("has_commits"):
                # Preserve existing history; just note no commit today
                if name not in self.state["students"]:
                    self.state["students"][name] = {
                        "last_sha": None,
                        "last_date": None,
                        "last_message": None,
                        "streak_days": 0,
                        "days_since_commit": None,
                    }
                continue

            commit_date_str = commit.get("date", "")[:10]  # YYYY-MM-DD
            try:
                commit_day = date.fromisoformat(commit_date_str)
                days_since = (today - commit_day).days
            except ValueError:
                commit_day = None
                days_since = None

            # Streak calculation: compare today with the date of the last recorded commit
            prev_date_str = prev.get("last_date")
            streak = prev.get("streak_days", 0)
            if prev_date_str and commit_day:
                try:
                    prev_day = date.fromisoformat(prev_date_str)
                    gap = (today - prev_day).days
                    if gap == 1:
                        streak += 1   # consecutive day
                    elif gap == 0:
                        pass          # already counted today
                    else:
                        streak = 1    # streak broken
                except ValueError:
                    streak = 1
            else:
                streak = 1

            self.state["students"][name] = {
                "last_sha": commit.get("sha"),
                "last_date": commit_date_str,
                "last_message": (commit.get("message") or "").splitlines()[0][:100],
                "streak_days": streak,
                "days_since_commit": days_since,
            }

        self._save()
        self._write_memory_md()

    # ------------------------------------------------------------------ #
    # Private                                                              #
    # ------------------------------------------------------------------ #

    def _save(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def _write_memory_md(self):
        """Regenerate the human-readable memory.md after each run."""
        lines = [
            "# GitHub Watchdog — Agent Memory",
            "",
            f"Last updated: {self.state['last_run']}",
            "",
            "## Student History",
            "",
        ]

        students = self.state.get("students", {})
        if not students:
            lines.append("No student data recorded yet.")
        else:
            for name, data in students.items():
                days = data.get("days_since_commit")
                streak = data.get("streak_days", 0)
                flag = " ⚠️" if (days is not None and days >= 3) else ""

                lines += [
                    f"### {name}{flag}",
                    f"- Last commit date : {data.get('last_date') or 'never'}",
                    f"- Last message     : {data.get('last_message') or 'n/a'}",
                    f"- Streak           : {streak} day(s)",
                    f"- Days since commit: {days if days is not None else 'unknown'}",
                    "",
                ]

        with open(MEMORY_MD, "w") as f:
            f.write("\n".join(lines))

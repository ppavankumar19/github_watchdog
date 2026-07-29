"""
agent/skills/fetch.py

FetchSkill: reads students.csv and pulls the latest commit for each repo.
Wraps github_utils so the agent core never touches the HTTP layer directly.
"""

import csv
import sys
from pathlib import Path

# Allow imports from the project root when running from any working directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from github_utils import get_latest_commit


class FetchSkill:
    def run(self, csv_path: str, github_token: str | None) -> list[dict]:
        """
        Returns a list of dicts:
          { name, repo_url, commit: {...} }   on success
          { name, repo_url, error: "..." }    on failure
        """
        students = self._read_csv(csv_path)
        results = []

        for s in students:
            entry = {"name": s["name"], "repo_url": s["repo_url"]}
            try:
                entry["commit"] = get_latest_commit(s["repo_url"], github_token)
            except Exception as exc:
                entry["error"] = str(exc)
            results.append(entry)

        return results

    def _read_csv(self, csv_path: str) -> list[dict]:
        students = []
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    name = row.get("name", "").strip()
                    repo_url = row.get("repo_url", "").strip()
                    if name and repo_url:
                        students.append({"name": name, "repo_url": repo_url})
        except FileNotFoundError:
            pass
        return students

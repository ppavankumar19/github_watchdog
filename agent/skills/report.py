"""
agent/skills/report.py

ReportSkill: converts raw commit data + agent memory into a formatted report.
Uses NVIDIA NIM via the OpenAI-compatible client.
Prompt template lives in prompts/report.md — edit there to change style, no Python needed.
"""

import os
from datetime import date
from pathlib import Path

from openai import OpenAI

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class ReportSkill:
    def __init__(self, api_key: str):
        self.client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        self.model = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
        self.template = (PROMPTS_DIR / "report.md").read_text()

    def run(self, student_results: list[dict], soul: str, memory_context: str) -> str:
        raw_data = self._format_raw(student_results)
        prompt = self.template.format(
            soul=soul,
            memory_context=memory_context,
            raw_data=raw_data,
            date=date.today().isoformat(),
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.6,
            top_p=0.95,
        )
        raw = resp.choices[0].message.content or ""
        # Strip any reasoning preamble — report always starts with "Daily GitHub"
        marker = "Daily GitHub Activity Report"
        idx = raw.find(marker)
        return raw[idx:].strip() if idx != -1 else raw.strip()

    def _format_raw(self, results: list[dict]) -> str:
        lines = []
        for entry in results:
            name = entry["name"]
            repo = entry["repo_url"]

            if entry.get("error"):
                lines.append(f"- {name} ({repo}): ERROR — {entry['error']}")
                continue

            commit = entry.get("commit") or {}
            if not commit.get("has_commits"):
                lines.append(f"- {name} ({repo}): No commits found in repo.")
                continue

            first_line = (commit.get("message") or "").splitlines()[0]
            lines.append(
                f"- {name} ({repo}): commit {commit['sha']} "
                f"by {commit['author_name']} on {commit['date']} "
                f'— "{first_line}" ({commit["url"]})'
            )
        return "\n".join(lines)

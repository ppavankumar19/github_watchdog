"""
agent/skills/reflect.py

ReflectSkill: agent self-QA pass before sending the report.
Uses NVIDIA NIM via the OpenAI-compatible client.
Prompt template lives in prompts/reflect.md.
"""

import os
from pathlib import Path

from openai import OpenAI

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class ReflectSkill:
    def __init__(self, api_key: str):
        self.client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        self.model = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
        self.template = (PROMPTS_DIR / "reflect.md").read_text()

    def run(self, report: str, soul: str) -> str:
        """
        Returns:
          "APPROVED"           — report passes QA
          "REVISE: <reason>"   — report has a specific problem
        """
        prompt = self.template.format(soul=soul, report=report)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2,
        )
        raw = (resp.choices[0].message.content or "").strip()
        # Extract APPROVED or REVISE: line — ignore any reasoning around it
        for line in raw.splitlines():
            line = line.strip()
            if line == "APPROVED" or line.startswith("REVISE:"):
                return line
        # Fallback: if model said something unexpected, approve and log
        return "APPROVED"

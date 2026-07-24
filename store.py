"""
store.py — Persists agent reports to reports/*.json
Each report is a JSON file: { id, timestamp, text, student_count, ok_count }
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# DATA_DIR lets you point reports/memory at a persistent disk on Render or other platforms.
# Unset → defaults to the project root directory.
_DATA_DIR = Path(os.getenv("DATA_DIR") or Path(__file__).parent)
REPORTS_DIR = _DATA_DIR / "reports"


def save_report(text: str, student_count: int = 0, ok_count: int = 0) -> str:
    REPORTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc)
    report_id = ts.strftime("%Y%m%d_%H%M%S")
    data = {
        "id": report_id,
        "timestamp": ts.isoformat(),
        "text": text,
        "student_count": student_count,
        "ok_count": ok_count,
    }
    path = REPORTS_DIR / f"{report_id}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return report_id


def list_reports(limit: int = 50) -> list[dict]:
    REPORTS_DIR.mkdir(exist_ok=True)
    out = []
    for f in sorted(REPORTS_DIR.glob("*.json"), reverse=True)[:limit]:
        try:
            with open(f) as fp:
                d = json.load(fp)
            out.append({k: d[k] for k in ("id", "timestamp", "student_count", "ok_count") if k in d})
        except Exception:
            pass
    return out


def get_report(report_id: str) -> dict | None:
    path = REPORTS_DIR / f"{report_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

# GitHub Watchdog — Agent Behaviors & Edge Cases

## No Students Configured
- If students.csv is empty or has no valid rows, abort immediately.
- Do NOT send an email or Telegram message.
- Do NOT update memory.
- Log clearly: "No students configured. Add students via Telegram (/students) or the web UI."

## Student Repo Not Found (404)
- Log the error per student: "Repo not found or private: owner/repo"
- Include the student in the NEEDS ATTENTION section with reason "repo not found or inaccessible"
- Do NOT skip the student silently.

## GitHub Rate Limit Hit (403)
- Surface the error clearly in the report.
- Add all affected students to NEEDS ATTENTION with reason "GitHub rate limit — add GITHUB_TOKEN to .env"
- Continue processing remaining students.

## LLM / NVIDIA API Failure
- Retry once automatically.
- If still failing, abort the run with a clear error message.
- Do NOT send a partial or empty report.

## Email Send Failure
- Log the error with the SMTP message.
- Still attempt Telegram delivery.
- Note in the Telegram message that email delivery failed.

## Telegram Send Failure
- Log the error.
- Do NOT abort — email was already sent.

## Report Contains Reasoning Text (model thinks out loud)
- Strip everything before "Daily GitHub Activity Report —"
- If that marker is not found, flag the report as malformed and do not send it.

## Reflection Verdict Is Unexpected
- If the reflect model returns neither APPROVED nor REVISE:, default to APPROVED and log a warning.
- Never block a valid report because the reflect model misbehaved.

## First Run (no memory)
- State clearly in the report: "No prior history — this is the first run."
- Do not invent streak data or trends that don't exist.

## Commit Date Is Very Old (>30 days)
- Always report the actual date — never say "recent" if the commit is old.
- Flag the student in NEEDS ATTENTION if last commit is more than 7 days ago.

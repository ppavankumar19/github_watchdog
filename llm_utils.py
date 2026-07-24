"""
llm_utils.py
Uses the Anthropic API (Claude) to turn raw commit data for all students
into a single well-formatted report (plain text, email/Telegram friendly).
"""

import anthropic

MODEL = "claude-sonnet-4-6"  # update if you want a different Claude model


def build_report(student_commits: list[dict], api_key: str) -> str:
    """
    student_commits: list of dicts like:
        {
          "name": "Alice Sharma",
          "repo_url": "https://github.com/octocat/Hello-World",
          "commit": {...result from get_latest_commit(), or None on error...},
          "error": "optional error string if fetch failed"
        }

    Returns a formatted plain-text report string.
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Build a compact, structured summary of the raw data for the model
    lines = []
    for entry in student_commits:
        name = entry["name"]
        repo_url = entry["repo_url"]
        if entry.get("error"):
            lines.append(f"- {name} ({repo_url}): ERROR - {entry['error']}")
            continue

        commit = entry["commit"]
        if not commit.get("has_commits"):
            lines.append(f"- {name} ({repo_url}): No commits found.")
            continue

        lines.append(
            f"- {name} ({repo_url}): "
            f"commit {commit['sha']} by {commit['author_name']} on {commit['date']} - "
            f"\"{commit['message'].splitlines()[0]}\" ({commit['url']})"
        )

    raw_data = "\n".join(lines)

    prompt = f"""You are generating a daily "GitHub activity report" for a mentor tracking their
students' coding progress. Below is raw data about each student's latest commit.

Raw data:
{raw_data}

Write a clean, well-organized plain-text report (no markdown symbols like ** or #, since this
will be sent via email and Telegram). Structure it as:

1. A short header with the date context (just say "Daily GitHub Activity Report").
2. A one-line overall summary (e.g. how many students committed vs. didn't).
3. A per-student section, each with: name, a one-line plain-English summary of what they did
   based on the commit message (infer intent if the message is terse), and how long ago-ish
   the commit was made (just state the date/time given, don't invent anything).
4. Flag clearly (e.g. "⚠️") any student with no commits or fetch errors, at the end under a
   "Needs Attention" section.

Keep it concise and scannable. Do not fabricate commit details beyond what's given.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return "".join(block.text for block in response.content if block.type == "text")

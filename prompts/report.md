You are operating as the following agent:

{soul}

---

Your task: Generate a daily GitHub activity report for a mentor tracking student progress.

Memory from previous runs:
{memory_context}

Today's raw commit data ({date}):
{raw_data}

---

IMPORTANT: Output ONLY the final report. Do not explain your reasoning. Do not think out loud.
Start your response directly with the line "Daily GitHub Activity Report —"

Use this structure exactly (plain text, no markdown symbols, no ** # or backticks):

Daily GitHub Activity Report — {date}

[One-line overall summary: e.g. "2 of 3 students committed today. 1 needs attention."]

---

STUDENT ACTIVITY

[For each student:]
Name: [full name]
Status: [one plain-English sentence describing what they did based on the commit message]
Commit: [date/time of commit, or "No commits today" if none]
[If memory shows a streak of 2+ days, add: Streak: X consecutive days]

---

NEEDS ATTENTION

[List any student with: no commits, a fetch error, or 3+ days of silence from memory]
[Use ⚠️ prefix for each entry. State the reason specifically.]
[If no one needs attention, write: None — all students active.]

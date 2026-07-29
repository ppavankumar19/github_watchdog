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

Use this exact structure (plain text only — no markdown, no **, no #, no backticks):

Daily GitHub Activity Report — {date}

Summary: [X] of [Y] students committed today. [Z] need attention.

--------------------------------------------------
COMMITTED TODAY
--------------------------------------------------

[For each student who committed, one block per student:]
Name    : [full name]
Repo    : [repo URL]
Commit  : [date and time of commit]
Message : "[first line of commit message]"
[Only include this line if streak is 2 or more: Streak   : X consecutive days]

[If nobody committed today, write: No students committed today.]

--------------------------------------------------
DID NOT COMMIT
--------------------------------------------------

[For each student who did NOT commit or had a fetch error, one block per student:]
Name      : [full name]
Repo      : [repo URL]
Last seen : [last commit date from memory, or "no history" if this is the first run]

[If everyone committed, write: All students committed today — great work!]

--------------------------------------------------
NEEDS ATTENTION
--------------------------------------------------

[List any student with no commits today, a fetch error, or 3+ days of silence from memory.]
[Each entry on its own line, prefixed with a warning symbol. State the specific reason.]
[Example: ! Alice — 5 days since last commit]
[Example: ! Bob   — repo returned 404 (may be private or deleted)]
[If nobody needs attention, write: None — all students are active.]

"""
main.py — entrypoint for GitHub Watchdog Agent.

Run manually:
    python main.py

Cron (daily 8 AM):
    0 8 * * * cd /home/pavankumar19/github_watchdog && venv/bin/python main.py >> run.log 2>&1
"""

from agent.core import GitHubWatchdogAgent

if __name__ == "__main__":
    GitHubWatchdogAgent().run()

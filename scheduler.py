"""
scheduler.py — APScheduler integration for in-process daily runs.
Reads SCHEDULE_TIME env var (HH:MM UTC, default 08:00).
This replaces OS cron when running inside Docker.
"""

import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger("scheduler")
scheduler = BackgroundScheduler(timezone="UTC")


def _run_agent():
    """Called by the scheduler. Runs the full agent loop and saves the report."""
    from agent.core import GitHubWatchdogAgent
    from store import save_report

    log.info("[scheduler] Starting scheduled agent run ...")
    try:
        agent = GitHubWatchdogAgent()
        result = agent.run()
        save_report(
            result["report"],
            student_count=result["student_count"],
            ok_count=result["ok_count"],
        )
        log.info("[scheduler] Run complete.")
    except Exception as exc:
        log.error(f"[scheduler] Agent run failed: {exc}", exc_info=True)


def init_scheduler():
    """Call once at app startup to register the daily job."""
    schedule_time = os.getenv("SCHEDULE_TIME", "08:00")
    try:
        hour, minute = schedule_time.split(":")
    except ValueError:
        hour, minute = "8", "0"

    scheduler.add_job(
        _run_agent,
        CronTrigger(hour=int(hour), minute=int(minute), timezone="UTC"),
        id="daily_watchdog",
        replace_existing=True,
    )
    scheduler.start()
    log.info(f"[scheduler] Daily job scheduled at {schedule_time} UTC.")


def get_next_run() -> str | None:
    job = scheduler.get_job("daily_watchdog")
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None

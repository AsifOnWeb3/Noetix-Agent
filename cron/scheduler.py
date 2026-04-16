"""
NoetixAgent Cron Scheduler — schedule tasks with cron expressions.
Inspired by Hermes Agent's cron module.
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable

logger = logging.getLogger("noetix.cron")


class CronJob:
    def __init__(self, name: str, expression: str, task: str, enabled: bool = True):
        self.name = name
        self.expression = expression
        self.task = task
        self.enabled = enabled
        self.last_run: Optional[str] = None
        self.run_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "expression": self.expression,
            "task": self.task,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "CronJob":
        job = cls(d["name"], d["expression"], d["task"], d.get("enabled", True))
        job.last_run = d.get("last_run")
        job.run_count = d.get("run_count", 0)
        return job

    def should_run(self, now: datetime) -> bool:
        """Simple cron expression matching: min hour day month weekday"""
        try:
            parts = self.expression.split()
            if len(parts) != 5:
                return False
            minute, hour, day, month, weekday = parts

            def match(value: str, current: int) -> bool:
                if value == "*":
                    return True
                if "/" in value:
                    _, step = value.split("/")
                    return current % int(step) == 0
                if "," in value:
                    return str(current) in value.split(",")
                return int(value) == current

            return (
                match(minute, now.minute)
                and match(hour, now.hour)
                and match(day, now.day)
                and match(month, now.month)
                and match(weekday, now.weekday())
            )
        except Exception:
            return False


class CronScheduler:
    def __init__(self, storage_path: Path, run_task_fn: Callable):
        self.storage_path = storage_path
        self.run_task = run_task_fn
        self.jobs: Dict[str, CronJob] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._load()

    def _load(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                self.jobs = {d["name"]: CronJob.from_dict(d) for d in data}
            except Exception as e:
                logger.warning(f"Cron load error: {e}")

    def _save(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps([j.to_dict() for j in self.jobs.values()], indent=2))
        except Exception as e:
            logger.warning(f"Cron save error: {e}")

    def add(self, name: str, expression: str, task: str) -> str:
        self.jobs[name] = CronJob(name, expression, task)
        self._save()
        return f"Cron job '{name}' added: [{expression}] → {task}"

    def remove(self, name: str) -> str:
        if name in self.jobs:
            del self.jobs[name]
            self._save()
            return f"Job '{name}' removed."
        return f"Job '{name}' not found."

    def list_jobs(self) -> str:
        if not self.jobs:
            return "No scheduled jobs."
        lines = []
        for j in self.jobs.values():
            status = "✓" if j.enabled else "✗"
            lines.append(f"{status} [{j.name}] {j.expression} → {j.task[:60]} (runs: {j.run_count})")
        return "\n".join(lines)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Cron scheduler started.")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            now = datetime.now()
            for job in list(self.jobs.values()):
                if job.enabled and job.should_run(now):
                    logger.info(f"Running cron job: {job.name}")
                    try:
                        result = self.run_task(job.task)
                        job.last_run = now.isoformat()
                        job.run_count += 1
                        self._save()
                    except Exception as e:
                        logger.error(f"Cron job {job.name} failed: {e}")
            time.sleep(60 - datetime.now().second)


# Tool registration
from agent.toolregistry import noetix_tool

_scheduler: Optional[CronScheduler] = None


def init_scheduler(storage_path: Path, run_task_fn: Callable):
    global _scheduler
    _scheduler = CronScheduler(storage_path, run_task_fn)
    _scheduler.start()


@noetix_tool(
    name="schedule_task",
    description="Schedule a recurring task using cron expression (min hour day month weekday).",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Unique job name"},
            "cron": {"type": "string", "description": "Cron expression e.g. '0 9 * * 1' = every Monday 9am"},
            "task": {"type": "string", "description": "Task description to run"},
        },
        "required": ["name", "cron", "task"],
    },
    tags=["automation", "core"],
)
def schedule_task(name: str, cron: str, task: str):
    if _scheduler is None:
        return "Scheduler not initialized. Run init_scheduler() first."
    return _scheduler.add(name, cron, task)


@noetix_tool(
    name="list_scheduled",
    description="List all scheduled cron jobs.",
    parameters={"type": "object", "properties": {}},
    tags=["automation", "core"],
)
def list_scheduled():
    if _scheduler is None:
        return "Scheduler not initialized."
    return _scheduler.list_jobs()


@noetix_tool(
    name="remove_scheduled",
    description="Remove a scheduled cron job by name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Job name to remove"},
        },
        "required": ["name"],
    },
    tags=["automation", "core"],
)
def remove_scheduled(name: str):
    if _scheduler is None:
        return "Scheduler not initialized."
    return _scheduler.remove(name)

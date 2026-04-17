"""Cron scheduler engine — runs cycles on schedule inside the Trinity process."""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import threading
import time
from pathlib import Path

from trinity._io import atomic_write_json
from trinity.config import CycleConfig, TrinityConfig

log = logging.getLogger(__name__)


def _parse_cron_field(field: str, min_val: int, max_val: int) -> set[int]:
    """Parse a single cron field into a set of matching values."""
    values: set[int] = set()
    for part in field.split(","):
        part = part.strip()
        if part == "*":
            values.update(range(min_val, max_val + 1))
        elif "/" in part:
            base, step = part.split("/", 1)
            step_int = int(step)
            start = min_val if base == "*" else int(base)
            values.update(range(start, max_val + 1, step_int))
        elif "-" in part:
            lo, hi = part.split("-", 1)
            values.update(range(int(lo), int(hi) + 1))
        else:
            values.add(int(part))
    return values


def cron_matches(schedule: str, now: dt.datetime) -> bool:
    """Check if a cron expression matches the given datetime.

    Supports: minute hour day-of-month month day-of-week
    """
    parts = schedule.split()
    if len(parts) != 5:
        return False

    minute = _parse_cron_field(parts[0], 0, 59)
    hour = _parse_cron_field(parts[1], 0, 23)
    dom = _parse_cron_field(parts[2], 1, 31)
    month = _parse_cron_field(parts[3], 1, 12)
    dow = _parse_cron_field(parts[4], 0, 6)

    # Convert Python weekday (0=Mon) to cron convention (0=Sun)
    cron_dow = (now.weekday() + 1) % 7
    return (
        now.minute in minute
        and now.hour in hour
        and now.day in dom
        and now.month in month
        and cron_dow in dow
    )


class Scheduler:
    """Background scheduler that checks cycles every 60 seconds."""

    def __init__(
        self,
        config: TrinityConfig,
        run_cycle: callable,
    ):
        self.config = config
        self.run_cycle = run_cycle  # fn(cycle_name, cycle_config) -> None
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_run: dict[str, str] = {}  # cycle -> last run minute "YYYY-MM-DD HH:MM"
        self._state_file = config.trinity_dir / "state" / "scheduler.json"
        self._load_state()

    def _load_state(self):
        if self._state_file.exists():
            try:
                self._last_run = json.loads(self._state_file.read_text())
            except (json.JSONDecodeError, OSError):
                self._last_run = {}

    def _save_state(self):
        atomic_write_json(self._state_file, self._last_run)

    def start(self):
        """Start the scheduler in a background thread."""
        if not self.config.scheduler.enabled:
            log.info("Scheduler disabled in config")
            return
        if not self.config.scheduler.cycles:
            log.info("No cycles configured")
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()
        log.info(
            "Scheduler started with %d cycles",
            len(self.config.scheduler.cycles),
        )

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                log.error("Scheduler tick error: %s", e, exc_info=True)
            time.sleep(60)

    def _tick(self):
        now = dt.datetime.now()
        now_key = now.strftime("%Y-%m-%d %H:%M")

        for name, cycle in self.config.scheduler.cycles.items():
            if not cycle.schedule:
                continue

            # Skip if already run this minute
            if self._last_run.get(name) == now_key:
                continue

            if cron_matches(cycle.schedule, now):
                log.info("Triggering cycle: %s", name)
                self._last_run[name] = now_key
                self._save_state()

                # Run in a separate thread so we don't block the scheduler
                t = threading.Thread(
                    target=self._run_safe,
                    args=(name, cycle),
                    daemon=True,
                    name=f"cycle-{name}",
                )
                t.start()

    def _run_safe(self, name: str, cycle: CycleConfig):
        try:
            self.run_cycle(name, cycle)
        except Exception as e:
            log.error("Cycle %s failed: %s", name, e, exc_info=True)

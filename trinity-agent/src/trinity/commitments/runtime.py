"""Background runtime that fires due commitments back to Telegram.

Polls the store every ``poll_interval_seconds`` (default 60s). Sends a
single message per due record using the existing TelegramAPI, then marks
the record as ``sent``. Survives transient network errors — failed sends
don't update status, so the next tick will retry.
"""
from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from pathlib import Path

from trinity.commitments import store
from trinity.commitments.types import SENT
from trinity.telegram.api import TelegramAPI

log = logging.getLogger(__name__)


class CommitmentsRuntime:
    """Polling thread that delivers due commitments to Telegram."""

    def __init__(
        self,
        trinity_dir: Path,
        api: TelegramAPI,
        poll_interval_seconds: int = 60,
    ):
        self.trinity_dir = trinity_dir
        self.api = api
        self.poll_interval = max(15, int(poll_interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="commitments-runtime",
        )
        self._thread.start()
        log.info("commitments runtime started (poll=%ds)", self.poll_interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                log.exception("commitments tick failed")
            self._stop.wait(self.poll_interval)

    def _tick(self) -> None:
        due = store.due_now(self.trinity_dir)
        if not due:
            return
        for record in due:
            try:
                chat_id = int(record.chat_id)
            except ValueError:
                log.warning("skipping commitment %s: bad chat_id", record.id)
                continue
            text = self._format_message(record)
            result = self.api.send_message(chat_id, text)
            if not result:
                log.warning("commitment %s send returned empty — will retry", record.id)
                continue
            store.update_status(
                self.trinity_dir,
                record.id,
                SENT,
                sent_at=dt.datetime.now().isoformat(),
            )
            log.info(
                "fired commitment %s (kind=%s) to chat %s",
                record.id, record.kind, record.chat_id,
            )

    @staticmethod
    def _format_message(record) -> str:
        body = record.nudge_text or record.text
        return f"⏰ Follow-up:\n{body}\n\n_/done {record.id}_  _/snooze {record.id} 1d_"

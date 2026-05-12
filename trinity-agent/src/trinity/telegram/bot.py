"""Main Telegram bot loop with per-chat worker threads.

This module is deliberately *decoupled* from agent logic.  The caller
provides a ``handle_message`` callable that does the actual work — this
module only handles polling, access control, routing, and concurrency.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import queue
import signal
import threading
import time
from pathlib import Path
from typing import Callable

import requests

from trinity.config import TrinityConfig
from trinity.telegram.api import TelegramAPI
from trinity.telegram.acl import AccessControl

log = logging.getLogger(__name__)

# Type alias for the handler the application provides.
HandleMessageFn = Callable[[TelegramAPI, dict, TrinityConfig], None]


# ── Offset persistence ──────────────────────────────────────────────

def _offset_path(config: TrinityConfig) -> Path:
    return config.trinity_dir / "state" / "offset.json"


def _load_offset(config: TrinityConfig) -> int:
    """Load the last processed ``update_id`` from disk."""
    path = _offset_path(config)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data.get("lastUpdateId", 0)
        except (json.JSONDecodeError, KeyError, OSError):
            log.warning("Corrupt offset file — starting from 0")
    return 0


def _save_offset(config: TrinityConfig, update_id: int) -> None:
    """Persist *update_id* so we resume correctly after a restart."""
    path = _offset_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps({
            "lastUpdateId": update_id,
            "updatedAt": dt.datetime.now().isoformat(),
        }))
    except OSError:
        log.exception("Failed to save offset")


# ── Per-chat worker pool ────────────────────────────────────────────

class ChatWorkerPool:
    """One thread per ``chat_id`` — messages within a chat are sequential,
    different chats run in parallel.

    Parameters
    ----------
    api:
        Telegram API wrapper used by the handler.
    bot_username:
        The bot's ``@username`` (used only for logging).
    config:
        Full Trinity configuration passed through to the handler.
    handle_message_fn:
        ``(api, msg, config) -> None`` — processes a single message.
    """

    def __init__(
        self,
        api: TelegramAPI,
        bot_username: str,
        config: TrinityConfig,
        handle_message_fn: HandleMessageFn,
    ):
        self.api = api
        self.bot_username = bot_username
        self.config = config
        self.handle_message_fn = handle_message_fn

        self._workers: dict[int, queue.Queue] = {}
        self._lock = threading.Lock()

    def dispatch(self, msg: dict) -> None:
        """Route *msg* to the worker thread for its ``chat_id``.

        Creates the worker on first contact — non-blocking.
        """
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id:
            return

        with self._lock:
            if chat_id not in self._workers:
                q: queue.Queue = queue.Queue()
                self._workers[chat_id] = q
                t = threading.Thread(
                    target=self._worker_loop,
                    args=(chat_id, q),
                    daemon=True,
                    name=f"chat-{chat_id}",
                )
                t.start()
                log.info("Started worker thread for chat %s", chat_id)

        self._workers[chat_id].put(msg)

    def shutdown(self) -> None:
        """Send a shutdown sentinel to each worker thread."""
        with self._lock:
            for chat_id, q in self._workers.items():
                q.put(None)
            log.info("Shutdown sentinels sent to %d workers", len(self._workers))

    def _worker_loop(self, chat_id: int, q: queue.Queue) -> None:
        """Consume messages for a single chat, one at a time."""
        while True:
            msg = q.get()
            if msg is None:
                log.info("Worker for chat %s received shutdown sentinel", chat_id)
                q.task_done()
                break
            try:
                self.handle_message_fn(self.api, msg, self.config)
            except Exception:
                log.exception("Error in worker for chat %s", chat_id)
            finally:
                q.task_done()


# ── Main loop ───────────────────────────────────────────────────────

def run_bot(config: TrinityConfig, handle_message: HandleMessageFn) -> None:
    """Start the long-polling loop.

    Parameters
    ----------
    config:
        Fully-loaded :class:`TrinityConfig`.
    handle_message:
        ``(api, msg, config) -> None`` — called for every message that
        passes access control.  Executed inside a per-chat worker thread.
    """
    # 1. Resolve bot token.
    token = config.telegram.get_bot_token()
    if not token:
        log.error(
            "No Telegram bot token — set %s in the environment",
            config.telegram.bot_token_env,
        )
        return

    api = TelegramAPI(token)

    # 2. Verify connectivity.
    me = api.get_me()
    if not me:
        log.error("Could not reach the Telegram Bot API — check token / network")
        return
    bot_username: str = me.get("username", "")
    log.info("Bot online: @%s (id: %s)", bot_username, me.get("id"))

    # 3. Clear stale webhooks / competing long-polls.
    api.delete_webhook(drop_pending=False)
    log.info("Cleared webhook / stale sessions")

    # 4. Access control.
    acl = AccessControl(config.telegram, bot_username)

    # 5. Worker pool.
    pool = ChatWorkerPool(api, bot_username, config, handle_message)

    # 6. Load persisted offset.
    offset = _load_offset(config)

    # 7. Graceful shutdown on SIGINT / SIGTERM.
    running = True

    def _shutdown(sig: int, _frame: object) -> None:
        nonlocal running
        log.info("Received signal %s — shutting down", sig)
        running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    log.info("Listening for messages (offset=%d)...", offset)

    poll_timeout = config.telegram.poll_timeout
    conflict_retries = 0
    connect_retries = 0
    last_successful_poll = time.monotonic()

    # Self-healing watchdog: if we haven't completed a successful poll in
    # WATCHDOG_TIMEOUT_S, something is wedged — raise to exit the loop and
    # let the supervisor in cmd_start restart us cleanly.
    WATCHDOG_TIMEOUT_S = 600  # 10 minutes

    # 8. Main polling loop.
    while running:
        # Self-healing check.
        if time.monotonic() - last_successful_poll > WATCHDOG_TIMEOUT_S:
            log.error(
                "Watchdog: no successful poll for %ds — forcing loop exit for restart",
                WATCHDOG_TIMEOUT_S,
            )
            break

        try:
            updates = api.get_updates(offset=offset + 1, timeout=poll_timeout)
            conflict_retries = 0
            connect_retries = 0
            last_successful_poll = time.monotonic()
        except requests.exceptions.HTTPError as exc:
            # 9. Handle 409 Conflict — another consumer is still draining.
            if exc.response is not None and exc.response.status_code == 409:
                conflict_retries += 1
                wait = min(conflict_retries * 5, 30)
                if conflict_retries <= 12:
                    log.info(
                        "409 conflict (attempt %d) — previous consumer draining, "
                        "retrying in %ds",
                        conflict_retries,
                        wait,
                    )
                    time.sleep(wait)
                    continue
                else:
                    log.error(
                        "409 conflict persists after 12 attempts — "
                        "another bot consumer is still active"
                    )
                    break
            log.error("HTTP error: %s — retrying in 10s", exc)
            time.sleep(10)
            continue
        except requests.exceptions.Timeout:
            # Normal for long-poll expiry.
            continue
        except requests.exceptions.ConnectionError as exc:
            # Exponential backoff: 5, 10, 20, 40, cap at 60s.
            connect_retries += 1
            wait = min(5 * (2 ** (connect_retries - 1)), 60)
            log.warning(
                "Connection error (attempt %d): %s — retrying in %ds",
                connect_retries, exc, wait,
            )
            # Rebuild the session after repeated failures — the connection
            # pool may be poisoned by a half-open socket.
            if connect_retries >= 3:
                try:
                    api.reset_session()
                    log.info("Rebuilt HTTP session after %d connect failures", connect_retries)
                except Exception:
                    log.exception("Failed to reset HTTP session")
            time.sleep(wait)
            continue
        except Exception:
            log.exception("Unexpected polling error — retrying in 10s")
            time.sleep(10)
            continue

        for update in updates:
            update_id = update.get("update_id", 0)
            offset = max(offset, update_id)
            # 10. Persist offset after each update.
            _save_offset(config, offset)

            if not acl.should_respond(update):
                continue

            msg = update.get("message", {})
            if msg:
                pool.dispatch(msg)

    pool.shutdown()
    log.info("Bot stopped.")

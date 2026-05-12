"""Trinity Telegram bot — modular package.

Submodules:
    api         Low-level Telegram Bot API wrapper.
    acl         Access-control / message-filtering logic.
    streaming   Live status updates pushed to Telegram during agent work.
    bot         Long-polling loop and per-chat worker thread pool.
"""

from trinity.telegram.api import TelegramAPI
from trinity.telegram.acl import AccessControl
from trinity.telegram.streaming import StreamState
from trinity.telegram.bot import run_bot, ChatWorkerPool

__all__ = [
    "TelegramAPI",
    "AccessControl",
    "StreamState",
    "run_bot",
    "ChatWorkerPool",
]

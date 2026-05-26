"""Configuration loader — reads trinity.toml and provides typed access."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Defaults ─────────────────────────────────────────────────────

DEFAULTS: dict[str, Any] = {
    "company": {
        "name": "My Company",
        "description": "",
        "default_employee": "assistant",
    },
    "auth": {
        "provider": "claude_sdk",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "",
    },
    "agent": {
        "max_turns": 30,
        "max_tokens": 16384,
        "action_timeout": 3600,
        "convo_timeout": 120,
        "default_model": "claude-sonnet-4-6",
        "router_model": "claude-haiku-4-5-20251001",
        "action_model": "claude-sonnet-4-6",
        "judge_model": "claude-opus-4-6",
        "max_retries": 3,
    },
    "telegram": {
        "bot_token_env": "TELEGRAM_BOT_TOKEN",
        "poll_timeout": 30,
        "max_response_length": 4000,
        "streaming_update_interval": 3,
        "streaming_mode": "append",  # "append" = new message per update; "edit" = overwrite a status message
        "acl": {
            "dm_policy": "allowlist",
            "allowed_users": [],
            "group_policy": "allowlist",
        },
        "groups": {},
    },
    "memory": {
        "short_term_decay_hours": 48,
        "long_term_decay_days": 30,
        "max_short_term": 200,
        "max_long_term": 500,
        "chat_history_buffer": 25,
        "chat_history_compress_at": 0,  # 0 = auto (2x buffer)
        "promotion_threshold": 0.8,
        "correction_weight": 2.0,
        "recall_engine": "hybrid",
        "recall_mode": "recent",
        "recall_model": "",
        "recall_provider": "",
        "recall_api_key_env": "",
        "recall_base_url": "",
        "recall_timeout_ms": 5000,
        "recall_max_summary_chars": 220,
        "memory_agent_enabled": True,
        "memory_agent_model": "",
        "share_global": True,
        "shared": {
            "publish_categories": [],
            "subscribe_to_workspaces": [],
            "shared_storage_path": "",
        },
    },
    "scheduler": {
        "enabled": True,
        "cycles": {},
    },
    "employees": {},
    "workspace": {
        "products_dir": ".",
        "exclude_patterns": [
            "node_modules", ".git", "__pycache__", ".next", "dist", "build",
        ],
    },
    "x_platform": {
        "x_username_env": "X_USERNAME",
        "x_password_env": "X_PASS",
        "nim_api_key_env": "NVIDIA_API_KEY",
        "nim_model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "nim_base_url": "https://integrate.api.nvidia.com/v1",
        "headless": True,
        "max_steps": 40,
        "max_failures": 3,
    },
}


# ── Typed config objects ─────────────────────────────────────────

@dataclass
class AuthConfig:
    provider: str = "claude_sdk"
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str = ""

    def get_api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)


@dataclass
class AgentConfig:
    max_turns: int = 30
    max_tokens: int = 16384
    action_timeout: int = 3600
    convo_timeout: int = 120
    default_model: str = "claude-sonnet-4-6"
    router_model: str = "claude-haiku-4-5-20251001"
    action_model: str = "claude-sonnet-4-6"
    judge_model: str = "claude-opus-4-6"
    max_retries: int = 3


@dataclass
class TelegramGroupConfig:
    chat_id: str = ""
    employee: str = ""
    focus: str = ""
    tone: str = ""
    require_mention: bool = False


@dataclass
class TelegramACLConfig:
    dm_policy: str = "allowlist"
    allowed_users: list[int] = field(default_factory=list)
    group_policy: str = "allowlist"


@dataclass
class TelegramConfig:
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    poll_timeout: int = 30
    max_response_length: int = 4000
    streaming_update_interval: int = 3
    streaming_mode: str = "append"
    acl: TelegramACLConfig = field(default_factory=TelegramACLConfig)
    groups: dict[str, TelegramGroupConfig] = field(default_factory=dict)

    def get_bot_token(self) -> str | None:
        return os.environ.get(self.bot_token_env)


@dataclass
class SharedMemoryConfig:
    """Config for cross-workspace memory sharing (Phase 4 sub-project 5)."""
    publish_categories: list[str] = field(default_factory=list)
    subscribe_to_workspaces: list[str] = field(default_factory=list)
    shared_storage_path: str = ""  # e.g. ~/.trinity/shared/


@dataclass
class MemoryConfig:
    short_term_decay_hours: int = 48
    long_term_decay_days: int = 30
    max_short_term: int = 200
    max_long_term: int = 500
    chat_history_buffer: int = 25
    chat_history_compress_at: int = 0  # 0 = use 2x chat_history_buffer
    promotion_threshold: float = 0.8
    correction_weight: float = 2.0
    recall_engine: str = "hybrid"
    recall_mode: str = "recent"
    recall_model: str = ""
    recall_provider: str = ""
    recall_api_key_env: str = ""
    recall_base_url: str = ""
    recall_timeout_ms: int = 5000
    recall_max_summary_chars: int = 220
    memory_agent_enabled: bool = True
    memory_agent_model: str = ""  # Falls back to agent.router_model if empty
    share_global: bool = True  # When False, this workspace neither reads nor writes ~/.trinity/ memories
    shared: SharedMemoryConfig = field(default_factory=SharedMemoryConfig)


@dataclass
class CycleConfig:
    schedule: str = ""
    employee: str = ""
    report_to: str = ""
    type: str = ""
    task: str = ""


@dataclass
class SchedulerConfig:
    enabled: bool = True
    cycles: dict[str, CycleConfig] = field(default_factory=dict)


@dataclass
class EmployeeConfig:
    title: str = ""
    model: str = ""


@dataclass
class CompanyConfig:
    name: str = "My Company"
    description: str = ""
    default_employee: str = "assistant"


@dataclass
class WorkspaceConfig:
    products_dir: str = "."
    exclude_patterns: list[str] = field(default_factory=lambda: [
        "node_modules", ".git", "__pycache__", ".next", "dist", "build",
    ])


@dataclass
class XPlatformConfig:
    x_username_env: str = "X_USERNAME"
    x_password_env: str = "X_PASS"
    nim_api_key_env: str = "NVIDIA_API_KEY"
    nim_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    headless: bool = True
    max_steps: int = 40
    max_failures: int = 3


@dataclass
class TrinityConfig:
    """Top-level configuration object."""
    company: CompanyConfig = field(default_factory=CompanyConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    employees: dict[str, EmployeeConfig] = field(default_factory=dict)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    x_platform: XPlatformConfig = field(default_factory=XPlatformConfig)

    # Runtime paths (set after loading)
    workspace_root: Path = field(default_factory=lambda: Path.cwd())
    trinity_dir: Path = field(default_factory=lambda: Path.cwd() / ".trinity")
    global_trinity_dir: Path | None = None  # ~/.trinity/ — shared memory across all agents


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base recursively."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _parse_groups(raw: dict) -> dict[str, TelegramGroupConfig]:
    groups = {}
    for name, cfg in raw.items():
        if isinstance(cfg, dict):
            groups[name] = TelegramGroupConfig(
                chat_id=str(cfg.get("chat_id", "")),
                employee=cfg.get("employee", ""),
                focus=cfg.get("focus", ""),
                tone=cfg.get("tone", ""),
                require_mention=cfg.get("require_mention", False),
            )
    return groups


def _parse_cycles(raw: dict) -> dict[str, CycleConfig]:
    cycles = {}
    for name, cfg in raw.items():
        if isinstance(cfg, dict):
            cycles[name] = CycleConfig(
                schedule=cfg.get("schedule", ""),
                employee=cfg.get("employee", ""),
                report_to=cfg.get("report_to", ""),
                type=cfg.get("type", ""),
                task=cfg.get("task", ""),
            )
    return cycles


def _parse_employees(raw: dict) -> dict[str, EmployeeConfig]:
    employees = {}
    for name, cfg in raw.items():
        if isinstance(cfg, dict):
            employees[name] = EmployeeConfig(
                title=cfg.get("title", ""),
                model=cfg.get("model", ""),
            )
    return employees


def load_config(workspace_root: Path | None = None) -> TrinityConfig:
    """Load trinity.toml from the workspace root directory."""
    root = workspace_root or Path.cwd()
    config_path = root / "trinity.toml"

    raw: dict[str, Any] = {}
    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                raw = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise SystemExit(
                f"trinity.toml parse error in {config_path}:\n  {e}\n"
                "Fix the syntax and run again."
            ) from None
        except OSError as e:
            raise SystemExit(
                f"Could not read {config_path}: {e}"
            ) from None

    merged = _deep_merge(DEFAULTS, raw)

    # Build telegram config
    tg_raw = merged.get("telegram", {})
    acl_raw = tg_raw.get("acl", {})
    groups_raw = tg_raw.get("groups", {})

    acl = TelegramACLConfig(
        dm_policy=acl_raw.get("dm_policy", "allowlist"),
        allowed_users=acl_raw.get("allowed_users", []),
        group_policy=acl_raw.get("group_policy", "allowlist"),
    )

    telegram = TelegramConfig(
        bot_token_env=tg_raw.get("bot_token_env", "TELEGRAM_BOT_TOKEN"),
        poll_timeout=tg_raw.get("poll_timeout", 30),
        max_response_length=tg_raw.get("max_response_length", 4000),
        streaming_update_interval=tg_raw.get("streaming_update_interval", 8),
        streaming_mode=tg_raw.get("streaming_mode", "append"),
        acl=acl,
        groups=_parse_groups(groups_raw),
    )

    # Build scheduler config
    sched_raw = merged.get("scheduler", {})
    scheduler = SchedulerConfig(
        enabled=sched_raw.get("enabled", True),
        cycles=_parse_cycles(sched_raw.get("cycles", {})),
    )

    # Build agent config
    ag = merged.get("agent", {})
    agent = AgentConfig(**{k: ag[k] for k in AgentConfig.__dataclass_fields__ if k in ag})

    # Build auth config
    au = merged.get("auth", {})
    auth = AuthConfig(**{k: au[k] for k in AuthConfig.__dataclass_fields__ if k in au})

    # Build company config
    co = merged.get("company", {})
    company = CompanyConfig(**{k: co[k] for k in CompanyConfig.__dataclass_fields__ if k in co})

    # Build memory config
    mem = merged.get("memory", {})
    shared_raw = mem.get("shared", {}) if isinstance(mem.get("shared", {}), dict) else {}
    shared_cfg = SharedMemoryConfig(
        publish_categories=list(shared_raw.get("publish_categories", []) or []),
        subscribe_to_workspaces=list(shared_raw.get("subscribe_to_workspaces", []) or []),
        shared_storage_path=str(shared_raw.get("shared_storage_path", "") or ""),
    )
    memory_kwargs = {
        k: mem[k]
        for k in MemoryConfig.__dataclass_fields__
        if k in mem and k != "shared"
    }
    memory = MemoryConfig(shared=shared_cfg, **memory_kwargs)

    # Build workspace config
    ws = merged.get("workspace", {})
    workspace_cfg = WorkspaceConfig(
        products_dir=ws.get("products_dir", "."),
        exclude_patterns=ws.get("exclude_patterns", DEFAULTS["workspace"]["exclude_patterns"]),
    )

    # Build x_platform config
    xp = merged.get("x_platform", {})
    x_platform = XPlatformConfig(**{k: xp[k] for k in XPlatformConfig.__dataclass_fields__ if k in xp})

    trinity_dir = root / ".trinity"

    # Global shared memory: ~/.trinity/ — but only if the workspace is NOT
    # the home dir itself (to avoid reading the same dir twice).
    home = Path.home()
    global_trinity_dir: Path | None = None
    if memory.share_global and root.resolve() != home.resolve():
        candidate = home / ".trinity"
        if candidate.exists():
            global_trinity_dir = candidate

    return TrinityConfig(
        company=company,
        auth=auth,
        agent=agent,
        telegram=telegram,
        memory=memory,
        scheduler=scheduler,
        employees=_parse_employees(merged.get("employees", {})),
        workspace=workspace_cfg,
        x_platform=x_platform,
        workspace_root=root,
        trinity_dir=trinity_dir,
        global_trinity_dir=global_trinity_dir,
    )

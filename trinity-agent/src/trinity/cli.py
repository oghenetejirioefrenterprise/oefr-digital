"""Trinity CLI — init, start, run, employee, auth, status, memory, knowledge."""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path


def _looks_like_secret(value: str) -> bool:
    """Return True if *value* looks like a raw secret rather than an env var name."""
    # Telegram tokens: digits:alphanum, API keys: sk-..., long base64-ish strings
    if ":" in value:
        return True
    if value.startswith(("sk-", "sk_")):
        return True
    if len(value) > 30 and not value.replace("_", "").isupper():
        return True
    return False


def _append_env(env_path: Path, key: str, value: str) -> None:
    """Append a KEY=VALUE line to a .env file, avoiding duplicates."""
    lines = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    # Remove existing entry for this key
    lines = [l for l in lines if not l.startswith(f"{key}=")]
    lines.append(f'{key}="{value}"')
    env_path.write_text("\n".join(lines) + "\n")


def _load_dotenv(workspace: Path) -> None:
    """Source a .env file into os.environ (simple KEY="VALUE" parsing)."""
    env_path = workspace / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main():
    parser = argparse.ArgumentParser(
        prog="trinity",
        description="Trinity Agent — a portable AI agent for your workspace",
    )
    parser.add_argument(
        "--workspace", "-w", default=None,
        help="Workspace root (default: current directory)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    sub = parser.add_subparsers(dest="command")

    # ── init ──────────────────────────────────────────────
    p_init = sub.add_parser("init", help="Initialize a Trinity workspace")
    p_init.add_argument("--from-openclaw", action="store_true",
                        help="Migrate from OpenClaw")

    # ── start ─────────────────────────────────────────────
    p_start = sub.add_parser("start", help="Start Telegram bot + scheduler (add --daemon to run in background)")
    p_start.add_argument("--daemon", action="store_true",
                         help="Run in background (detach from terminal)")

    # ── stop ──────────────────────────────────────────────
    sub.add_parser("stop", help="Stop a running daemon")

    # ── restart ───────────────────────────────────────────
    p_restart = sub.add_parser("restart", help="Restart the daemon")
    p_restart.add_argument("--foreground", action="store_true",
                           help="Restart in foreground instead of daemon mode")

    # ── run ───────────────────────────────────────────────
    p_run = sub.add_parser("run", help="Run a one-shot task")
    p_run.add_argument("task", help="Task description")
    p_run.add_argument("--employee", "-e", default=None,
                       help="Employee to use")

    # ── status ────────────────────────────────────────────
    sub.add_parser("status", help="Show current state")

    # ── employee ──────────────────────────────────────────
    p_emp = sub.add_parser("employee", help="Manage employees")
    emp_sub = p_emp.add_subparsers(dest="employee_cmd")
    emp_sub.add_parser("list", help="List all employees")
    p_emp_add = emp_sub.add_parser("add", help="Add an employee")
    p_emp_add.add_argument("--name", help="Employee name")
    p_emp_add.add_argument("--title", help="Title (CEO, CMO, CTO, etc.)")
    p_emp_edit = emp_sub.add_parser("edit", help="Edit employee identity")
    p_emp_edit.add_argument("name", help="Employee name")
    p_emp_rm = emp_sub.add_parser("remove", help="Remove an employee")
    p_emp_rm.add_argument("name", help="Employee name")

    # ── auth ──────────────────────────────────────────────
    p_auth = sub.add_parser("auth", help="Manage authentication")
    auth_sub = p_auth.add_subparsers(dest="auth_cmd")
    auth_sub.add_parser("status", help="Show auth state")
    p_auth_switch = auth_sub.add_parser("switch", help="Switch provider")
    p_auth_switch.add_argument("provider",
                               choices=["claude_sdk", "anthropic_api", "openai", "openrouter"])

    # ── memory ────────────────────────────────────────────
    p_mem = sub.add_parser("memory", help="Memory operations")
    mem_sub = p_mem.add_subparsers(dest="memory_cmd")
    p_mem_search = mem_sub.add_parser("search", help="Search memories")
    p_mem_search.add_argument("query", help="Search term")
    mem_sub.add_parser("stats", help="Memory statistics")

    # ── knowledge ─────────────────────────────────────────
    p_kb = sub.add_parser("knowledge", help="Knowledge base operations")
    p_kb.add_argument("args", nargs="*", help="Knowledge CLI arguments")

    # ── workspaces ───────────────────────────────────────
    p_ws = sub.add_parser("workspaces", help="Cross-workspace registry for the memory agent")
    ws_sub = p_ws.add_subparsers(dest="workspaces_cmd")
    ws_sub.add_parser("list", help="List registered workspaces")
    ws_sub.add_parser("rescan", help="Rescan ~/apps for workspaces and refresh the registry")

    # ── board (kanban) ───────────────────────────────────
    from trinity.kanban.cli import add_subparser as _add_board
    _add_board(sub)

    # ── plugins ──────────────────────────────────────────
    p_plug = sub.add_parser("plugins", help="Plugin inspection")
    plug_sub = p_plug.add_subparsers(dest="plug_cmd", required=True)

    p_plug_list = plug_sub.add_parser("list", help="List registered plugins")
    p_plug_list.add_argument(
        "group",
        nargs="?",
        choices=["providers", "tools", "agents"],
        help="Limit output to a single group",
    )

    p_plug_show = plug_sub.add_parser(
        "show", help="Show details for a single plugin (group/name)"
    )
    p_plug_show.add_argument("spec", help="Plugin reference in 'group/name' form")

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Scrub common secret shapes from every log record before it hits a handler.
    from trinity._safety import install_redaction_filter
    install_redaction_filter()

    workspace = Path(args.workspace) if args.workspace else Path.cwd()

    if args.command == "init":
        cmd_init(workspace, from_openclaw=args.from_openclaw)
    elif args.command == "start":
        cmd_start(workspace, daemon=args.daemon)
    elif args.command == "stop":
        cmd_stop(workspace)
    elif args.command == "restart":
        cmd_restart(workspace, foreground=args.foreground)
    elif args.command == "run":
        cmd_run(workspace, args.task, args.employee)
    elif args.command == "status":
        cmd_status(workspace)
    elif args.command == "employee":
        cmd_employee(workspace, args)
    elif args.command == "auth":
        cmd_auth(workspace, args)
    elif args.command == "memory":
        cmd_memory(workspace, args)
    elif args.command == "knowledge":
        cmd_knowledge(workspace, args)
    elif args.command == "workspaces":
        cmd_workspaces(workspace, args)
    elif args.command == "plugins":
        _run_plugins(args)
    elif args.command == "board":
        from trinity.kanban.cli import dispatch as _board_dispatch
        _board_dispatch(workspace, args)
    else:
        parser.print_help()


# ── Command implementations ──────────────────────────────────────

def cmd_init(workspace: Path, from_openclaw: bool = False):
    """Interactive onboarding wizard."""
    print()
    print("  Trinity Agent — Setup Wizard")
    print("  " + "=" * 34)
    print()

    # Step 1: Authentication
    print("  Step 1/4: Authentication\n")
    print("  How do you want to connect to an LLM?\n")
    print("  [1] Claude Agent SDK (recommended — full agent with built-in tools)")
    print("  [2] Anthropic API key")
    print("  [3] OpenAI API key")
    print("  [4] OpenRouter API key (use any model)")
    print()

    auth_choice = input("  > ").strip()
    provider = "claude_sdk"
    api_key_env = "ANTHROPIC_API_KEY"
    base_url = ""

    if auth_choice == "1" or not auth_choice:
        provider = "claude_sdk"
        api_key_env = ""
        print()
        print("  Using your Claude Code subscription (no API key needed).")
        print("  The Agent SDK handles the full agent loop —")
        print("  built-in tools (Read, Write, Edit, Bash, Grep, etc.)")
        print("  are executed by the SDK automatically.")
    elif auth_choice == "2":
        provider = "anthropic_api"
        key_input = input("  Anthropic API key or env var [ANTHROPIC_API_KEY]: ").strip()
        key_input = key_input or "ANTHROPIC_API_KEY"
        if _looks_like_secret(key_input):
            api_key_env = "ANTHROPIC_API_KEY"
            _append_env(workspace / ".env", api_key_env, key_input)
            print(f"  Key saved to .env as {api_key_env}")
        else:
            api_key_env = key_input
    elif auth_choice == "3":
        provider = "openai"
        key_input = input("  OpenAI API key or env var [OPENAI_API_KEY]: ").strip()
        key_input = key_input or "OPENAI_API_KEY"
        if _looks_like_secret(key_input):
            api_key_env = "OPENAI_API_KEY"
            _append_env(workspace / ".env", api_key_env, key_input)
            print(f"  Key saved to .env as {api_key_env}")
        else:
            api_key_env = key_input
    elif auth_choice == "4":
        provider = "openrouter"
        key_input = input("  OpenRouter API key or env var [OPENROUTER_API_KEY]: ").strip()
        key_input = key_input or "OPENROUTER_API_KEY"
        if _looks_like_secret(key_input):
            api_key_env = "OPENROUTER_API_KEY"
            _append_env(workspace / ".env", api_key_env, key_input)
            print(f"  Key saved to .env as {api_key_env}")
        else:
            api_key_env = key_input
        base_url = "https://openrouter.ai/api/v1"
    else:
        print(f"  Unknown option '{auth_choice}', defaulting to Claude Agent SDK.")
        provider = "claude_sdk"

    if api_key_env and not os.environ.get(api_key_env):
        print(f"\n  Warning: {api_key_env} is not set in your environment.")
        print(f"  Set it before running `trinity start`.\n")

    # Step 2: Company
    print("\n  Step 2/4: Company Identity\n")
    company_name = input("  Company/project name: ").strip() or "My Company"
    company_desc = input("  One-sentence description: ").strip()

    # Step 3: Employees
    print("\n  Step 3/4: Create Employees\n")
    print("  Available titles:")
    titles = ["CEO", "CMO", "CTO", "CFO", "COO", "Research IC",
              "SEO Operator", "Product Mgr", "Custom"]
    for t in titles:
        print(f"    {t}")
    print()

    employees = []
    while True:
        title = input("  Title (or 'done'): ").strip()
        if title.lower() == "done" or not title:
            break
        matched = [t for t in titles if t.lower() == title.lower()]
        if matched:
            title = matched[0]
        else:
            print(f"  Unknown title: {title}")
            continue

        name = input(f"  Name for {title}: ").strip().lower().replace(" ", "_")
        if not name:
            continue
        employees.append({"name": name, "title": title})
        print(f"  Created: {name} ({title})\n")

    if not employees:
        employees.append({"name": "assistant", "title": "CEO"})
        print("  No employees created — added default 'assistant' (CEO)\n")

    # Step 4: Telegram
    print("\n  Step 4/4: Telegram (optional)\n")
    setup_telegram = input("  Connect a Telegram bot? (y/n): ").strip().lower()
    bot_token_env = ""
    allowed_users = []
    if setup_telegram == "y":
        token_input = input("  Bot token or env var name [TELEGRAM_BOT_TOKEN]: ").strip()
        token_input = token_input or "TELEGRAM_BOT_TOKEN"

        # Detect if user pasted an actual token (digits:alphanumeric) vs env var name
        if ":" in token_input:
            # Raw token — write to .env and use a standard env var name
            bot_token_env = "TELEGRAM_BOT_TOKEN"
            env_path = workspace / ".env"
            _append_env(env_path, bot_token_env, token_input)
            print(f"\n  Token saved to .env as {bot_token_env}")
        else:
            bot_token_env = token_input

        user_id = input("  Your Telegram user ID: ").strip()
        if user_id.isdigit():
            allowed_users.append(int(user_id))

    # ── Generate files ────────────────────────────────────
    trinity_dir = workspace / ".trinity"
    for subdir in [
        "employees", "memory/permanent", "memory/long-term", "memory/short-term",
        "knowledge", "sessions", "chat-history", "logs", "state",
    ]:
        (trinity_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Create employee identities
    from trinity.employees.registry import create_employee
    for emp in employees:
        create_employee(
            trinity_dir, emp["name"], emp["title"],
            company_name, company_desc,
        )

    # Generate trinity.toml
    toml_lines = [
        '[company]',
        f'name = "{company_name}"',
        f'description = "{company_desc}"',
        f'default_employee = "{employees[0]["name"]}"',
        '',
        '[auth]',
        f'provider = "{provider}"',
        f'api_key_env = "{api_key_env}"',
    ]
    if base_url:
        toml_lines.append(f'base_url = "{base_url}"')

    toml_lines += [
        '', '[agent]',
        'max_turns = 30',
        'max_tokens = 16384',
        'default_model = "claude-sonnet-4-6"',
        'router_model = "claude-haiku-4-5-20251001"',
        'action_model = "claude-sonnet-4-6"',
    ]

    if bot_token_env:
        toml_lines += [
            '', '[telegram]',
            f'bot_token_env = "{bot_token_env}"',
            '', '[telegram.acl]',
            'dm_policy = "allowlist"',
            f'allowed_users = [{", ".join(str(u) for u in allowed_users)}]',
            'group_policy = "allowlist"',
        ]

    for emp in employees:
        toml_lines += [
            '', f'[employees.{emp["name"]}]',
            f'title = "{emp["title"]}"',
        ]

    toml_lines += [
        '', '[memory]',
        'short_term_decay_hours = 48',
        'long_term_decay_days = 30',
        'chat_history_buffer = 10',
        '', '[scheduler]',
        'enabled = true',
    ]

    config_path = workspace / "trinity.toml"
    config_path.write_text("\n".join(toml_lines) + "\n")

    # Initialize knowledge files
    from trinity.knowledge.wiki import init_knowledge
    init_knowledge(trinity_dir)

    # Initialize memory index
    index_path = trinity_dir / "memory" / "index.json"
    if not index_path.exists():
        index_path.write_text("[]")

    print()
    print("  " + "=" * 34)
    print("  Setup complete!")
    print(f"  Created: trinity.toml, .trinity/")
    print(f"  Employees: {', '.join(e['name'] + ' (' + e['title'] + ')' for e in employees)}")
    print()
    print("  Next steps:")
    print("    trinity start              # Start the agent")
    print("    trinity employee add       # Add more employees")
    print("    trinity run 'hello'        # Test a one-shot task")
    print("  " + "=" * 34)
    print()


def cmd_start(workspace: Path, daemon: bool = False):
    """Start the Telegram bot + scheduler."""
    _load_dotenv(workspace)
    if daemon:
        # Daemon mode: re-launch ourselves in the background
        pid_dir = workspace / ".trinity" / "state"
        pid_dir.mkdir(parents=True, exist_ok=True)
        pid_file = pid_dir / "trinity.pid"

        # Build the command to re-launch without --daemon
        cmd = [sys.executable, "-m", "trinity", "--workspace", str(workspace), "start"]
        log_path = workspace / ".trinity" / "logs" / "daemon.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "a") as log_fh:
            proc = subprocess.Popen(
                cmd,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        pid_file.write_text(str(proc.pid))
        print(f"Trinity started in background (PID {proc.pid})")
        print(f"  PID file: {pid_file}")
        print(f"  Log file: {log_path}")
        return

    from trinity.config import load_config
    from trinity.app import init, handle_message, run_cycle
    from trinity.telegram.bot import run_bot
    from trinity.scheduler.engine import Scheduler

    config = load_config(workspace)
    init(config)

    # Write PID for foreground mode too (useful for monitoring)
    pid_file = config.trinity_dir / "state" / "trinity.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))

    scheduler = Scheduler(config, run_cycle)
    scheduler.start()

    # Start commitments runtime if Telegram is configured.
    commitments_runtime = None
    token = config.telegram.get_bot_token()
    if token:
        from trinity.commitments.runtime import CommitmentsRuntime
        from trinity.telegram.api import TelegramAPI
        commitments_runtime = CommitmentsRuntime(
            trinity_dir=config.trinity_dir,
            api=TelegramAPI(token),
            poll_interval_seconds=60,
        )
        commitments_runtime.start()

    if config.telegram.get_bot_token():
        print(f"Starting Trinity in {workspace}")
        # Supervisor loop: restart run_bot on unhandled exceptions with
        # exponential backoff. SIGTERM/SIGINT exit cleanly via the signal
        # handler inside run_bot (sets running=False, returns normally).
        import logging as _logging
        _log = _logging.getLogger("trinity.cli")
        restart_count = 0
        while True:
            try:
                run_bot(config, handle_message)
                _log.info("run_bot returned cleanly — exiting supervisor")
                break
            except KeyboardInterrupt:
                _log.info("Supervisor: KeyboardInterrupt — exiting")
                break
            except Exception:
                restart_count += 1
                wait = min(5 * (2 ** (restart_count - 1)), 120)
                _log.exception(
                    "Supervisor: run_bot crashed (restart %d) — retrying in %ds",
                    restart_count, wait,
                )
                time.sleep(wait)
    else:
        print("No Telegram bot token configured.")
        if config.scheduler.enabled:
            print("Scheduler running. Press Ctrl+C to stop.")
            import signal
            signal.pause()


def _read_pid(workspace: Path) -> int | None:
    """Read the PID from .trinity/state/trinity.pid, return None if stale or missing."""
    pid_file = workspace / ".trinity" / "state" / "trinity.pid"
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # check if process exists
        return pid
    except (ValueError, OSError):
        return None


def cmd_stop(workspace: Path) -> bool:
    """Stop a running daemon. Returns True if a process was stopped."""
    import signal as _signal
    import time

    pid = _read_pid(workspace)
    if pid is None:
        print("No running Trinity process found.")
        return False

    print(f"Stopping Trinity (PID {pid})...")
    try:
        os.kill(pid, _signal.SIGTERM)
        # Wait up to 5 seconds for clean shutdown
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            # Still alive — force kill
            os.kill(pid, _signal.SIGKILL)
    except OSError:
        pass

    pid_file = workspace / ".trinity" / "state" / "trinity.pid"
    if pid_file.exists():
        pid_file.unlink()

    print("Stopped.")
    return True


def cmd_restart(workspace: Path, foreground: bool = False):
    """Stop the running daemon, then start again."""
    cmd_stop(workspace)
    if foreground:
        cmd_start(workspace, daemon=False)
    else:
        cmd_start(workspace, daemon=True)


def cmd_run(workspace: Path, task: str, employee: str | None):
    """Run a one-shot task."""
    _load_dotenv(workspace)
    from trinity.config import load_config
    from trinity.app import init
    from trinity.agents.builder import run as builder_run
    from trinity.employees.loader import load_full_identity
    from trinity.knowledge.wiki import load_for_identity
    from trinity.tools.registry import TOOL_DEFINITIONS, execute_tool

    config = load_config(workspace)
    provider = init(config)

    employee_name = employee or config.company.default_employee
    briefing = load_for_identity(config.trinity_dir)
    system = load_full_identity(
        config.trinity_dir, employee_name, config.company, briefing,
        workspace_root=config.workspace_root,
    )

    result = builder_run(
        provider=provider,
        config=config,
        system=system,
        task=task,
        tool_definitions=TOOL_DEFINITIONS,
        tool_executor=execute_tool,
    )
    print(result)


def cmd_status(workspace: Path):
    """Show current state."""
    _load_dotenv(workspace)
    from trinity.config import load_config
    config = load_config(workspace)

    print(f"Workspace: {workspace}")
    print(f"Provider:  {config.auth.provider}")
    print(f"Company:   {config.company.name}")

    emp_dir = config.trinity_dir / "employees"
    if emp_dir.exists():
        employees = [d.name for d in emp_dir.iterdir() if d.is_dir()]
        print(f"Employees: {', '.join(employees) or '(none)'}")

    index = config.trinity_dir / "memory" / "index.json"
    if index.exists():
        try:
            data = json.loads(index.read_text())
            tiers = {}
            for m in data:
                t = m.get("tier", "?")
                tiers[t] = tiers.get(t, 0) + 1
            print(f"Memories:  {sum(tiers.values())} total ({tiers})")
        except (json.JSONDecodeError, OSError):
            print("Memories:  (index unreadable)")

    token = config.telegram.get_bot_token()
    print(f"Telegram:  {'configured' if token else 'not configured'}")
    print(f"Groups:    {len(config.telegram.groups)}")
    print(f"Scheduler: {'enabled' if config.scheduler.enabled else 'disabled'}")
    print(f"Cycles:    {len(config.scheduler.cycles)}")


def cmd_employee(workspace: Path, args):
    """Employee management."""
    from trinity.config import load_config
    config = load_config(workspace)

    if args.employee_cmd == "list":
        from trinity.employees.registry import list_employees
        emps = list_employees(config.trinity_dir)
        if not emps:
            print("No employees found.")
            return
        for e in emps:
            print(f"  {e['name']:20s} {e.get('title', '?')}")

    elif args.employee_cmd == "add":
        name = args.name or input("Employee name: ").strip().lower().replace(" ", "_")
        title = args.title or input("Title: ").strip()
        from trinity.employees.registry import create_employee
        path = create_employee(
            config.trinity_dir, name, title,
            config.company.name, config.company.description,
        )
        print(f"Created {name} ({title})")
        print(f"Identity: {path}")

    elif args.employee_cmd == "edit":
        identity = config.trinity_dir / "employees" / args.name / "identity.md"
        if not identity.exists():
            print(f"Employee '{args.name}' not found.")
            return
        editor = os.environ.get("EDITOR", "nano")
        subprocess.run([editor, str(identity)])

    elif args.employee_cmd == "remove":
        from trinity.employees.registry import remove_employee
        if remove_employee(config.trinity_dir, args.name):
            print(f"Removed {args.name}")
        else:
            print(f"Employee '{args.name}' not found.")
    else:
        print("Usage: trinity employee [list|add|edit|remove]")


def cmd_auth(workspace: Path, args):
    """Auth management."""
    from trinity.config import load_config
    config = load_config(workspace)

    if args.auth_cmd == "status":
        print(f"Provider: {config.auth.provider}")
        key = config.auth.get_api_key()
        if key:
            print(f"API key:  {config.auth.api_key_env} = {key[:8]}...{key[-4:]}")
        else:
            print(f"API key:  {config.auth.api_key_env} (NOT SET)")
    elif args.auth_cmd == "switch":
        import re
        toml_path = workspace / "trinity.toml"
        if toml_path.exists():
            content = toml_path.read_text()
            content = re.sub(
                r'provider\s*=\s*"[^"]*"',
                f'provider = "{args.provider}"',
                content,
            )
            toml_path.write_text(content)
            print(f"Switched to {args.provider}")
        else:
            print("No trinity.toml found. Run `trinity init` first.")
    else:
        print("Usage: trinity auth [status|switch]")


def cmd_memory(workspace: Path, args):
    """Memory operations."""
    from trinity.config import load_config
    config = load_config(workspace)

    if args.memory_cmd == "search":
        from trinity.memory.search import search_memories
        results = search_memories(config.trinity_dir, args.query, global_trinity_dir=config.global_trinity_dir)
        if not results:
            print("No results.")
            return
        for r in results:
            source_tag = f" ({r['source']})" if r.get("source", "local") != "local" else ""
            print(f"  [{r['tier']}] {r['segment']} — {r['summary']}{source_tag}")
            print(f"    Score: {r['score']:.2f} | ID: {r['id']}")
            print()

    elif args.memory_cmd == "stats":
        from trinity.memory.store import list_memories
        memories = list_memories(config.trinity_dir)
        tiers = {}
        segments = {}
        for m in memories:
            t = m.get("tier", "?")
            s = m.get("segment", "?")
            tiers[t] = tiers.get(t, 0) + 1
            segments[s] = segments.get(s, 0) + 1
        print(f"Total: {len(memories)}")
        print(f"By tier: {tiers}")
        print(f"By segment: {segments}")
    else:
        print("Usage: trinity memory [search|stats]")


def cmd_knowledge(workspace: Path, args):
    """Knowledge base CLI passthrough."""
    from trinity.config import load_config
    config = load_config(workspace)
    sys.argv = ["trinity-knowledge"] + (args.args or [])
    from trinity.knowledge.cli import main as kb_main
    kb_main()


def cmd_workspaces(workspace: Path, args):
    """Show or refresh the cross-workspace registry."""
    from trinity.workspaces import list_workspaces, rescan

    sub = getattr(args, "workspaces_cmd", None) or "list"

    if sub == "rescan":
        reg = rescan(current=workspace)
        print(f"Rescanned ~/apps — {len(reg)} workspace(s) registered (excluding current).")
        sub = "list"

    if sub == "list":
        reg = list_workspaces(current=workspace)
        if not reg:
            print("No other workspaces registered. Run `trinity workspaces rescan` to discover them.")
            return
        print(f"Registered workspaces (excluding current: {workspace.name}):\n")
        for name, info in reg.items():
            company = info.get("company", "(no company)")
            path = info.get("path", "?")
            last = info.get("last_seen", "?")
            print(f"  • {name}")
            print(f"      company:   {company}")
            print(f"      path:      {path}")
            print(f"      last seen: {last}\n")


def _run_plugins(args):
    """Dispatch `trinity plugins <subcommand>`."""
    if args.plug_cmd == "list":
        _plugins_list(args.group)
    elif args.plug_cmd == "show":
        _plugins_show(args.spec)


def _plugins_list(group: str | None) -> None:
    from trinity.agents.registry import AGENTS
    from trinity.providers.registry import PROVIDERS
    from trinity.tools.registry import TOOLS

    groups = {"providers": PROVIDERS, "tools": TOOLS, "agents": AGENTS}
    if group:
        if group not in groups:
            print(f"Unknown group: {group}. Choose from: {list(groups)}")
            raise SystemExit(2)
        selected = {group: groups[group]}
    else:
        selected = groups

    for label, reg in selected.items():
        print(f"\n{label}:")
        if not reg.names():
            print("  (none registered)")
            continue
        for name in reg.names():
            src = reg.source_of(name)
            desc = getattr(reg.get(name), "description", "") or ""
            if desc:
                print(f"  {name:<28} [{src}]  {desc}")
            else:
                print(f"  {name:<28} [{src}]")


def _plugins_show(spec: str) -> None:
    from trinity.agents.registry import AGENTS
    from trinity.providers.registry import PROVIDERS
    from trinity.tools.registry import TOOLS

    groups = {"providers": PROVIDERS, "tools": TOOLS, "agents": AGENTS}
    if "/" not in spec:
        print(f"Expected 'group/name', got: {spec!r}")
        raise SystemExit(2)
    group, _, name = spec.partition("/")
    if group not in groups:
        print(f"Unknown group: {group}. Choose from: {list(groups)}")
        raise SystemExit(2)
    reg = groups[group]
    if name not in reg:
        print(f"Not registered in {group}: {name!r}")
        print(f"Known: {reg.names()}")
        raise SystemExit(1)
    item = reg.get(name)
    print(f"Group:       {group}")
    print(f"Name:        {name}")
    print(f"Source:      {reg.source_of(name)}")
    for attr in ("description", "kind", "tool_subset", "requires_api_key"):
        if hasattr(item, attr):
            value = getattr(item, attr)
            if value not in (None, ""):
                print(f"{attr.replace('_', ' ').title() + ':':<12} {value}")


if __name__ == "__main__":
    main()

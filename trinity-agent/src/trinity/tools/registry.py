"""Central tool registry.

Tools register as :class:`trinity.plugins.ToolSpec` entries in the module-level
``TOOLS`` registry at import time. Third-party packages can add more via the
``trinity.tools`` entry-point group.

Back-compat exports — every symbol that pre-migration callers use:
  * ``TOOL_DEFINITIONS`` — list of Anthropic-format schema dicts
  * ``BUILDER_TOOLS`` / ``RESEARCHER_TOOLS`` / ``MEMORY_TOOLS`` — name lists
  * ``get_tools(names)`` — filtered definition list
  * ``execute_tool(name, input, workspace_root, **context)`` — dispatcher
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from trinity.plugins import Registry, ToolSpec
from trinity.tools import (
    filesystem,
    git,
    knowledge_tools,
    memory_tools,
    search,
    shell,
    telegram_tools,
    web,
)


TOOLS: Registry[ToolSpec] = Registry("trinity.tools")


# ── Builtin tool specs ────────────────────────────────────────────────

_BUILTIN_SPECS: list[ToolSpec] = [
    # Filesystem
    ToolSpec(
        name="read_file",
        definition={
            "name": "read_file",
            "description": (
                "Read a file's contents with line numbers. Returns up to 50 KB. "
                "Path is relative to the workspace root."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to workspace root.",
                    },
                },
                "required": ["path"],
            },
        },
        handler=lambda inp, ws, **_: filesystem.read_file(inp["path"], ws),
        subsets=("builder", "researcher"),
    ),
    ToolSpec(
        name="write_file",
        definition={
            "name": "write_file",
            "description": (
                "Create or overwrite a file. Creates parent directories "
                "automatically. Path is relative to the workspace root."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to workspace root.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The full file content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
        handler=lambda inp, ws, **_: filesystem.write_file(
            inp["path"], inp["content"], ws
        ),
        subsets=("builder",),
    ),
    ToolSpec(
        name="edit_file",
        definition={
            "name": "edit_file",
            "description": (
                "Find and replace text in an existing file. old_text must appear "
                "exactly once."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to workspace root.",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to find (must appear exactly once).",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
        handler=lambda inp, ws, **_: filesystem.edit_file(
            inp["path"], inp["old_text"], inp["new_text"], ws
        ),
        subsets=("builder",),
    ),
    ToolSpec(
        name="list_directory",
        definition={
            "name": "list_directory",
            "description": (
                "List the contents of a directory, showing types, names, sizes. "
                "Path is relative to workspace root. Use '.' for root."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to workspace root.",
                    },
                },
                "required": ["path"],
            },
        },
        handler=lambda inp, ws, **_: filesystem.list_directory(inp["path"], ws),
        subsets=("builder", "researcher"),
    ),

    # Search
    ToolSpec(
        name="search_files",
        definition={
            "name": "search_files",
            "description": (
                "Find files by glob pattern (e.g. '*.py', '**/*.tsx'). "
                "Returns matching paths. Skips node_modules, .git, __pycache__, .next, dist, build."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search, relative to workspace. Defaults to '.'.",
                    },
                },
                "required": ["pattern"],
            },
        },
        handler=lambda inp, ws, **_: search.search_files(
            inp["pattern"], inp.get("path", "."), ws
        ),
        subsets=("builder", "researcher"),
    ),
    ToolSpec(
        name="search_content",
        definition={
            "name": "search_content",
            "description": (
                "Search file contents using a regex. Returns filename:line:match. "
                "Skips binary files and excluded directories."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search. Defaults to '.'.",
                    },
                    "file_type": {
                        "type": "string",
                        "description": "File extension without the dot (e.g. 'py').",
                    },
                },
                "required": ["pattern"],
            },
        },
        handler=lambda inp, ws, **_: search.search_content(
            inp["pattern"],
            inp.get("path", "."),
            ws,
            file_type=inp.get("file_type", ""),
        ),
        subsets=("builder", "researcher"),
    ),

    # Shell
    ToolSpec(
        name="run_command",
        definition={
            "name": "run_command",
            "description": (
                "Run a shell command via bash and return stdout + stderr. "
                "Default timeout 120s, max 600s."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (workspace-relative or absolute).",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds.",
                    },
                },
                "required": ["command"],
            },
        },
        handler=lambda inp, ws, **_: shell.run_command(
            inp["command"],
            ws,
            cwd=inp.get("cwd", ""),
            timeout=min(inp.get("timeout", 120), 600),
        ),
        subsets=("builder", "researcher"),
    ),

    # Git
    ToolSpec(
        name="git_status",
        definition={
            "name": "git_status",
            "description": "Show the working tree status of the workspace git repo.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        handler=lambda inp, ws, **_: git.git_status(ws),
        subsets=("builder",),
    ),
    ToolSpec(
        name="git_diff",
        definition={
            "name": "git_diff",
            "description": "Show git diff output. Supports --stat, --staged, HEAD~N, paths.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "string",
                        "description": "Arguments passed through to git diff.",
                    },
                },
                "required": [],
            },
        },
        handler=lambda inp, ws, **_: git.git_diff(ws, args=inp.get("args", "")),
        subsets=("builder",),
    ),
    ToolSpec(
        name="git_commit",
        definition={
            "name": "git_commit",
            "description": "Stage the given files and create a commit. Returns the hash.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message."},
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Paths to stage and commit.",
                    },
                },
                "required": ["message", "files"],
            },
        },
        handler=lambda inp, ws, **_: git.git_commit(
            inp["message"], inp["files"], ws
        ),
        subsets=("builder",),
    ),

    # Web
    ToolSpec(
        name="web_search",
        definition={
            "name": "web_search",
            "description": (
                "Search the web for information. (Not yet implemented — use "
                "run_command with curl as a workaround.)"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                },
                "required": ["query"],
            },
        },
        handler=lambda inp, ws, **_: web.web_search(inp["query"]),
        subsets=("researcher",),
    ),
    ToolSpec(
        name="web_fetch",
        definition={
            "name": "web_fetch",
            "description": (
                "Fetch a URL and return the content as text. Capped at 50 KB, "
                "30-second timeout."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch."},
                },
                "required": ["url"],
            },
        },
        handler=lambda inp, ws, **_: web.web_fetch(inp["url"]),
        subsets=("researcher",),
    ),

    # Telegram
    ToolSpec(
        name="send_telegram",
        definition={
            "name": "send_telegram",
            "description": (
                "Send a message to a configured Telegram group. Group names "
                "come from trinity.toml."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message text (Markdown supported).",
                    },
                    "group": {
                        "type": "string",
                        "description": "Logical group name (from trinity.toml).",
                    },
                },
                "required": ["message", "group"],
            },
        },
        handler=lambda inp, ws, **ctx: telegram_tools.send_telegram(
            inp["message"],
            inp["group"],
            ctx.get("bot_token", ""),
            ctx.get("groups", {}),
        ),
        subsets=("builder", "researcher"),
    ),

    # Memory
    ToolSpec(
        name="memory_store",
        definition=memory_tools.MEMORY_STORE_SCHEMA,
        handler=memory_tools.memory_store,
        subsets=("builder", "researcher", "memory"),
    ),
    ToolSpec(
        name="memory_search",
        definition=memory_tools.MEMORY_SEARCH_SCHEMA,
        handler=memory_tools.memory_search,
        subsets=("builder", "researcher", "memory"),
    ),
    ToolSpec(
        name="memory_forget",
        definition=memory_tools.MEMORY_FORGET_SCHEMA,
        handler=memory_tools.memory_forget,
        subsets=("memory",),
    ),
    ToolSpec(
        name="memory_recall",
        definition=memory_tools.MEMORY_RECALL_SCHEMA,
        handler=memory_tools.memory_recall,
        subsets=("memory",),
    ),
    ToolSpec(
        name="memory_update",
        definition=memory_tools.MEMORY_UPDATE_SCHEMA,
        handler=memory_tools.memory_update,
        subsets=("memory",),
    ),
    ToolSpec(
        name="memory_promote",
        definition=memory_tools.MEMORY_PROMOTE_SCHEMA,
        handler=memory_tools.memory_promote,
        subsets=("memory",),
    ),

    # Knowledge
    ToolSpec(
        name="log_issue",
        definition=knowledge_tools.LOG_ISSUE_SCHEMA,
        handler=knowledge_tools.log_issue,
        subsets=("builder",),
    ),
    ToolSpec(
        name="log_decision",
        definition=knowledge_tools.LOG_DECISION_SCHEMA,
        handler=knowledge_tools.log_decision,
        subsets=("builder",),
    ),
    ToolSpec(
        name="log_audit",
        definition=knowledge_tools.LOG_AUDIT_SCHEMA,
        handler=knowledge_tools.log_audit,
        subsets=("builder",),
    ),
    ToolSpec(
        name="log_lesson",
        definition=knowledge_tools.LOG_LESSON_SCHEMA,
        handler=knowledge_tools.log_lesson,
        subsets=("builder",),
    ),
]

for _spec in _BUILTIN_SPECS:
    TOOLS.register(_spec.name, _spec, source="builtin")

# Third-party tools register themselves via the entry-point group.
TOOLS.discover()


# ── Back-compat API ───────────────────────────────────────────────────

def build_tool_definitions() -> list[dict[str, Any]]:
    """Return the current list of Anthropic-format tool definitions."""
    return [TOOLS.get(name).definition for name in TOOLS.names()]


def _subset(tag: str) -> list[str]:
    return sorted(
        name for name in TOOLS.names()
        if tag in TOOLS.get(name).subsets
    )


# Computed once at import time — third parties that register after import
# should call build_tool_definitions() directly to see fresh state.
TOOL_DEFINITIONS: list[dict[str, Any]] = build_tool_definitions()
BUILDER_TOOLS: list[str] = _subset("builder")
RESEARCHER_TOOLS: list[str] = _subset("researcher")
MEMORY_TOOLS: list[str] = _subset("memory")


def get_tools(names: list[str] | None = None) -> list[dict[str, Any]]:
    """Return Anthropic-format tool definitions for the given names.

    If ``names`` is None, returns all registered definitions. Unknown names
    are silently skipped (back-compat contract).
    """
    if names is None:
        return build_tool_definitions()
    result = []
    for n in names:
        if n in TOOLS:
            result.append(TOOLS.get(n).definition)
    return result


def execute_tool(
    name: str,
    input: dict[str, Any],
    workspace_root: Path,
    **context: Any,
) -> str:
    """Execute a tool by name and return the string result.

    Raises KeyError if the tool is not registered.
    """
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: '{name}'")
    spec = TOOLS.get(name)
    try:
        return spec.handler(input, workspace_root, **context)
    except Exception as e:
        return f"Error in {name}: {type(e).__name__}: {e}"

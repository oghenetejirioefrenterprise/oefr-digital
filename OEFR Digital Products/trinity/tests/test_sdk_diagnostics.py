"""Regression coverage for actionable Claude SDK failure diagnostics.

The legacy Claude path remains a supported fallback even when Trinity's active
provider is Codex.  On 2026-07-12 the SDK reader discarded the CLI's useful
error result and emitted only "check stderr", forcing TJ to request a manual
diagnosis.  These tests protect both halves of the fix: capture at the message
stream and inclusion in the final exhausted-retry error.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


TRINITY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRINITY_DIR))

import agent  # noqa: E402


@pytest.mark.asyncio
async def test_sdk_query_collect_captures_error_result(monkeypatch):
    from claude_agent_sdk import ResultMessage
    import claude_agent_sdk

    error_text = "There's an issue with the selected model (bogus-model)."

    async def fake_query(*, prompt, options):
        del prompt, options
        yield ResultMessage(
            subtype="error_during_execution",
            duration_ms=1,
            duration_api_ms=1,
            is_error=True,
            num_turns=0,
            session_id="diagnostic-regression",
            result=error_text,
        )

    monkeypatch.setattr(claude_agent_sdk, "query", fake_query)
    sink: list[str] = []

    output, usage = await agent._sdk_query_collect(
        "diagnostic test", max_turns=1, stderr_sink=sink,
    )

    assert output == error_text
    assert usage is None
    assert sink == [f"CLI error result: {error_text}"]


def test_exhausted_retries_include_cli_diagnostic(monkeypatch):
    from claude_agent_sdk._errors import ProcessError

    diagnostic = "authentication failed: refresh the Claude CLI session"
    attempts = 0

    async def fail_with_diagnostic(prompt, max_turns, model=None, stderr_sink=None):
        nonlocal attempts
        del prompt, max_turns, model
        attempts += 1
        assert stderr_sink is not None
        stderr_sink.append(diagnostic)
        raise ProcessError("Command failed with exit code 1", exit_code=1)

    monkeypatch.setattr(agent, "_sdk_query_collect", fail_with_diagnostic)
    monkeypatch.setattr(agent.time, "sleep", lambda _seconds: None)

    sdk_runner = getattr(agent, "_run_agent_sdk_claude", agent.run_agent_sdk)
    result = sdk_runner(
        "diagnostic test", max_turns=1, print_output=False, lightweight=True,
    )

    assert attempts == 3
    assert "after 3 attempts" in result
    assert "CLI stderr tail:" in result
    assert diagnostic in result


@pytest.mark.skipif(
    not hasattr(agent, "_run_agent_codex"),
    reason="Codex provider path not present on this branch",
)
def test_active_codex_path_includes_cli_diagnostic(monkeypatch):
    diagnostic = "model access denied for this account"

    def fake_run(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(returncode=1, stdout="", stderr=diagnostic)

    monkeypatch.setattr(agent.subprocess, "run", fake_run)
    monkeypatch.setattr(agent, "_build_full_prompt", lambda *args, **kwargs: "prompt")

    result = agent._run_agent_codex(
        "diagnostic test", max_turns=1, print_output=False, lightweight=True,
    )

    assert "Error running Codex CLI (exit 1)" in result
    assert diagnostic in result

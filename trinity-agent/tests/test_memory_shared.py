"""Regression tests for cross-workspace memory sharing (Phase 4 sub-project 5)."""
from __future__ import annotations

from pathlib import Path

from trinity.memory.cleanup import run_cleanup  # ensure import works


def test_shared_memory_config_defaults():
    from trinity.config import SharedMemoryConfig

    cfg = SharedMemoryConfig()
    assert cfg.publish_categories == []
    assert cfg.subscribe_to_workspaces == []
    assert cfg.shared_storage_path == ""


def test_shared_memory_config_populated_from_toml(tmp_path):
    """If trinity.toml has [memory.shared], config.memory.shared should reflect it."""
    workspace = tmp_path / "fake_workspace"
    workspace.mkdir()
    (workspace / ".trinity").mkdir()
    (workspace / "trinity.toml").write_text(
        """
[company]
name = "test"
default_employee = "ceo"

[auth]
provider = "claude_sdk"

[memory.shared]
publish_categories = ["compliance_patterns", "buyer_segments"]
subscribe_to_workspaces = ["sister-lob"]
shared_storage_path = "~/.trinity/shared/"
"""
    )

    from trinity.config import load_config
    config = load_config(workspace)

    assert config.memory.shared.publish_categories == [
        "compliance_patterns",
        "buyer_segments",
    ]
    assert config.memory.shared.subscribe_to_workspaces == ["sister-lob"]
    assert config.memory.shared.shared_storage_path == "~/.trinity/shared/"


def test_shared_memory_config_absent_block_uses_defaults(tmp_path):
    """Loader must not crash when [memory.shared] is absent."""
    workspace = tmp_path / "fake_workspace"
    workspace.mkdir()
    (workspace / ".trinity").mkdir()
    (workspace / "trinity.toml").write_text(
        """
[company]
name = "test"
default_employee = "ceo"

[auth]
provider = "claude_sdk"
"""
    )

    from trinity.config import load_config
    config = load_config(workspace)

    assert config.memory.shared.publish_categories == []
    assert config.memory.shared.subscribe_to_workspaces == []
    assert config.memory.shared.shared_storage_path == ""


# Reference the cleanup import so static-analysis doesn't flag it as unused.
assert callable(run_cleanup)

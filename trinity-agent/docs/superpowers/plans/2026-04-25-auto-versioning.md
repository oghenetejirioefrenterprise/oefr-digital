# Auto-Versioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bump trinity-agent's minor version + create an annotated `vX.Y.Z` tag automatically on every commit that touches `trinity-agent/`. Manual `trinity dev bump-major` for major bumps.

**Architecture:** Two git hooks (`pre-commit`, `post-commit`) under `trinity-agent/scripts/git-hooks/`, activated via `core.hooksPath`. Both shell out to a single Python module `bump_version.py` for all version-string manipulation. A new `trinity dev` CLI subcommand group exposes `install-hooks` and `bump-major`. Annotated tags are the canonical changelog.

**Tech Stack:** Python 3.11+, bash, git, pytest. No new dependencies.

**Spec reference:** `trinity-agent/docs/superpowers/specs/2026-04-25-auto-versioning-design.md`

---

## File Structure

| Path | New / Modified | Purpose |
|---|---|---|
| `trinity-agent/scripts/bump_version.py` | NEW | Pure version-bumping logic + CLI (`show|minor|major`). Single source of truth. |
| `trinity-agent/scripts/git-hooks/pre-commit` | NEW | Bumps version + stages files when `trinity-agent/` is in the staged paths. |
| `trinity-agent/scripts/git-hooks/post-commit` | NEW | Creates annotated `vX.Y.Z` tag with commit message + diff stat. |
| `trinity-agent/src/trinity/cli_dev.py` | NEW | `install-hooks` and `bump-major` implementations. |
| `trinity-agent/src/trinity/cli.py` | MODIFIED | Register `dev` subparser + dispatch. |
| `trinity-agent/tests/test_bump_version.py` | NEW | Unit tests for `bump_version.py`. |
| `trinity-agent/tests/test_hooks.py` | NEW | Integration tests for both hooks (use a throwaway git repo). |
| `trinity-agent/tests/test_cli_dev.py` | NEW | Tests for the `trinity dev` CLI surface. |
| `trinity-agent/CLAUDE.md` | MODIFIED | Add a "Versioning" section. |

---

## Task 1: `bump_version.py` — pure parse/bump functions

**Files:**
- Create: `trinity-agent/scripts/bump_version.py`
- Test: `trinity-agent/tests/test_bump_version.py`

- [ ] **Step 1: Write the failing test**

Create `trinity-agent/tests/test_bump_version.py`:

```python
"""Tests for trinity-agent/scripts/bump_version.py — pure functions."""
from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import bump_version  # noqa: E402


def test_parse_valid():
    assert bump_version.parse("0.1.0") == (0, 1, 0)
    assert bump_version.parse("12.345.6789") == (12, 345, 6789)


def test_parse_rejects_invalid():
    import pytest
    with pytest.raises(ValueError):
        bump_version.parse("0.1")
    with pytest.raises(ValueError):
        bump_version.parse("v0.1.0")
    with pytest.raises(ValueError):
        bump_version.parse("0.1.0-rc1")


def test_format_roundtrip():
    assert bump_version.format_version((0, 1, 0)) == "0.1.0"
    assert bump_version.format_version((12, 345, 6789)) == "12.345.6789"


def test_bump_minor_increments_minor_zeroes_patch():
    assert bump_version.bump_minor("0.1.0") == "0.2.0"
    assert bump_version.bump_minor("1.5.3") == "1.6.0"
    assert bump_version.bump_minor("12.345.6789") == "12.346.0"


def test_bump_major_increments_major_zeroes_rest():
    assert bump_version.bump_major("0.1.0") == "1.0.0"
    assert bump_version.bump_major("1.5.3") == "2.0.0"
    assert bump_version.bump_major("12.345.6789") == "13.0.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_bump_version.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bump_version'`.

- [ ] **Step 3: Write minimal implementation**

Create `trinity-agent/scripts/bump_version.py`:

```python
"""Single source of truth for trinity-agent version bumping.

Usable as a library (import) and a CLI:

    python scripts/bump_version.py show
    python scripts/bump_version.py minor
    python scripts/bump_version.py major
"""
from __future__ import annotations

import re
from pathlib import Path

Version = tuple[int, int, int]

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse(version: str) -> Version:
    m = _SEMVER.match(version)
    if not m:
        raise ValueError(f"Not a strict X.Y.Z version: {version!r}")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def format_version(v: Version) -> str:
    return f"{v[0]}.{v[1]}.{v[2]}"


def bump_minor(version: str) -> str:
    major, minor, _ = parse(version)
    return format_version((major, minor + 1, 0))


def bump_major(version: str) -> str:
    major, _, _ = parse(version)
    return format_version((major + 1, 0, 0))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_bump_version.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git -C /home/oghenetejiri/apps add trinity-agent/scripts/bump_version.py trinity-agent/tests/test_bump_version.py
git -C /home/oghenetejiri/apps commit -m "feat(versioning): pure bump_version functions" -m "Pure parse/format/bump_minor/bump_major helpers, no I/O yet."
```

After this commit, expect the version to bump to `0.2.0` once the hooks are installed in Task 8. Until then, the version stays `0.1.0`.

---

## Task 2: `bump_version.py` — read/write version files

**Files:**
- Modify: `trinity-agent/scripts/bump_version.py` (add I/O functions)
- Test: `trinity-agent/tests/test_bump_version.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `trinity-agent/tests/test_bump_version.py`:

```python
def test_read_version_from_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "foo"\nversion = "0.7.3"\n'
        'description = "x"\n'
    )
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "0.7.3"\n')
    assert bump_version.read_version(pyproject) == "0.7.3"


def test_write_version_updates_both_files(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "foo"\nversion = "0.7.3"\n'
        'description = "x"\n'
    )
    init_file = tmp_path / "__init__.py"
    init_file.write_text(
        '"""Trinity Agent."""\n__version__ = "0.7.3"\n'
    )
    bump_version.write_version(pyproject, init_file, "0.8.0")
    assert 'version = "0.8.0"' in pyproject.read_text()
    assert '__version__ = "0.8.0"' in init_file.read_text()
    # Other content preserved.
    assert 'name = "foo"' in pyproject.read_text()
    assert '"""Trinity Agent."""' in init_file.read_text()


def test_write_version_refuses_non_strictly_greater(tmp_path):
    import pytest
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.7.3"\n')
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "0.7.3"\n')
    with pytest.raises(ValueError, match="strictly greater"):
        bump_version.write_version(pyproject, init_file, "0.7.3")
    with pytest.raises(ValueError, match="strictly greater"):
        bump_version.write_version(pyproject, init_file, "0.7.0")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_bump_version.py -v`
Expected: 3 new failures with `AttributeError: module 'bump_version' has no attribute 'read_version'`.

- [ ] **Step 3: Add I/O functions**

Append to `trinity-agent/scripts/bump_version.py`:

```python
_PYPROJECT_VERSION = re.compile(
    r'^(version\s*=\s*")([^"]+)(")', re.MULTILINE
)
_INIT_VERSION = re.compile(
    r'^(__version__\s*=\s*")([^"]+)(")', re.MULTILINE
)


def read_version(pyproject: Path) -> str:
    text = pyproject.read_text()
    m = _PYPROJECT_VERSION.search(text)
    if not m:
        raise ValueError(f"No version line found in {pyproject}")
    return m.group(2)


def write_version(pyproject: Path, init_file: Path, new_version: str) -> None:
    """Update version in both files. Refuses if not strictly greater than current."""
    parse(new_version)  # validate format
    current = read_version(pyproject)
    if parse(new_version) <= parse(current):
        raise ValueError(
            f"New version {new_version} must be strictly greater than current {current}"
        )
    py_text = pyproject.read_text()
    new_py = _PYPROJECT_VERSION.sub(rf'\g<1>{new_version}\g<3>', py_text, count=1)
    pyproject.write_text(new_py)

    init_text = init_file.read_text()
    if not _INIT_VERSION.search(init_text):
        raise ValueError(f"No __version__ line found in {init_file}")
    new_init = _INIT_VERSION.sub(rf'\g<1>{new_version}\g<3>', init_text, count=1)
    init_file.write_text(new_init)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_bump_version.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git -C /home/oghenetejiri/apps add trinity-agent/scripts/bump_version.py trinity-agent/tests/test_bump_version.py
git -C /home/oghenetejiri/apps commit -m "feat(versioning): read/write version in pyproject + __init__"
```

---

## Task 3: `bump_version.py` — CLI entry point

**Files:**
- Modify: `trinity-agent/scripts/bump_version.py` (add `__main__`)
- Test: `trinity-agent/tests/test_bump_version.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `trinity-agent/tests/test_bump_version.py`:

```python
def test_paths_resolves_relative_to_script(monkeypatch, tmp_path):
    """bump_version.default_paths() finds pyproject + __init__ relative to its own location."""
    # The real script lives at trinity-agent/scripts/bump_version.py
    # so default paths resolve to trinity-agent/pyproject.toml and
    # trinity-agent/src/trinity/__init__.py
    py, init = bump_version.default_paths()
    assert py.name == "pyproject.toml"
    assert py.parent.name == "trinity-agent"
    assert init.name == "__init__.py"
    assert init.parent.name == "trinity"


def test_cli_show(capsys, tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.7.3"\n')
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "0.7.3"\n')

    rc = bump_version.main(["show"], paths=(pyproject, init_file))
    assert rc == 0
    assert capsys.readouterr().out.strip() == "0.7.3"


def test_cli_minor(capsys, tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.7.3"\n')
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "0.7.3"\n')

    rc = bump_version.main(["minor"], paths=(pyproject, init_file))
    assert rc == 0
    assert capsys.readouterr().out.strip() == "0.8.0"
    assert 'version = "0.8.0"' in pyproject.read_text()
    assert '__version__ = "0.8.0"' in init_file.read_text()


def test_cli_major(capsys, tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.7.3"\n')
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "0.7.3"\n')

    rc = bump_version.main(["major"], paths=(pyproject, init_file))
    assert rc == 0
    assert capsys.readouterr().out.strip() == "1.0.0"


def test_cli_unknown_command(capsys, tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.7.3"\n')
    init_file = tmp_path / "__init__.py"
    init_file.write_text('__version__ = "0.7.3"\n')

    rc = bump_version.main(["bogus"], paths=(pyproject, init_file))
    assert rc != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_bump_version.py -v`
Expected: 5 new failures (`default_paths`, `main` not defined).

- [ ] **Step 3: Add CLI entry point**

Append to `trinity-agent/scripts/bump_version.py`:

```python
import sys


def default_paths() -> tuple[Path, Path]:
    """Resolve pyproject.toml and __init__.py paths relative to this script.

    Layout expected:
        trinity-agent/
            pyproject.toml
            scripts/bump_version.py   <- this file
            src/trinity/__init__.py
    """
    repo_root = Path(__file__).resolve().parent.parent
    return (
        repo_root / "pyproject.toml",
        repo_root / "src" / "trinity" / "__init__.py",
    )


def main(argv: list[str] | None = None, paths: tuple[Path, Path] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    pyproject, init_file = paths if paths else default_paths()

    if not argv:
        print("Usage: bump_version.py {show|minor|major}", file=sys.stderr)
        return 2

    cmd = argv[0]
    if cmd == "show":
        print(read_version(pyproject))
        return 0
    if cmd == "minor":
        new = bump_minor(read_version(pyproject))
        write_version(pyproject, init_file, new)
        print(new)
        return 0
    if cmd == "major":
        new = bump_major(read_version(pyproject))
        write_version(pyproject, init_file, new)
        print(new)
        return 0

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_bump_version.py -v`
Expected: 13 passed.

Also smoke-test the CLI directly:
```bash
python /home/oghenetejiri/apps/trinity-agent/scripts/bump_version.py show
```
Expected: prints `0.1.0` (the current version).

- [ ] **Step 5: Commit**

```bash
git -C /home/oghenetejiri/apps add trinity-agent/scripts/bump_version.py trinity-agent/tests/test_bump_version.py
git -C /home/oghenetejiri/apps commit -m "feat(versioning): bump_version.py CLI (show|minor|major)"
```

---

## Task 4: `pre-commit` hook + integration test

**Files:**
- Create: `trinity-agent/scripts/git-hooks/pre-commit`
- Test: `trinity-agent/tests/test_hooks.py`

- [ ] **Step 1: Write the failing tests**

Create `trinity-agent/tests/test_hooks.py`:

```python
"""Integration tests for git-hook driven versioning.

Each test creates a throwaway git repo, copies the trinity-agent layout
into it (just the pieces needed: pyproject.toml, __init__.py, hooks,
bump_version.py), sets core.hooksPath, and exercises real git commits.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REAL_REPO = Path(__file__).resolve().parents[1]
HOOKS_SRC = REAL_REPO / "scripts" / "git-hooks"
BUMP_SCRIPT_SRC = REAL_REPO / "scripts" / "bump_version.py"


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(cmd, cwd=cwd, env=full_env, check=True,
                          capture_output=True, text=True)


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Create a throwaway git repo mirroring the trinity-agent layout.

    Layout:
        <tmp>/
            .git/
            trinity-agent/
                pyproject.toml
                scripts/bump_version.py        (copied from real repo)
                scripts/git-hooks/             (copied from real repo)
                src/trinity/__init__.py
            sibling-app/
                foo.txt
    """
    # Init a fresh repo at tmp_path.
    _run(["git", "init", "-q", "-b", "main"], cwd=tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path)
    _run(["git", "config", "user.name", "Test"], cwd=tmp_path)

    # Build trinity-agent layout.
    ta = tmp_path / "trinity-agent"
    (ta / "src" / "trinity").mkdir(parents=True)
    (ta / "scripts").mkdir(parents=True)
    (ta / "pyproject.toml").write_text(
        '[project]\nname = "trinity-agent"\nversion = "0.1.0"\n'
    )
    (ta / "src" / "trinity" / "__init__.py").write_text(
        '"""Trinity Agent."""\n__version__ = "0.1.0"\n'
    )

    # Copy the real bump_version.py and hooks.
    shutil.copy(BUMP_SCRIPT_SRC, ta / "scripts" / "bump_version.py")
    shutil.copytree(HOOKS_SRC, ta / "scripts" / "git-hooks")
    for hook in (ta / "scripts" / "git-hooks").iterdir():
        hook.chmod(0o755)

    # Sibling app.
    (tmp_path / "sibling-app").mkdir()
    (tmp_path / "sibling-app" / "foo.txt").write_text("hello\n")

    # Activate hooks.
    _run(["git", "config", "core.hooksPath", "trinity-agent/scripts/git-hooks"],
         cwd=tmp_path)

    # Initial commit (no hooks yet for trinity-agent files; we'll commit and
    # let the hook fire — that's what we're testing).
    _run(["git", "add", "."], cwd=tmp_path)
    return tmp_path


def _read_version(repo: Path) -> str:
    text = (repo / "trinity-agent" / "pyproject.toml").read_text()
    for line in text.splitlines():
        if line.startswith("version"):
            return line.split('"')[1]
    raise AssertionError("no version line")


def test_commit_touching_trinity_agent_bumps_minor(fake_repo: Path):
    _run(["git", "commit", "-q", "-m", "feat: initial"], cwd=fake_repo)
    assert _read_version(fake_repo) == "0.2.0"


def test_commit_touching_only_sibling_does_not_bump(fake_repo: Path):
    # Stage only the sibling file (already staged from fixture, but make a fresh change).
    _run(["git", "commit", "-q", "-m", "chore: initial bundle"], cwd=fake_repo)
    # First commit bumped because trinity-agent files were also staged.
    # Reset and isolate.
    initial = _read_version(fake_repo)

    (fake_repo / "sibling-app" / "foo.txt").write_text("changed\n")
    _run(["git", "add", "sibling-app/foo.txt"], cwd=fake_repo)
    _run(["git", "commit", "-q", "-m", "fix(sibling): tweak"], cwd=fake_repo)
    assert _read_version(fake_repo) == initial
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_hooks.py -v`
Expected: FAIL — `HOOKS_SRC` does not exist (`FileNotFoundError` during fixture).

- [ ] **Step 3: Write the pre-commit hook**

Create `trinity-agent/scripts/git-hooks/pre-commit`:

```bash
#!/usr/bin/env bash
# pre-commit: bump trinity-agent's minor version when staged files touch
# trinity-agent/. Skips during rebase, amend, and chore(release): commits.
set -euo pipefail

# Skip during rebase.
git_dir=$(git rev-parse --git-dir)
if [[ -d "$git_dir/rebase-merge" || -d "$git_dir/rebase-apply" ]]; then
    exit 0
fi

# Skip during amend (best-effort detection via reflog action).
if [[ "${GIT_REFLOG_ACTION:-}" == *"amend"* ]]; then
    exit 0
fi

# Find the trinity-agent dir (this hook lives in trinity-agent/scripts/git-hooks/).
hook_dir=$(cd "$(dirname "$0")" && pwd)
ta_dir=$(cd "$hook_dir/../.." && pwd)
ta_rel=$(git -C "$(git rev-parse --show-toplevel)" \
    rev-parse --show-prefix < /dev/null && cd "$ta_dir" && \
    git rev-parse --show-prefix 2>/dev/null || true)
# Simpler: relative path from repo root to trinity-agent.
repo_root=$(git rev-parse --show-toplevel)
ta_rel=${ta_dir#"$repo_root/"}

# Inspect staged files; bail if none under trinity-agent/.
staged=$(git diff --cached --name-only --diff-filter=ACMRTUXB || true)
if ! grep -q "^${ta_rel}/" <<< "$staged"; then
    exit 0
fi

# Skip release commits — bump-major handles them itself.
# (Best-effort: read the prepared commit message file when available.)
if [[ -n "${GIT_AUTHOR_DATE:-}" && -f "$git_dir/COMMIT_EDITMSG" ]]; then
    first_line=$(head -n1 "$git_dir/COMMIT_EDITMSG" 2>/dev/null || true)
    if [[ "$first_line" == chore\(release\):* ]]; then
        exit 0
    fi
fi

# Bump.
new_version=$(python "$ta_dir/scripts/bump_version.py" minor)
echo "trinity-agent: bumped to v$new_version"

# Stage the version files.
git add "$ta_dir/pyproject.toml" "$ta_dir/src/trinity/__init__.py"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_hooks.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git -C /home/oghenetejiri/apps add trinity-agent/scripts/git-hooks/pre-commit trinity-agent/tests/test_hooks.py
git -C /home/oghenetejiri/apps commit -m "feat(versioning): pre-commit hook bumps minor on trinity-agent commits"
```

---

## Task 5: `post-commit` hook + integration test

**Files:**
- Create: `trinity-agent/scripts/git-hooks/post-commit`
- Test: `trinity-agent/tests/test_hooks.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `trinity-agent/tests/test_hooks.py`:

```python
def _tags(repo: Path) -> list[str]:
    out = _run(["git", "tag", "--list"], cwd=repo).stdout.strip()
    return out.splitlines() if out else []


def _tag_message(repo: Path, tag: str) -> str:
    return _run(
        ["git", "for-each-ref", f"refs/tags/{tag}",
         "--format=%(contents)"],
        cwd=repo,
    ).stdout


def test_commit_touching_trinity_agent_creates_annotated_tag(fake_repo: Path):
    _run(["git", "commit", "-q", "-m", "feat: initial bundle\n\nbody line"],
         cwd=fake_repo)
    tags = _tags(fake_repo)
    assert "v0.2.0" in tags
    msg = _tag_message(fake_repo, "v0.2.0")
    assert "trinity-agent v0.2.0" in msg
    assert "feat: initial bundle" in msg
    assert "body line" in msg
    assert "Files changed:" in msg


def test_commit_touching_only_sibling_creates_no_tag(fake_repo: Path):
    _run(["git", "commit", "-q", "-m", "feat: initial"], cwd=fake_repo)
    initial_tags = set(_tags(fake_repo))

    (fake_repo / "sibling-app" / "foo.txt").write_text("changed\n")
    _run(["git", "add", "sibling-app/foo.txt"], cwd=fake_repo)
    _run(["git", "commit", "-q", "-m", "fix(sibling): tweak"], cwd=fake_repo)

    assert set(_tags(fake_repo)) == initial_tags


def test_post_commit_is_idempotent_when_tag_exists(fake_repo: Path):
    _run(["git", "commit", "-q", "-m", "feat: initial"], cwd=fake_repo)
    # Manually re-trigger post-commit; should not crash even though tag exists.
    hook = fake_repo / "trinity-agent" / "scripts" / "git-hooks" / "post-commit"
    _run([str(hook)], cwd=fake_repo)  # Should warn and exit 0.
    # Still only one tag for that version.
    assert _tags(fake_repo).count("v0.2.0") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_hooks.py -v`
Expected: 3 new failures (`v0.2.0` tag missing).

- [ ] **Step 3: Write the post-commit hook**

Create `trinity-agent/scripts/git-hooks/post-commit`:

```bash
#!/usr/bin/env bash
# post-commit: tag trinity-agent commits with vX.Y.Z and annotate with the
# commit subject + body + diff stat. Never blocks; logs warnings and exits 0
# on failure.
set -uo pipefail

# Skip during rebase.
git_dir=$(git rev-parse --git-dir)
if [[ -d "$git_dir/rebase-merge" || -d "$git_dir/rebase-apply" ]]; then
    exit 0
fi

hook_dir=$(cd "$(dirname "$0")" && pwd)
ta_dir=$(cd "$hook_dir/../.." && pwd)
repo_root=$(git rev-parse --show-toplevel)
ta_rel=${ta_dir#"$repo_root/"}

# Did this commit touch trinity-agent?
changed=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null || true)
if ! grep -q "^${ta_rel}/" <<< "$changed"; then
    exit 0
fi

# Skip release commits — bump-major creates its own tag.
subject=$(git log -1 --pretty=%s HEAD)
if [[ "$subject" == chore\(release\):* ]]; then
    exit 0
fi

# Read new version.
version=$(python "$ta_dir/scripts/bump_version.py" show)
tag="v$version"

# Idempotency: skip if tag already exists.
if git rev-parse -q --verify "refs/tags/$tag" > /dev/null; then
    echo "trinity-agent: tag $tag already exists — skipping" >&2
    exit 0
fi

# Build tag message.
body=$(git log -1 --pretty=%b HEAD)
diff_stat=$(git diff --stat "HEAD~1" HEAD -- "$ta_dir/" 2>/dev/null || true)

msg="trinity-agent $tag

$subject"
if [[ -n "$body" ]]; then
    msg="$msg

$body"
fi
if [[ -n "$diff_stat" ]]; then
    msg="$msg

Files changed:
$diff_stat"
fi

if ! git tag -a "$tag" -m "$msg"; then
    echo "trinity-agent: failed to create tag $tag" >&2
    exit 0
fi
echo "trinity-agent: tagged $tag"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_hooks.py -v`
Expected: 5 passed (2 from Task 4 + 3 new).

- [ ] **Step 5: Commit**

```bash
git -C /home/oghenetejiri/apps add trinity-agent/scripts/git-hooks/post-commit trinity-agent/tests/test_hooks.py
git -C /home/oghenetejiri/apps commit -m "feat(versioning): post-commit hook tags release with diff stat"
```

---

## Task 6: `trinity dev install-hooks` CLI command

**Files:**
- Create: `trinity-agent/src/trinity/cli_dev.py`
- Modify: `trinity-agent/src/trinity/cli.py`
- Test: `trinity-agent/tests/test_cli_dev.py`

- [ ] **Step 1: Write the failing test**

Create `trinity-agent/tests/test_cli_dev.py`:

```python
"""Tests for trinity.cli_dev — install-hooks and bump-major."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from trinity import cli_dev


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def fake_clone(tmp_path: Path) -> Path:
    """Initialize a git repo at tmp_path and create scripts/git-hooks/."""
    _run(["git", "init", "-q", "-b", "main"], cwd=tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path)
    _run(["git", "config", "user.name", "Test"], cwd=tmp_path)
    hooks = tmp_path / "trinity-agent" / "scripts" / "git-hooks"
    hooks.mkdir(parents=True)
    (hooks / "pre-commit").write_text("#!/usr/bin/env bash\nexit 0\n")
    (hooks / "post-commit").write_text("#!/usr/bin/env bash\nexit 0\n")
    return tmp_path


def test_install_hooks_sets_core_hooks_path(fake_clone: Path):
    rc = cli_dev.install_hooks(repo_root=fake_clone)
    assert rc == 0
    out = _run(["git", "config", "--get", "core.hooksPath"], cwd=fake_clone).stdout.strip()
    assert out == "trinity-agent/scripts/git-hooks"


def test_install_hooks_makes_hooks_executable(fake_clone: Path):
    cli_dev.install_hooks(repo_root=fake_clone)
    pre = fake_clone / "trinity-agent" / "scripts" / "git-hooks" / "pre-commit"
    post = fake_clone / "trinity-agent" / "scripts" / "git-hooks" / "post-commit"
    assert pre.stat().st_mode & 0o111
    assert post.stat().st_mode & 0o111


def test_install_hooks_fails_outside_git_repo(tmp_path: Path):
    rc = cli_dev.install_hooks(repo_root=tmp_path)
    assert rc != 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_cli_dev.py -v`
Expected: FAIL — `ImportError: cannot import name 'cli_dev' from 'trinity'`.

- [ ] **Step 3: Implement `cli_dev.install_hooks`**

Create `trinity-agent/src/trinity/cli_dev.py`:

```python
"""Trinity development utilities — version + hook management."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

HOOKS_REL = "trinity-agent/scripts/git-hooks"


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists() or (path / ".git").is_file()


def install_hooks(repo_root: Path | None = None) -> int:
    """Activate the trinity-agent git hooks for the local clone."""
    repo = repo_root or Path.cwd()
    if not _is_git_repo(repo):
        print(f"Not a git repository: {repo}", flush=True)
        return 1

    hooks_dir = repo / HOOKS_REL
    if not hooks_dir.is_dir():
        print(f"Hooks directory missing: {hooks_dir}", flush=True)
        return 1

    # Make hooks executable.
    for hook in hooks_dir.iterdir():
        if hook.is_file():
            mode = hook.stat().st_mode
            hook.chmod(mode | 0o111)

    # Set core.hooksPath.
    subprocess.run(
        ["git", "config", "core.hooksPath", HOOKS_REL],
        cwd=repo,
        check=True,
    )
    print(f"Installed trinity-agent hooks: core.hooksPath = {HOOKS_REL}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_cli_dev.py -v`
Expected: 3 passed.

- [ ] **Step 5: Wire into `cli.py`**

Read `trinity-agent/src/trinity/cli.py` to find the existing subparser block ending with `# ── workspaces` (around line 130). Add a new `dev` subparser block immediately after it:

```python
    # ── dev ───────────────────────────────────────────────
    p_dev = sub.add_parser("dev", help="Trinity-agent development utilities")
    dev_sub = p_dev.add_subparsers(dest="dev_cmd")
    dev_sub.add_parser("install-hooks", help="Activate trinity-agent git hooks for this clone")
    p_bump_major = dev_sub.add_parser("bump-major", help="Cut a major release")
    p_bump_major.add_argument("--reason", required=True,
                              help="Why the major bump (recorded in tag and commit body)")
```

And in the dispatcher (around line 165 where `if args.command == "init":` etc.), add:

```python
    elif args.command == "dev":
        from trinity import cli_dev
        if args.dev_cmd == "install-hooks":
            return cli_dev.install_hooks()
        elif args.dev_cmd == "bump-major":
            return cli_dev.bump_major(reason=args.reason)
        else:
            p_dev.print_help()
            return 1
```

(Note: `cli_dev.bump_major` doesn't exist yet — Task 7. Importing it lazily means this code only fails when the user runs `trinity dev bump-major` before Task 7 lands. The dispatcher returns its rc; existing dispatch lines that return None should be wrapped if needed — keep current behavior for unrelated commands.)

- [ ] **Step 6: Smoke-test the CLI registration**

Run: `cd /home/oghenetejiri/apps/trinity-agent && python -m trinity dev --help`
Expected: shows `install-hooks` and `bump-major` subcommands.

- [ ] **Step 7: Commit**

```bash
git -C /home/oghenetejiri/apps add trinity-agent/src/trinity/cli_dev.py trinity-agent/src/trinity/cli.py trinity-agent/tests/test_cli_dev.py
git -C /home/oghenetejiri/apps commit -m "feat(cli): trinity dev install-hooks command"
```

---

## Task 7: `trinity dev bump-major` CLI command

**Files:**
- Modify: `trinity-agent/src/trinity/cli_dev.py`
- Test: `trinity-agent/tests/test_cli_dev.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `trinity-agent/tests/test_cli_dev.py`:

```python
import shutil
import sys

REAL_REPO = Path(__file__).resolve().parents[1]


def _build_full_clone(tmp_path: Path) -> Path:
    """Like fake_clone but with the real bump_version.py and hooks copied in."""
    _run(["git", "init", "-q", "-b", "main"], cwd=tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path)
    _run(["git", "config", "user.name", "Test"], cwd=tmp_path)

    ta = tmp_path / "trinity-agent"
    (ta / "src" / "trinity").mkdir(parents=True)
    (ta / "scripts").mkdir(parents=True)
    (ta / "pyproject.toml").write_text(
        '[project]\nname = "trinity-agent"\nversion = "0.5.0"\n'
    )
    (ta / "src" / "trinity" / "__init__.py").write_text(
        '"""Trinity Agent."""\n__version__ = "0.5.0"\n'
    )
    shutil.copy(REAL_REPO / "scripts" / "bump_version.py",
                ta / "scripts" / "bump_version.py")
    shutil.copytree(REAL_REPO / "scripts" / "git-hooks",
                    ta / "scripts" / "git-hooks")
    for hook in (ta / "scripts" / "git-hooks").iterdir():
        hook.chmod(0o755)

    _run(["git", "add", "."], cwd=tmp_path)
    _run(["git", "commit", "-q", "-m", "initial"], cwd=tmp_path)
    _run(["git", "config", "core.hooksPath", "trinity-agent/scripts/git-hooks"],
         cwd=tmp_path)
    return tmp_path


def test_bump_major_creates_commit_and_tag(tmp_path: Path):
    repo = _build_full_clone(tmp_path)
    rc = cli_dev.bump_major(reason="legacy provider removed", repo_root=repo)
    assert rc == 0

    # Version files updated.
    py_text = (repo / "trinity-agent" / "pyproject.toml").read_text()
    assert 'version = "1.0.0"' in py_text

    # Commit subject is chore(release).
    subject = _run(["git", "log", "-1", "--pretty=%s"], cwd=repo).stdout.strip()
    assert subject == "chore(release): bump to v1.0.0"

    # Body contains the reason.
    body = _run(["git", "log", "-1", "--pretty=%b"], cwd=repo).stdout
    assert "legacy provider removed" in body

    # Tag exists.
    tags = _run(["git", "tag", "--list"], cwd=repo).stdout.strip().splitlines()
    assert "v1.0.0" in tags

    # Tag message contains reason.
    tag_msg = _run(
        ["git", "for-each-ref", "refs/tags/v1.0.0", "--format=%(contents)"],
        cwd=repo,
    ).stdout
    assert "legacy provider removed" in tag_msg


def test_bump_major_refuses_dirty_tree(tmp_path: Path):
    repo = _build_full_clone(tmp_path)
    (repo / "trinity-agent" / "dirty.txt").write_text("uncommitted\n")
    _run(["git", "add", "trinity-agent/dirty.txt"], cwd=repo)

    rc = cli_dev.bump_major(reason="x", repo_root=repo)
    assert rc != 0


def test_bump_major_does_not_double_bump_via_hook(tmp_path: Path):
    """The chore(release): commit must not trigger pre-commit's own bump."""
    repo = _build_full_clone(tmp_path)
    cli_dev.bump_major(reason="x", repo_root=repo)
    # Version is exactly 1.0.0, not 1.1.0.
    py_text = (repo / "trinity-agent" / "pyproject.toml").read_text()
    assert 'version = "1.0.0"' in py_text
    # Only one v1.0.0 tag (post-commit didn't add a duplicate).
    tags = _run(["git", "tag", "--list"], cwd=repo).stdout.strip().splitlines()
    assert tags.count("v1.0.0") == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_cli_dev.py -v`
Expected: 3 new failures (`AttributeError: module 'trinity.cli_dev' has no attribute 'bump_major'`).

- [ ] **Step 3: Implement `bump_major`**

Append to `trinity-agent/src/trinity/cli_dev.py`:

```python
def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True)


def bump_major(reason: str, repo_root: Path | None = None) -> int:
    """Cut a major release: bump, commit, tag — all in one step."""
    repo = repo_root or Path.cwd()
    if not _is_git_repo(repo):
        print(f"Not a git repository: {repo}", flush=True)
        return 1

    # Refuse dirty tree.
    status = _git(["status", "--porcelain"], cwd=repo).stdout.strip()
    if status:
        print("Working tree must be clean before bump-major.", flush=True)
        print(status, flush=True)
        return 1

    # Bump.
    bump_script = repo / "trinity-agent" / "scripts" / "bump_version.py"
    if not bump_script.exists():
        print(f"bump_version.py missing: {bump_script}", flush=True)
        return 1
    new_version = subprocess.run(
        ["python", str(bump_script), "major"],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()

    # Stage version files.
    _git(["add",
          "trinity-agent/pyproject.toml",
          "trinity-agent/src/trinity/__init__.py"],
         cwd=repo)

    # Commit. Hooks must skip this — they detect the chore(release): prefix.
    subject = f"chore(release): bump to v{new_version}"
    body = f"Major release.\n\nReason: {reason}"
    _git(["commit", "-m", subject, "-m", body], cwd=repo)

    # Tag.
    tag_msg = f"trinity-agent v{new_version}\n\n{subject}\n\n{body}"
    _git(["tag", "-a", f"v{new_version}", "-m", tag_msg], cwd=repo)

    print(f"trinity-agent: bumped to v{new_version} (major)")
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_cli_dev.py tests/test_hooks.py tests/test_bump_version.py -v`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git -C /home/oghenetejiri/apps add trinity-agent/src/trinity/cli_dev.py trinity-agent/tests/test_cli_dev.py
git -C /home/oghenetejiri/apps commit -m "feat(cli): trinity dev bump-major command"
```

---

## Task 8: Document + activate hooks in the live repo

**Files:**
- Modify: `trinity-agent/CLAUDE.md`

- [ ] **Step 1: Run the full test suite**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest -v`
Expected: all green. Confirms nothing regressed.

- [ ] **Step 2: Add a "Versioning" section to `CLAUDE.md`**

Read `trinity-agent/CLAUDE.md` and append (or insert after the "Configuration" section):

```markdown
## Versioning

Versions auto-bump on every commit that touches `trinity-agent/` files. The
mechanism is two git hooks installed via `core.hooksPath`:

- `pre-commit`: bumps `MINOR` in `pyproject.toml` + `__init__.py` and stages them.
- `post-commit`: creates an annotated tag `vX.Y.Z` whose body is the commit
  subject + body + `git diff --stat`.

Sibling-app commits (e.g., `oefr-website/`) are ignored. Rebases and amends
are skipped to avoid burning versions on history rewrites.

### Activate the hooks (one-time per clone)

```bash
trinity dev install-hooks
```

This sets `git config core.hooksPath trinity-agent/scripts/git-hooks` and
makes the hook scripts executable.

### Cut a major release

```bash
trinity dev bump-major --reason "removed legacy X provider"
```

This makes a single `chore(release): bump to vN.0.0` commit and tags it.
The hooks detect the prefix and skip their own bump/tag, so no double-bump.

### Inspect releases

```bash
git tag --list "v*"            # all versions
git tag -l -n20 v0.42.0        # release notes for one tag
git show v0.42.0               # full commit + diff
```
```

- [ ] **Step 3: Activate the hooks in the live `~/apps` clone**

```bash
cd /home/oghenetejiri/apps && python -m trinity dev install-hooks
```

Expected output: `Installed trinity-agent hooks: core.hooksPath = trinity-agent/scripts/git-hooks`

Verify: `git -C /home/oghenetejiri/apps config --get core.hooksPath`
Expected: `trinity-agent/scripts/git-hooks`

- [ ] **Step 4: Commit the docs change**

This commit is the first one made *with the live hooks active*. Verify the bump fires.

```bash
git -C /home/oghenetejiri/apps add trinity-agent/CLAUDE.md
git -C /home/oghenetejiri/apps commit -m "docs(versioning): explain auto-versioning hooks"
```

Expected behavior:
- `pre-commit` fires, sees `trinity-agent/CLAUDE.md` staged, bumps `0.1.0 → 0.2.0`, stages `pyproject.toml` + `__init__.py`.
- Commit lands with all three files in it.
- `post-commit` fires, creates tag `v0.2.0`.

Verify:
```bash
git -C /home/oghenetejiri/apps tag --list | grep ^v
# Expected: v0.2.0

cat /home/oghenetejiri/apps/trinity-agent/pyproject.toml | grep version
# Expected: version = "0.2.0"

git -C /home/oghenetejiri/apps log -1 --stat
# Expected: 3 files in the commit (CLAUDE.md, pyproject.toml, __init__.py)
```

If anything is off, investigate before proceeding. Manual recovery: `git tag -d v0.2.0` and re-run the commit.

---

## Self-Review

**Spec coverage:**
- ✅ Two-hook mechanism with `core.hooksPath` (Tasks 4-6)
- ✅ Pre-commit bump on `trinity-agent/` changes only (Task 4)
- ✅ Skip rebase/amend (Task 4 hook code)
- ✅ Skip `chore(release):` (Tasks 4 hook code, Task 5 hook code)
- ✅ Annotated tag with subject + body + diff stat (Task 5)
- ✅ Idempotent post-commit (Task 5 test + hook)
- ✅ Single source `bump_version.py` (Tasks 1-3)
- ✅ `default_paths` resolves relative to `__file__` (Task 3 test)
- ✅ `trinity dev install-hooks` (Task 6)
- ✅ `trinity dev bump-major --reason` (Task 7)
- ✅ Major-bump skip coordination via subject prefix (Task 7 test)
- ✅ Refuse dirty tree before major bump (Task 7 test)
- ✅ Docs update (Task 8)
- ✅ Hook activation in live repo (Task 8)

**Placeholder scan:** none.

**Type / signature consistency:**
- `bump_version.read_version(pyproject)` — Task 2, used in Task 3. ✅
- `bump_version.write_version(pyproject, init_file, new)` — Task 2, used in Task 3. ✅
- `bump_version.main(argv, paths=...)` — Task 3 signature matches Task 3 tests. ✅
- `cli_dev.install_hooks(repo_root=None)` — Task 6, matches tests. ✅
- `cli_dev.bump_major(reason, repo_root=None)` — Task 7, matches dispatcher in Task 6 (`reason=args.reason`). ✅
- Hooks use `python "$ta_dir/scripts/bump_version.py"` consistently. ✅

No issues found.

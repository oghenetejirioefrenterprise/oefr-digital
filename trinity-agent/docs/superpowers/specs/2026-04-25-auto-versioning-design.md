# Auto-Versioning for Trinity Agent

**Status:** Approved (brainstorming) — pending implementation plan
**Date:** 2026-04-25
**Owner:** Trinity

## Goal

Automate version bumping for the `trinity-agent` package. Every commit that touches `trinity-agent/` files bumps the minor version, creates an annotated git tag, and records release notes in the tag body. Major bumps are explicit, triggered by a CLI command.

## Non-goals

- Versioning sibling projects in the `~/apps` monorepo (each can adopt the same pattern later if desired).
- Patch-level versioning (per spec: every commit is a minor bump; patch stays at 0).
- A `CHANGELOG.md` file (annotated tags are the canonical changelog; deferred until a real need).
- GitHub Releases / `gh release create` (deferred until the repo is regularly pushed).
- CI-driven releases (local hooks are the single source of truth).

## Scope

The repo at `~/apps` is a monorepo containing many independent projects. This design only versions `trinity-agent/`. Hooks fire on every commit but exit early when no `trinity-agent/` files are staged.

## Mechanism

### Two git hooks, installed via `core.hooksPath`

Hooks live at `trinity-agent/scripts/git-hooks/` and are tracked in git so they version with the code. A new CLI command activates them in the local clone:

```
trinity dev install-hooks
# runs: git config core.hooksPath trinity-agent/scripts/git-hooks
```

This is per-clone (git config is local) — collaborators run it once after cloning.

### `pre-commit` hook

Fires before every commit in the `~/apps` repo.

1. Detect whether to skip:
   - During `git rebase` (any of `.git/rebase-merge/`, `.git/rebase-apply/` exist) → skip.
   - During `git commit --amend` (detected via `GIT_REFLOG_ACTION` containing `amend`, with a fallback to checking if `HEAD` matches the parent of staged changes) → skip.
   - Commit subject begins with `chore(release):` (the major-bump path handles its own version) → skip.
2. Inspect `git diff --cached --name-only`. If no path starts with `trinity-agent/` → exit 0 silently.
3. Otherwise call `python trinity-agent/scripts/bump_version.py minor`, which:
   - Reads current version from `trinity-agent/pyproject.toml`.
   - Computes new version (`MAJOR.(MINOR+1).0`).
   - Writes new version to `trinity-agent/pyproject.toml` and `trinity-agent/src/trinity/__init__.py`.
   - Prints the new version to stdout.
4. `git add` the two modified files so they land in the in-progress commit.

Failure mode: if any step errors, `set -e` aborts the commit. The user sees the error and can either fix it or bypass with `git commit --no-verify`.

### `post-commit` hook

Fires after every commit succeeds.

1. Detect whether to skip:
   - During rebase (same checks as pre-commit) → skip.
   - The just-made commit didn't touch `trinity-agent/` (`git diff-tree --no-commit-id --name-only -r HEAD`) → skip.
   - Commit subject begins with `chore(release):` → skip (the `bump-major` command tags this commit itself).
2. Read the new version from `trinity-agent/pyproject.toml`.
3. If `git tag -l "v$VERSION"` already exists → log a warning, skip tagging (idempotent for partial-failure recovery).
4. Build the tag message:

   ```
   trinity-agent v<version>

   <commit subject from `git log -1 --pretty=%s HEAD`>

   <commit body from `git log -1 --pretty=%b HEAD`, if non-empty>

   Files changed:
   <output of `git diff --stat HEAD~1 HEAD -- trinity-agent/`>
   ```

5. Create annotated tag: `git tag -a "v$VERSION" -m "<message>"`.

Failure mode: post-commit never blocks (the commit already succeeded). Errors print to stderr; tag can be created manually if needed.

## Major bumps

Triggered explicitly by a new CLI command:

```
trinity dev bump-major --reason "removed legacy provider; new agent registry contract"
```

Behavior:

1. Verifies working tree is clean (no staged or unstaged changes).
2. Calls `bump_version.py major`, which sets `MAJOR=(MAJOR+1)`, `MINOR=0`, `PATCH=0`.
3. Stages the version files.
4. Creates a commit with subject `chore(release): bump to v<new-version>` and the `--reason` text in the body. (This commit triggers the hooks, but both detect the `chore(release):` prefix and skip — see hook skip rules above.)
5. Creates annotated tag `v<new-version>` with the same message body.

The `chore(release):` subject prefix is the single coordination signal: `pre-commit` skips its bump and `post-commit` skips its tagging when the commit was made by `bump-major`.

## Files

### New

- `trinity-agent/scripts/git-hooks/pre-commit` — bash, ~40 lines.
- `trinity-agent/scripts/git-hooks/post-commit` — bash, ~25 lines.
- `trinity-agent/scripts/bump_version.py` — python, ~60 lines. Single source of bump logic; usable as a library and a CLI (`python bump_version.py minor|major|show`).
- `trinity-agent/src/trinity/cli_dev.py` — new dev subcommand group containing `install-hooks` and `bump-major`.

### Modified

- `trinity-agent/src/trinity/cli.py` — register `trinity dev` subcommand group.
- `trinity-agent/CLAUDE.md` — document the auto-versioning behavior in a new "Versioning" section.

`bump_version.py` is the only place version-bumping logic lives. Hooks shell out to it, the CLI calls it via import. No duplication.

## Edge cases

| Case | Behavior |
|---|---|
| Commit touches only sibling apps (e.g., `oefr-website/`) | Hooks exit 0; version untouched. |
| `git commit --amend` | Hook skips bump (would otherwise burn a version on every amendment). |
| Mid-rebase | Hook skips bump (rewrites would otherwise burn many versions). |
| Major-bump commit (`chore(release):` prefix) | `pre-commit` skips bump; `post-commit` skips tagging (already done by `bump-major`). |
| Tag already exists for current version | `post-commit` warns and skips; safe to re-run. |
| Pre-commit fails partway (e.g., write error on `__init__.py`) | `set -e` aborts the commit; user fixes the underlying issue and retries. |
| `bump_version.py` invoked from any cwd | Resolves `pyproject.toml` and `__init__.py` paths relative to its own location (`__file__` → parent of `scripts/`), not cwd. Works regardless of where it's called from. |
| Working in a `git worktree` of the repo | `core.hooksPath` is set on the parent clone and inherited; hooks fire normally. |
| `git commit --no-verify` | Hooks bypassed entirely; no bump, no tag. (User opt-out — intentional.) |
| Multiple commits in a single push | Each commit was independently versioned and tagged at commit time; push delivers them all. |

## Testing strategy

Unit tests for `bump_version.py`:

- `bump_minor("0.1.0")` → `"0.2.0"`
- `bump_minor("1.5.3")` → `"1.6.0"` (patch resets)
- `bump_major("0.42.0")` → `"1.0.0"` (minor and patch reset)
- Round-trip: read → bump → write → re-read returns the new value.
- Refuses to write a version that's not strictly greater than the current.

Integration tests for the hooks (run inside a throwaway git repo):

- Commit touching `trinity-agent/foo.py` → version bumps, tag created.
- Commit touching `oefr-website/foo.tsx` → no bump, no tag.
- `git commit --amend` after a normal commit → no double bump.
- `trinity dev bump-major --reason "x"` followed by inspection → tag created, hook didn't double-bump.

Tests live at `trinity-agent/tests/test_versioning.py` (pytest) and `trinity-agent/tests/test_hooks.sh` (bats or plain bash with assertions).

## Rollout

1. Implement `bump_version.py` + tests.
2. Implement hooks + integration tests.
3. Implement `trinity dev` CLI group.
4. Update `CLAUDE.md`.
5. Run `trinity dev install-hooks` in the live `~/apps` clone.
6. Make the first qualifying commit; confirm `0.1.0 → 0.2.0` and `v0.2.0` tag created.

No data migration. No backwards-compat concerns (the package is at `0.1.0` with no published artifacts).

## Open questions

None — all design questions resolved during brainstorming.

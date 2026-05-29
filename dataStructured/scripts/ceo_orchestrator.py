"""CEO orchestration helpers — dispatch downstream employees as subprocesses."""
import concurrent.futures
import subprocess
from pathlib import Path
from typing import Callable

WORKSPACE = Path(__file__).resolve().parents[1]


class DispatchError(Exception):
    """Raised when a dispatched employee subprocess fails."""


def dispatch_employee(employee: str, task: str, timeout_sec: int = 3600) -> str:
    """Spawn `trinity run "<task>" -e <employee>` from the workspace.

    Returns stdout on success. Raises DispatchError on non-zero exit.
    """
    cmd = ["trinity", "run", task, "-e", employee]
    result = subprocess.run(
        cmd,
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    if result.returncode != 0:
        raise DispatchError(
            f"trinity run -e {employee} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


import json
from pathlib import Path


def next_pipeline_step(workspace: Path, slug: str) -> str:
    """Determine the next pipeline step for *slug* by reading state/.

    Returns one of: "data-engineer", "data-steward", "compliance-officer",
    "engineer", "done", or "blocked".
    """
    workspace = Path(workspace)
    products = workspace / "state" / "products" / slug
    launch_report = products / "launch-report.json"
    if launch_report.exists():
        report = json.loads(launch_report.read_text())
        if report.get("status") == "SHIPPED":
            return "done"
        if report.get("status") in ("FAILED", "BLOCKED"):
            return "blocked"

    ledger_dir = workspace / "state" / "ethics-ledger"
    ledger_files = list(ledger_dir.glob(f"*-{slug}.json"))
    if ledger_files:
        ledger = json.loads(ledger_files[-1].read_text())
        if ledger.get("verdict") == "PASS":
            return "engineer"
        return "blocked"

    dataset_dir = workspace / "state" / "datasets" / slug
    if dataset_dir.exists():
        clean = list(dataset_dir.glob("clean-*.csv"))
        if clean:
            return "compliance-officer"
        raw = list(dataset_dir.glob("raw-*.csv"))
        if raw:
            return "data-steward"

    return "data-engineer"


def format_daily_dm(
    date: str,
    advanced: list[str],
    shipped: list[dict],
    blocked: list[dict],
    running_tomorrow: str,
    cycle_cost_tokens: int,
) -> str:
    """Format the CEO's daily DM."""
    advanced_lines = "\n".join(f"- {s}" for s in advanced) or "- (none)"
    shipped_lines = (
        "\n".join(f"- {s['name']}: {s.get('stripe_url', '')} / {s.get('gumroad_url', '')}" for s in shipped)
        or "- (none)"
    )
    blocked_lines = (
        "\n".join(f"- {b['slug']}: {b['reason']}" for b in blocked) or "- (none)"
    )
    return (
        f"📊 DataStructured — {date}\n"
        "══════════════════════════════\n"
        "ADVANCED TODAY:\n"
        f"{advanced_lines}\n\n"
        "SHIPPED:\n"
        f"{shipped_lines}\n\n"
        "BLOCKED (needs you):\n"
        f"{blocked_lines}\n\n"
        "RUNNING TOMORROW:\n"
        f"- {running_tomorrow}\n\n"
        f"CYCLE COST: {cycle_cost_tokens:,} tokens\n"
    )


def dispatch_parallel(briefs: list[dict], runner: Callable[[dict], dict], max_concurrent: int = 3) -> list[dict]:
    """Run `runner(brief)` for each brief concurrently, bounded by max_concurrent.

    Each runner invocation returns a result dict; this returns the list of results
    in the same order as `briefs`. Exceptions are caught per-brief and embedded
    in the result dict so one brief's failure doesn't cancel siblings.
    """
    results: list[dict | None] = [None] * len(briefs)

    def _worker(index: int, brief: dict) -> tuple[int, dict]:
        try:
            return index, runner(brief)
        except Exception as exc:
            return index, {
                "slug": brief.get("slug"),
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as pool:
        futures = [pool.submit(_worker, i, b) for i, b in enumerate(briefs)]
        for fut in concurrent.futures.as_completed(futures):
            i, r = fut.result()
            results[i] = r

    return [r for r in results if r is not None]


def write_pipeline_status(workspace: Path, slug: str, status: dict) -> None:
    """Write a per-product pipeline-status snapshot under state/products/<slug>/."""
    path = workspace / "state" / "products" / slug / "pipeline-status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    import json
    from datetime import datetime, timezone
    payload = {
        **status,
        "slug": slug,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")

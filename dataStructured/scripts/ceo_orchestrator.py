"""CEO orchestration helpers — dispatch downstream employees as subprocesses."""
import subprocess
from pathlib import Path

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

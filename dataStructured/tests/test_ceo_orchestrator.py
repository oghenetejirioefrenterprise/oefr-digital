import subprocess
from unittest.mock import patch, MagicMock
import pytest

from scripts.ceo_orchestrator import dispatch_employee, DispatchError


def test_dispatch_runs_trinity_run_subprocess():
    fake = MagicMock(returncode=0, stdout="Done.", stderr="")
    with patch("subprocess.run", return_value=fake) as mock_run:
        out = dispatch_employee("data-engineer", "Harvest niche X")
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert cmd[0] == "trinity"
    assert cmd[1] == "run"
    assert cmd[2] == "Harvest niche X"
    assert cmd[3] == "-e"
    assert cmd[4] == "data-engineer"
    assert kwargs["cwd"].endswith("dataStructured")
    assert out == "Done."


def test_dispatch_raises_on_nonzero_exit():
    fake = MagicMock(returncode=1, stdout="", stderr="boom")
    with patch("subprocess.run", return_value=fake):
        with pytest.raises(DispatchError, match="boom"):
            dispatch_employee("data-engineer", "task")


def test_dispatch_passes_timeout():
    fake = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=fake) as mock_run:
        dispatch_employee("data-engineer", "task", timeout_sec=600)
    _, kwargs = mock_run.call_args
    assert kwargs["timeout"] == 600


from scripts.ceo_orchestrator import next_pipeline_step


def test_next_step_is_data_engineer_when_only_brief_exists(workspace):
    (workspace / "state" / "opportunities" / "2026-05-04-test.json").write_text("{}")
    step = next_pipeline_step(workspace, slug="test")
    assert step == "data-engineer"


def test_next_step_is_data_steward_when_raw_exists(workspace):
    (workspace / "state" / "opportunities" / "2026-05-04-test.json").write_text("{}")
    (workspace / "state" / "datasets" / "test").mkdir(parents=True)
    (workspace / "state" / "datasets" / "test" / "raw-2026-05-04.csv").write_text("a,b\n1,2")
    step = next_pipeline_step(workspace, slug="test")
    assert step == "data-steward"


def test_next_step_is_compliance_when_clean_exists(workspace):
    (workspace / "state" / "opportunities" / "2026-05-04-test.json").write_text("{}")
    (workspace / "state" / "datasets" / "test").mkdir(parents=True)
    (workspace / "state" / "datasets" / "test" / "raw-2026-05-04.csv").write_text("a,b\n1,2")
    (workspace / "state" / "datasets" / "test" / "clean-2026-05-04.csv").write_text("a,b\n1,2")
    step = next_pipeline_step(workspace, slug="test")
    assert step == "compliance-officer"


def test_next_step_is_engineer_when_ledger_passes(workspace):
    (workspace / "state" / "opportunities" / "2026-05-04-test.json").write_text("{}")
    dsdir = workspace / "state" / "datasets" / "test"; dsdir.mkdir(parents=True)
    (dsdir / "raw-2026-05-04.csv").write_text("a,b\n1,2")
    (dsdir / "clean-2026-05-04.csv").write_text("a,b\n1,2")
    (workspace / "state" / "ethics-ledger" / "2026-05-04-test.json").write_text('{"verdict": "PASS"}')
    step = next_pipeline_step(workspace, slug="test")
    assert step == "engineer"


def test_next_step_is_done_when_launch_report_shipped(workspace):
    pdir = workspace / "state" / "products" / "test"; pdir.mkdir(parents=True)
    (pdir / "launch-report.json").write_text('{"status": "SHIPPED"}')
    step = next_pipeline_step(workspace, slug="test")
    assert step == "done"

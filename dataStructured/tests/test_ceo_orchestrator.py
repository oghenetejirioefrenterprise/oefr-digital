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

import os
from scripts.lib.env import load_profile_env


def test_loads_quoted_and_bare(tmp_path, monkeypatch):
    p = tmp_path / ".profile"
    p.write_text(
        'export A="one"\n'
        "export B=two\n"
        "export C='three'\n"
        "# a comment line\n"
        "noexport=skip\n"
    )
    for k in ("A", "B", "C"):
        monkeypatch.delenv(k, raising=False)
    loaded = load_profile_env(p)
    assert loaded["A"] == "one"
    assert os.environ["B"] == "two"
    assert os.environ["C"] == "three"
    assert "noexport" not in loaded


def test_captures_final_line_without_newline(tmp_path, monkeypatch):
    p = tmp_path / ".profile"
    p.write_text('export LAST="endval"')  # no trailing newline
    monkeypatch.delenv("LAST", raising=False)
    loaded = load_profile_env(p)
    assert loaded["LAST"] == "endval"


def test_expands_var_references(tmp_path, monkeypatch):
    monkeypatch.setenv("BASEDIR", "/root")
    p = tmp_path / ".profile"
    p.write_text("export PATHX=$BASEDIR/bin\nexport PATHY=${BASEDIR}/lib\n")
    loaded = load_profile_env(p)
    assert loaded["PATHX"] == "/root/bin"
    assert loaded["PATHY"] == "/root/lib"


def test_missing_file_is_noop(tmp_path):
    assert load_profile_env(tmp_path / "does-not-exist") == {}


def test_no_override_keeps_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("KEEP", "original")
    p = tmp_path / ".profile"
    p.write_text("export KEEP=changed\n")
    load_profile_env(p, override=False)
    assert os.environ["KEEP"] == "original"


def test_override_replaces_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("REPL", "old")
    p = tmp_path / ".profile"
    p.write_text("export REPL=new\n")
    load_profile_env(p, override=True)
    assert os.environ["REPL"] == "new"

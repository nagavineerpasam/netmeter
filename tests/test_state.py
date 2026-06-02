import json, os, tempfile
from pathlib import Path
from netmeter.state import write_state, read_state, State

def test_round_trip(tmp_path):
    p = tmp_path / "abc.json"
    s = State(session_id="abc", claude_pid=123,
              bytes_in=1000, bytes_out=500,
              started_at="2026-06-03T10:00:00Z",
              updated_at="2026-06-03T10:00:01Z")
    write_state(p, s)
    got = read_state(p)
    assert got == s

def test_atomic_write_uses_rename(tmp_path, monkeypatch):
    """Writing should never leave a half-written .json visible."""
    p = tmp_path / "abc.json"
    real_rename = os.rename
    saw_tmp = []
    def spy_rename(src, dst):
        saw_tmp.append(str(src))
        return real_rename(src, dst)
    monkeypatch.setattr(os, "rename", spy_rename)
    write_state(p, State("abc", 1, 0, 0, "t", "t"))
    assert saw_tmp and saw_tmp[0].endswith(".tmp")

def test_read_missing_returns_none(tmp_path):
    assert read_state(tmp_path / "nope.json") is None

def test_read_corrupt_returns_none(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    assert read_state(p) is None

def test_error_field_round_trips(tmp_path):
    p = tmp_path / "err.json"
    s = State("abc", 1, 0, 0, "t", "t", error="nettop unavailable")
    write_state(p, s)
    got = read_state(p)
    assert got.error == "nettop unavailable"

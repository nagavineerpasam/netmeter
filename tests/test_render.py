import json, os, subprocess, sys
from pathlib import Path

ENTRY = Path(__file__).parent.parent / "plugin" / "bin" / "netmeter-render"

def run_render(state_dir, stdin_json, env_overrides=None):
    env = {**os.environ, "NETMETER_STATE_DIR": str(state_dir)}
    if env_overrides:
        env.update(env_overrides)
    p = subprocess.run([str(ENTRY)], input=stdin_json,
                       capture_output=True, text=True, env=env, timeout=5)
    return p.stdout.strip(), p.returncode

def test_missing_state_prints_nothing(tmp_path):
    out, rc = run_render(tmp_path, json.dumps({"session_id": "x"}))
    assert rc == 0
    assert out == ""

def test_renders_compact(tmp_path):
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": int(12.3 * 1024 * 1024),
        "bytes_out": int(4.1 * 1024 * 1024),
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}))
    assert rc == 0
    assert "12.3 MB" in out and "4.1 MB" in out
    assert "↓" in out and "↑" in out

def test_stale_shows_warning(tmp_path):
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": 1024 * 1024, "bytes_out": 0,
        "started_at": "1970-01-01T00:00:00Z",
        "updated_at": "1970-01-01T00:00:00Z",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}))
    assert rc == 0
    assert "⚠" in out

def test_error_field_renders_label(tmp_path):
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": 0, "bytes_out": 0,
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
        "error": "nettop unavailable",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}))
    assert rc == 0
    assert out == "netmeter: nettop unavailable"

def test_format_total(tmp_path):
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": int(12 * 1024 * 1024),
        "bytes_out": int(4 * 1024 * 1024),
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_FORMAT": "total"})
    assert rc == 0
    assert "↓" not in out
    assert "16.0 MB" in out

def test_format_verbose(tmp_path):
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": int(10 * 1024 * 1024),
        "bytes_out": int(2 * 1024 * 1024),
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_FORMAT": "verbose"})
    assert rc == 0
    assert out.startswith("net: ")
    assert "12.0 MB" in out

def test_no_session_id_silent(tmp_path):
    out, rc = run_render(tmp_path, json.dumps({}))
    assert rc == 0
    assert out == ""

def test_invalid_stdin_silent(tmp_path):
    out, rc = run_render(tmp_path, "not json")
    assert rc == 0
    assert out == ""

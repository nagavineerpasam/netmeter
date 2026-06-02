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

def test_renders_default_total_used(tmp_path):
    """Default compact mode shows '<total> used' — single number, no arrows."""
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": int(12.3 * 1024 * 1024),
        "bytes_out": int(4.1 * 1024 * 1024),
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}))
    assert rc == 0
    assert "16.4 MB used" in out
    assert "↓" not in out and "↑" not in out

def test_format_split_shows_arrows(tmp_path):
    """NETMETER_FORMAT=split brings back the old up/down arrow display."""
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": int(12.3 * 1024 * 1024),
        "bytes_out": int(4.1 * 1024 * 1024),
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_FORMAT": "split"})
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

def test_invalid_threshold_env_falls_back(tmp_path):
    """NETMETER_STALE_THRESHOLD_SEC=foo must not crash the render."""
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": 1024, "bytes_out": 512,
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_STALE_THRESHOLD_SEC": "foo"})
    assert rc == 0
    # default compact mode: shows total (1024+512 = 1536 bytes → "1 KB used")
    assert "1 KB used" in out


def _make_state(tmp_path, b_in, b_out):
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": b_in, "bytes_out": b_out,
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))

def test_right_align_pads_to_terminal_width(tmp_path):
    _make_state(tmp_path, 1024, 512)
    env = {**os.environ, "NETMETER_STATE_DIR": str(tmp_path), "NETMETER_ALIGN": "right"}
    p = subprocess.run([str(ENTRY)],
                       input=json.dumps({"session_id": "abc", "terminal_width": 80}),
                       capture_output=True, text=True, env=env, timeout=5)
    raw = p.stdout.rstrip("\n")
    assert raw.endswith("1 KB used"), f"got: {raw!r}"
    assert raw.startswith("   "), f"expected leading spaces, got: {raw!r}"
    assert len(raw) == 80, f"expected width 80, got {len(raw)}: {raw!r}"

def test_left_align_explicit_no_padding(tmp_path):
    _make_state(tmp_path, 1024, 512)
    env = {**os.environ, "NETMETER_STATE_DIR": str(tmp_path), "NETMETER_ALIGN": "left"}
    p = subprocess.run([str(ENTRY)],
                       input=json.dumps({"session_id": "abc", "terminal_width": 80}),
                       capture_output=True, text=True, env=env, timeout=5)
    raw = p.stdout.rstrip("\n")
    assert raw == "1 KB used", f"got: {raw!r}"

def test_center_align(tmp_path):
    _make_state(tmp_path, 1024, 512)
    env = {**os.environ, "NETMETER_STATE_DIR": str(tmp_path), "NETMETER_ALIGN": "center"}
    p = subprocess.run([str(ENTRY)],
                       input=json.dumps({"session_id": "abc", "terminal_width": 60}),
                       capture_output=True, text=True, env=env, timeout=5)
    raw = p.stdout.rstrip("\n")
    visible = "1 KB used"
    expected_pad = (60 - len(visible)) // 2
    assert raw == " " * expected_pad + visible, f"got: {raw!r}"

import json, os, subprocess, sys
from pathlib import Path

ENTRY = Path(__file__).parent.parent / "plugin" / "bin" / "netmeter-render"

# Most tests assert on semantic output (the bytes, the words). Default to no
# ANSI colours so substring assertions are clean. Colour tests opt in by
# overriding NETMETER_COLOR.

def run_render(state_dir, stdin_json, env_overrides=None):
    env = {**os.environ, "NETMETER_STATE_DIR": str(state_dir), "NETMETER_COLOR": "0"}
    if env_overrides:
        env.update(env_overrides)
    p = subprocess.run([str(ENTRY)], input=stdin_json,
                       capture_output=True, text=True, env=env, timeout=5)
    return p.stdout.strip(), p.returncode


def _make_state(tmp_path, b_in, b_out):
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": b_in, "bytes_out": b_out,
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))


# --- behaviour tests (colour disabled for clean substring assertions) ---

def test_missing_state_prints_nothing(tmp_path):
    out, rc = run_render(tmp_path, json.dumps({"session_id": "x"}))
    assert rc == 0
    assert out == ""

def test_renders_default_total_used(tmp_path):
    """Default compact mode shows 'net  <total> used' — single number, no arrows."""
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": int(12.3 * 1024 * 1024),
        "bytes_out": int(4.1 * 1024 * 1024),
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}))
    assert rc == 0
    assert "net" in out
    assert "16.4 MB" in out
    assert "used" in out
    assert "↓" not in out and "↑" not in out

def test_format_split_shows_arrows(tmp_path):
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
    assert out == "16.0 MB  │  0.0 Mbps"

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
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": 1024, "bytes_out": 512,
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_STALE_THRESHOLD_SEC": "foo"})
    assert rc == 0
    # default compact mode: 'net  1 KB used' (1024+512 = 1536 bytes → 1 KB)
    assert "net" in out and "1 KB" in out and "used" in out


# --- alignment tests (compute visible width from the colourless output) ---

def _no_color_env(tmp_path, **extra):
    env = {**os.environ, "NETMETER_STATE_DIR": str(tmp_path), "NETMETER_COLOR": "0"}
    env.update(extra)
    return env

def test_right_align_pads_to_terminal_width(tmp_path):
    _make_state(tmp_path, 1024, 512)
    env = _no_color_env(tmp_path, NETMETER_ALIGN="right")
    p = subprocess.run([str(ENTRY)],
                       input=json.dumps({"session_id": "abc", "terminal_width": 80}),
                       capture_output=True, text=True, env=env, timeout=5)
    raw = p.stdout.rstrip("\n")
    assert raw.endswith("0.0 Mbps"), f"got: {raw!r}"
    assert raw.startswith("   "), f"expected leading spaces, got: {raw!r}"
    assert len(raw) == 80, f"expected width 80, got {len(raw)}: {raw!r}"

def test_left_align_explicit_no_padding(tmp_path):
    _make_state(tmp_path, 1024, 512)
    env = _no_color_env(tmp_path, NETMETER_ALIGN="left")
    p = subprocess.run([str(ENTRY)],
                       input=json.dumps({"session_id": "abc", "terminal_width": 80}),
                       capture_output=True, text=True, env=env, timeout=5)
    raw = p.stdout.rstrip("\n")
    assert raw == "net  1 KB used  │  0.0 Mbps", f"got: {raw!r}"

def test_center_align(tmp_path):
    _make_state(tmp_path, 1024, 512)
    env = _no_color_env(tmp_path, NETMETER_ALIGN="center")
    p = subprocess.run([str(ENTRY)],
                       input=json.dumps({"session_id": "abc", "terminal_width": 60}),
                       capture_output=True, text=True, env=env, timeout=5)
    raw = p.stdout.rstrip("\n")
    visible = "net  1 KB used  │  0.0 Mbps"
    expected_pad = (60 - len(visible)) // 2
    assert raw == " " * expected_pad + visible, f"got: {raw!r}"


# --- colour tests (opt-in) ---

def _color_env(tmp_path, **extra):
    env = {**os.environ, "NETMETER_STATE_DIR": str(tmp_path)}
    env.pop("NETMETER_COLOR", None)
    env.update(extra)
    return env

def test_colors_present_when_enabled(tmp_path):
    """ANSI escapes appear by default — cyan label, dim 'used'."""
    _make_state(tmp_path, 1024, 512)
    p = subprocess.run([str(ENTRY)],
                       input=json.dumps({"session_id": "abc"}),
                       capture_output=True, text=True,
                       env=_color_env(tmp_path, NETMETER_ALIGN="left"),
                       timeout=5)
    raw = p.stdout.rstrip("\n")
    assert "\x1b[36m" in raw      # cyan for 'net'
    assert "\x1b[2m" in raw       # dim for 'used'
    assert "\x1b[0m" in raw       # at least one reset

def test_byte_value_is_green(tmp_path):
    """The byte value renders in green regardless of magnitude — single colour by design."""
    for total in (1024, 30 * 1024 * 1024, 600 * 1024 * 1024):
        _make_state(tmp_path, total, 0)
        p = subprocess.run([str(ENTRY)],
                           input=json.dumps({"session_id": "abc"}),
                           capture_output=True, text=True,
                           env=_color_env(tmp_path, NETMETER_ALIGN="left"),
                           timeout=5)
        raw = p.stdout.rstrip("\n")
        assert "\x1b[32m" in raw, f"expected green for {total} bytes, got: {raw!r}"
        # Stale ⚠ is yellow and error label is red — neither should appear in
        # a fresh, non-error state file.
        assert "\x1b[33m" not in raw, f"unexpected yellow for {total} bytes"
        assert "\x1b[31m" not in raw, f"unexpected red for {total} bytes"

def test_color_off_strips_ansi(tmp_path):
    _make_state(tmp_path, 1024, 512)
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_ALIGN": "left"})
    assert rc == 0
    assert "\x1b[" not in out
    assert out == "net  1 KB used  │  0.0 Mbps"


def _make_state_with_rate(tmp_path, b_in, b_out, rate_bps):
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": b_in, "bytes_out": b_out,
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
        "rate_bytes_per_sec": rate_bps,
    }))

def test_compact_shows_mbps_segment(tmp_path):
    """Default compact mode: 'net  X used  │  Y.Y Mbps'."""
    # 525000 bytes/sec = 4.2 Mbps (×8 / 1_000_000)
    _make_state_with_rate(tmp_path, 1024, 0, 525000.0)
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_ALIGN": "left"})
    assert rc == 0
    assert "│" in out
    assert "4.2 Mbps" in out

def test_idle_shows_zero_mbps(tmp_path):
    _make_state_with_rate(tmp_path, 0, 0, 0.0)
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_ALIGN": "left"})
    assert rc == 0
    assert "0.0 Mbps" in out

def test_total_mode_shows_mbps(tmp_path):
    _make_state_with_rate(tmp_path, 1024, 0, 525000.0)
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_FORMAT": "total", "NETMETER_ALIGN": "left"})
    assert rc == 0
    assert "│" in out and "4.2 Mbps" in out

def test_split_mode_shows_mbps(tmp_path):
    _make_state_with_rate(tmp_path, 1024, 512, 525000.0)
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_FORMAT": "split", "NETMETER_ALIGN": "left"})
    assert rc == 0
    assert "↓" in out and "↑" in out
    assert "│" in out and "4.2 Mbps" in out

def test_verbose_mode_includes_mbps_inside_parens(tmp_path):
    _make_state_with_rate(tmp_path, 1024, 512, 525000.0)
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_FORMAT": "verbose", "NETMETER_ALIGN": "left"})
    assert rc == 0
    # verbose: 'net: X (↓Y ↑Z, R.R Mbps)' — Mbps is inside the parens, no '│'.
    assert "│" not in out
    assert "(" in out and ")" in out
    assert "4.2 Mbps" in out

def test_color_off_strips_ansi_includes_mbps(tmp_path):
    _make_state_with_rate(tmp_path, 1024, 0, 525000.0)
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_ALIGN": "left"})
    # run_render already sets NETMETER_COLOR=0
    assert rc == 0
    assert "\x1b[" not in out
    assert out == "net  1 KB used  │  4.2 Mbps"


# --- mascot tier tests (opt-in via NETMETER_MASCOT=1) ---

def _mascot_run(tmp_path, rate_bps, fmt="compact"):
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": 0, "bytes_out": 0,
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
        "rate_bytes_per_sec": rate_bps,
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_MASCOT": "1",
                                       "NETMETER_FORMAT": fmt,
                                       "NETMETER_ALIGN": "left"})
    return out, rc

def test_mascot_off_by_default(tmp_path):
    """Without NETMETER_MASCOT=1, no emoji appears."""
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": 0, "bytes_out": 0,
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
        "rate_bytes_per_sec": 1_000_000.0,  # 8 Mbps
    }))
    out, rc = run_render(tmp_path, json.dumps({"session_id": "abc"}),
                        env_overrides={"NETMETER_ALIGN": "left"})
    assert rc == 0
    # None of the tier glyphs should appear
    for glyph in ("🐌", "🐢", "🐇", "🚀"):
        assert glyph not in out, f"unexpected mascot {glyph} in default output: {out!r}"

def test_mascot_snail_at_idle(tmp_path):
    out, rc = _mascot_run(tmp_path, 0.0)
    assert rc == 0
    assert "🐌" in out
    for glyph in ("🐢", "🐇", "🚀"):
        assert glyph not in out

def test_mascot_turtle_for_sub_mbps(tmp_path):
    # 0.5 Mbps = 62500 bytes/sec
    out, rc = _mascot_run(tmp_path, 62500.0)
    assert rc == 0
    assert "🐢" in out
    for glyph in ("🐌", "🐇", "🚀"):
        assert glyph not in out

def test_mascot_rabbit_for_low_active(tmp_path):
    # 4 Mbps = 500000 bytes/sec
    out, rc = _mascot_run(tmp_path, 500000.0)
    assert rc == 0
    assert "🐇" in out
    for glyph in ("🐌", "🐢", "🚀"):
        assert glyph not in out

def test_mascot_single_rocket_for_heavy(tmp_path):
    # 24 Mbps = 3000000 bytes/sec
    out, rc = _mascot_run(tmp_path, 3000000.0)
    assert rc == 0
    assert "🚀" in out
    # exactly one rocket, not two
    assert out.count("🚀") == 1

def test_mascot_double_rocket_for_50plus(tmp_path):
    # 60 Mbps = 7500000 bytes/sec
    out, rc = _mascot_run(tmp_path, 7500000.0)
    assert rc == 0
    assert out.count("🚀") == 2

def test_mascot_boundary_50mbps_is_double(tmp_path):
    # exactly 50 Mbps = 6250000 bytes/sec — boundary, should be double rocket
    out, rc = _mascot_run(tmp_path, 6250000.0)
    assert rc == 0
    assert out.count("🚀") == 2

def test_mascot_appears_in_all_modes(tmp_path):
    """All four format modes should accept the mascot."""
    for fmt in ("compact", "total", "split", "verbose"):
        out, rc = _mascot_run(tmp_path, 500000.0, fmt=fmt)  # 4 Mbps → 🐇
        assert rc == 0, f"non-zero rc in mode {fmt}"
        assert "🐇" in out, f"no rabbit in mode {fmt}: {out!r}"

def test_mascot_verbose_emoji_after_closing_paren(tmp_path):
    out, rc = _mascot_run(tmp_path, 500000.0, fmt="verbose")
    assert rc == 0
    # The rabbit comes after the ')' of the verbose paren block
    paren_pos = out.rfind(")")
    rabbit_pos = out.find("🐇")
    assert paren_pos != -1 and rabbit_pos != -1
    assert rabbit_pos > paren_pos

def test_mascot_enabled_via_marker_file(tmp_path):
    """A 'mascot' marker file in the state dir opts in even without the env var."""
    (tmp_path / "abc.json").write_text(json.dumps({
        "session_id": "abc", "claude_pid": 1,
        "bytes_in": 0, "bytes_out": 0,
        "started_at": "t", "updated_at": "9999-01-01T00:00:00Z",
        "rate_bytes_per_sec": 500000.0,  # 4 Mbps → rabbit
    }))
    (tmp_path / "mascot").touch()
    # Note: NO NETMETER_MASCOT set, only the file
    env = {**os.environ, "NETMETER_STATE_DIR": str(tmp_path),
           "NETMETER_COLOR": "0", "NETMETER_ALIGN": "left"}
    env.pop("NETMETER_MASCOT", None)
    p = subprocess.run([str(ENTRY)],
                       input=json.dumps({"session_id": "abc"}),
                       capture_output=True, text=True, env=env, timeout=5)
    raw = p.stdout.rstrip("\n")
    assert "🐇" in raw, f"expected rabbit via marker file, got: {raw!r}"

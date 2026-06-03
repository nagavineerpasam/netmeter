import json, os, subprocess, sys, time, signal
from pathlib import Path
import pytest
from netmeter.daemon import _compute_rate

@pytest.fixture
def fake_nettop(tmp_path):
    """A fake `nettop` that emits real-format delta samples and stays alive.

    Format MUST match what the parser expects (whitespace + units):
      'time      bytes_in   bytes_out'
      '00:00:00 python.PID   1000 B   500 B'

    Emits three header blocks so the daemon flushes the first two samples
    before we assert (daemon only flushes a sample when it sees the NEXT header).
    """
    my_pid = os.getpid()
    script = tmp_path / "fake_nettop"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, time\n"
        "# Sample 1\n"
        "print('time      bytes_in   bytes_out')\n"
        f"print('00:00:01 python.{my_pid}   1000 B   500 B')\n"
        "sys.stdout.flush()\n"
        "time.sleep(0.2)\n"
        "# Sample 2\n"
        "print('time      bytes_in   bytes_out')\n"
        f"print('00:00:02 python.{my_pid}   2000 B   1000 B')\n"
        "sys.stdout.flush()\n"
        "time.sleep(0.2)\n"
        "# Sample 3 header — triggers flush of sample 2 by the daemon\n"
        "print('time      bytes_in   bytes_out')\n"
        "sys.stdout.flush()\n"
        "time.sleep(10)\n"
    )
    script.chmod(0o755)
    return script

def test_daemon_accumulates_deltas(tmp_path, fake_nettop):
    state_dir = tmp_path / "state"
    state_file = state_dir / "test-session.json"
    env = {**os.environ,
           "NETMETER_STATE_DIR": str(state_dir),
           "NETMETER_NETTOP_BIN": str(fake_nettop)}

    proc = subprocess.Popen(
        [sys.executable, "-m", "netmeter.daemon",
         "--session-id", "test-session",
         "--claude-pid", str(os.getpid())],
        env=env,
        cwd=str(Path(__file__).parent.parent / "plugin" / "bin"),
    )
    try:
        # wait up to 5s for both deltas to be accumulated
        deadline = time.monotonic() + 5
        last = {}
        while time.monotonic() < deadline:
            if state_file.exists():
                try:
                    last = json.loads(state_file.read_text())
                    if last.get("bytes_in", 0) >= 3000:
                        break
                except json.JSONDecodeError:
                    pass
            time.sleep(0.1)
        assert last.get("bytes_in") == 3000, f"got: {last}"
        assert last.get("bytes_out") == 1500, f"got: {last}"
        assert last["session_id"] == "test-session"
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait()


def test_daemon_writes_initial_zero_state(tmp_path, fake_nettop):
    """Daemon should write a 0-byte state file immediately before nettop emits."""
    state_dir = tmp_path / "state"
    state_file = state_dir / "init-session.json"
    env = {**os.environ,
           "NETMETER_STATE_DIR": str(state_dir),
           "NETMETER_NETTOP_BIN": str(fake_nettop)}
    proc = subprocess.Popen(
        [sys.executable, "-m", "netmeter.daemon",
         "--session-id", "init-session",
         "--claude-pid", str(os.getpid())],
        env=env,
        cwd=str(Path(__file__).parent.parent / "plugin" / "bin"),
    )
    try:
        for _ in range(20):
            if state_file.exists():
                break
            time.sleep(0.05)
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["bytes_in"] == 0
        assert data["bytes_out"] == 0
        assert data["session_id"] == "init-session"
    finally:
        proc.send_signal(signal.SIGTERM)
        try: proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait()


def test_daemon_writes_error_when_nettop_missing(tmp_path):
    """If NETMETER_NETTOP_BIN points to a nonexistent file, state file should record the error."""
    state_dir = tmp_path / "state"
    state_file = state_dir / "missing.json"
    env = {**os.environ,
           "NETMETER_STATE_DIR": str(state_dir),
           "NETMETER_NETTOP_BIN": str(tmp_path / "does-not-exist")}
    proc = subprocess.run(
        [sys.executable, "-m", "netmeter.daemon",
         "--session-id", "missing",
         "--claude-pid", str(os.getpid())],
        env=env,
        cwd=str(Path(__file__).parent.parent / "plugin" / "bin"),
        timeout=5,
    )
    data = json.loads(state_file.read_text())
    assert data.get("error") == "nettop unavailable"


def test_compute_rate_empty():
    assert _compute_rate([]) == 0.0


def test_compute_rate_single_sample():
    assert _compute_rate([(0.0, 1000)]) == 0.0


def test_compute_rate_two_samples():
    # 2000 bytes over 1.0 second → 2000 bytes/sec
    assert _compute_rate([(0.0, 0), (1.0, 2000)]) == 2000.0


def test_compute_rate_uses_first_and_last_only():
    # Spans 3 seconds, total grew by 6000 bytes → 2000 bytes/sec
    assert _compute_rate([(0.0, 0), (1.0, 999), (2.0, 4321), (3.0, 6000)]) == 2000.0


def test_compute_rate_handles_zero_dt():
    # Same timestamp on both ends: don't divide by zero.
    rate = _compute_rate([(5.0, 100), (5.0, 200)])
    assert rate >= 0  # Doesn't crash; value is implementation-defined but finite.

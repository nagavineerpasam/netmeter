"""netmeter daemon: stream nettop, accumulate deltas for the claude PID tree."""

from __future__ import annotations
import argparse, datetime, os, shutil, signal, subprocess, sys, time
from collections import deque
from pathlib import Path
from .state import State, write_state, read_state
from .parser import parse_samples
from .proctree import descendants, is_alive

PROC_REFRESH_SEC = 2.0
LIVENESS_CHECK_SEC = 2.0

def _compute_rate(samples) -> float:
    """Bytes-per-second over the span of the samples.

    `samples` is a sequence of (monotonic_time, total_bytes_so_far). Uses
    only the first and last entries; intermediate samples don't matter
    because the underlying counter is monotonic.
    """
    if len(samples) < 2:
        return 0.0
    oldest_t, oldest_b = samples[0]
    newest_t, newest_b = samples[-1]
    dt = max(newest_t - oldest_t, 1e-3)
    return (newest_b - oldest_b) / dt

def now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def state_dir() -> Path:
    return Path(os.environ.get(
        "NETMETER_STATE_DIR",
        Path.home() / ".claude" / "plugins" / "data" / "netmeter"
    ))

def nettop_bin() -> str:
    return os.environ.get("NETMETER_NETTOP_BIN", "nettop")

def sweep_stale(dir_: Path) -> None:
    """Remove state files whose claude_pid is no longer alive."""
    if not dir_.exists():
        return
    for f in dir_.glob("*.json"):
        s = read_state(f)
        if s and not is_alive(s.claude_pid):
            try:
                f.unlink()
            except OSError:
                pass

def run(session_id: str, claude_pid: int) -> int:
    sd = state_dir()
    sd.mkdir(parents=True, exist_ok=True)
    sweep_stale(sd)
    state_path = sd / f"{session_id}.json"

    state = State(
        session_id=session_id, claude_pid=claude_pid,
        bytes_in=0, bytes_out=0,
        started_at=now_iso(), updated_at=now_iso(),
    )
    write_state(state_path, state)

    bin_ = nettop_bin()
    # If bin is an absolute path, shutil.which won't find it unless executable;
    # check both absolute existence and PATH lookup.
    bin_path = bin_ if (os.path.isabs(bin_) and os.access(bin_, os.X_OK)) else shutil.which(bin_)
    if not bin_path:
        state.error = "nettop unavailable"
        state.updated_at = now_iso()
        write_state(state_path, state)
        return 1

    nettop = subprocess.Popen(
        [bin_path, "-P", "-J", "bytes_in,bytes_out", "-d", "-s", "1", "-l", "0"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1,
    )
    assert nettop.stdout is not None

    pids = descendants(claude_pid)
    last_proc_refresh = time.monotonic()
    last_liveness = time.monotonic()
    buf: list[str] = []
    rate_samples: deque = deque(maxlen=4)

    try:
        for line in nettop.stdout:
            now = time.monotonic()

            if now - last_proc_refresh > PROC_REFRESH_SEC:
                pids = descendants(claude_pid)
                last_proc_refresh = now

            if now - last_liveness > LIVENESS_CHECK_SEC:
                if not is_alive(claude_pid):
                    break
                last_liveness = now

            # A new header marks the boundary of the previous sample — flush buf.
            if "bytes_in" in line and "bytes_out" in line and buf:
                _accumulate(buf, pids, state)
                state.updated_at = now_iso()
                rate_samples.append((now, state.bytes_in + state.bytes_out))
                state.rate_bytes_per_sec = _compute_rate(list(rate_samples))
                write_state(state_path, state)
                buf = []
            buf.append(line)

        if buf:
            _accumulate(buf, pids, state)
            state.updated_at = now_iso()
            rate_samples.append((time.monotonic(), state.bytes_in + state.bytes_out))
            state.rate_bytes_per_sec = _compute_rate(list(rate_samples))
            write_state(state_path, state)
    finally:
        try:
            nettop.terminate()
            nettop.wait(timeout=2)
        except Exception:
            pass
    return 0

def _accumulate(buf: list[str], pids: set[int], state: State) -> None:
    text = "".join(buf)
    for sample in parse_samples(text):
        for row in sample.rows:
            if row.pid in pids:
                state.bytes_in += row.bytes_in
                state.bytes_out += row.bytes_out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-id", required=True)
    ap.add_argument("--claude-pid", required=True, type=int)
    args = ap.parse_args()

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    return run(args.session_id, args.claude_pid)

if __name__ == "__main__":
    sys.exit(main())

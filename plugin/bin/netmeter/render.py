"""Statusline render: read state, print one line."""

from __future__ import annotations
import datetime, json, os, sys
from pathlib import Path
from .formatter import bytes_to_human
from .state import read_state

DEFAULT_STALE_SEC = 10

def state_dir() -> Path:
    return Path(os.environ.get(
        "NETMETER_STATE_DIR",
        Path.home() / ".claude" / "plugins" / "data" / "netmeter"
    ))

def parse_iso(s: str):
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None

def is_stale(updated_at: str, threshold_sec: int) -> bool:
    ts = parse_iso(updated_at)
    if ts is None:
        return False
    age = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds()
    return age > threshold_sec

def format_line(b_in: int, b_out: int, mode: str) -> str:
    h_in = bytes_to_human(b_in)
    h_out = bytes_to_human(b_out)
    if mode == "total":
        return bytes_to_human(b_in + b_out)
    if mode == "verbose":
        return f"net: {bytes_to_human(b_in + b_out)} (↓{h_in} ↑{h_out})"
    return f"↓ {h_in}  ↑ {h_out}"

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    session_id = payload.get("session_id")
    if not session_id:
        return 0

    state = read_state(state_dir() / f"{session_id}.json")
    if state is None:
        return 0
    if state.error:
        print(f"netmeter: {state.error}")
        return 0

    threshold = int(os.environ.get("NETMETER_STALE_THRESHOLD_SEC", DEFAULT_STALE_SEC))
    mode = os.environ.get("NETMETER_FORMAT", "compact")
    line = format_line(state.bytes_in, state.bytes_out, mode)
    if is_stale(state.updated_at, threshold):
        line = line + " ⚠"
    print(line)
    return 0

if __name__ == "__main__":
    sys.exit(main())

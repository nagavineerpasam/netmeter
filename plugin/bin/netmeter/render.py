"""Statusline render: read state, print one line."""

from __future__ import annotations
import datetime, json, os, shutil, sys
from pathlib import Path
from .formatter import bytes_to_human
from .state import read_state

DEFAULT_STALE_SEC = 10
DEFAULT_ALIGN = "right"
FALLBACK_WIDTH = 120

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

def terminal_width(payload: dict) -> int:
    """Best-effort terminal column count: payload hint → env → shutil → fallback."""
    for key in ("terminal_width", "cols", "columns", "width"):
        v = payload.get(key)
        if isinstance(v, int) and v > 0:
            return v
    env_cols = os.environ.get("COLUMNS")
    if env_cols and env_cols.isdigit():
        return int(env_cols)
    try:
        size = shutil.get_terminal_size((FALLBACK_WIDTH, 24))
        if size.columns > 0:
            return size.columns
    except OSError:
        pass
    return FALLBACK_WIDTH

def align_line(line: str, mode: str, width: int) -> str:
    """Pad `line` left or center; right-padding adds nothing useful for a statusline."""
    visible = len(line)
    pad = max(0, width - visible)
    if mode == "right":
        return " " * pad + line
    if mode == "center":
        return " " * (pad // 2) + line
    return line

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

    try:
        threshold = int(os.environ.get("NETMETER_STALE_THRESHOLD_SEC", DEFAULT_STALE_SEC))
    except ValueError:
        threshold = DEFAULT_STALE_SEC
    mode = os.environ.get("NETMETER_FORMAT", "compact")
    line = format_line(state.bytes_in, state.bytes_out, mode)
    if is_stale(state.updated_at, threshold):
        line = line + " ⚠"
    align = os.environ.get("NETMETER_ALIGN", DEFAULT_ALIGN)
    if align in ("right", "center"):
        line = align_line(line, align, terminal_width(payload))
    print(line)
    return 0

if __name__ == "__main__":
    sys.exit(main())

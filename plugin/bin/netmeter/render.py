"""Statusline render: read state, print one line."""

from __future__ import annotations
import datetime, json, os, re, shutil, sys
from pathlib import Path
from .formatter import bytes_to_human
from .state import read_state

DEFAULT_STALE_SEC = 10
DEFAULT_ALIGN = "right"
FALLBACK_WIDTH = 120

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Colours intentionally match the style of the Claude Code model+context bar:
#   cyan label, green value, dim grey suffix. Yellow is reserved for the
#   stale-marker, red for the error label.
CYAN   = "\033[36m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
RESET  = "\033[0m"

MBPS_BITS_PER_BYTE = 8
MBPS_DIVISOR = 1_000_000  # SI megabits (matches what ISPs and speedtests use)


def _colour_enabled() -> bool:
    return os.environ.get("NETMETER_COLOR", "1") != "0"


def _wrap(text: str, code: str) -> str:
    if not code or not _colour_enabled():
        return text
    return f"{code}{text}{RESET}"


def _value_colour(_n: int) -> str:
    """Byte values render in green. Single colour by design — netmeter
    measures usage, not a limit, so a traffic-light scheme would invent
    thresholds that don't exist for every user."""
    return GREEN


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


def _format_mbps(rate_bytes_per_sec: float) -> str:
    """Convert bytes/sec to a one-decimal Mbps string, e.g. '4.2 Mbps'."""
    mbps = max(rate_bytes_per_sec, 0.0) * MBPS_BITS_PER_BYTE / MBPS_DIVISOR
    return f"{mbps:.1f} Mbps"


# Mascot tier: speed-kingdom escalation when NETMETER_MASCOT=1.
_MASCOT_TIERS = (
    (0.1,        "🐌"),
    (1.0,        "🐢"),
    (10.0,       "🐇"),
    (50.0,       "🚀"),
    (float("inf"), "🚀🚀"),
)

def _mascot_for(mbps: float) -> str:
    for upper, glyph in _MASCOT_TIERS:
        if mbps < upper:
            return glyph
    return _MASCOT_TIERS[-1][1]

def _mascot_enabled() -> bool:
    return os.environ.get("NETMETER_MASCOT", "0") == "1"


def format_line(b_in: int, b_out: int, mode: str, rate_bps: float = 0.0) -> str:
    h_in    = bytes_to_human(b_in)
    h_out   = bytes_to_human(b_out)
    h_total = bytes_to_human(b_in + b_out)
    mbps    = _format_mbps(rate_bps)

    sep         = _wrap("│", DIM)
    rate_styled = _wrap(mbps, GREEN)

    mascot_suffix = ""
    if _mascot_enabled():
        mbps_value = max(rate_bps, 0.0) * MBPS_BITS_PER_BYTE / MBPS_DIVISOR
        mascot_suffix = "  " + _mascot_for(mbps_value)

    if mode == "total":
        return f"{_wrap(h_total, _value_colour(b_in + b_out))}  {sep}  {rate_styled}{mascot_suffix}"

    if mode == "split":
        return (
            f"{_wrap('↓', CYAN)} {_wrap(h_in,  _value_colour(b_in))}  "
            f"{_wrap('↑', CYAN)} {_wrap(h_out, _value_colour(b_out))}"
            f"  {sep}  {rate_styled}{mascot_suffix}"
        )

    if mode == "verbose":
        return (
            f"{_wrap('net:', CYAN)} {_wrap(h_total, _value_colour(b_in + b_out))} "
            f"({_wrap('↓', CYAN)}{h_in} {_wrap('↑', CYAN)}{h_out}, {rate_styled}){mascot_suffix}"
        )

    # default 'compact'
    return (
        f"{_wrap('net', CYAN)}  "
        f"{_wrap(h_total, _value_colour(b_in + b_out))} "
        f"{_wrap('used', DIM)}  {sep}  {rate_styled}{mascot_suffix}"
    )


def visible_len(s: str) -> int:
    """Length excluding ANSI colour escapes, so right-alignment hits the real edge."""
    return len(ANSI_RE.sub("", s))


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
    """Pad based on visible width (excluding ANSI escapes)."""
    pad = max(0, width - visible_len(line))
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
        print(_wrap(f"netmeter: {state.error}", RED))
        return 0

    try:
        threshold = int(os.environ.get("NETMETER_STALE_THRESHOLD_SEC", DEFAULT_STALE_SEC))
    except ValueError:
        threshold = DEFAULT_STALE_SEC
    mode = os.environ.get("NETMETER_FORMAT", "compact")
    line = format_line(state.bytes_in, state.bytes_out, mode, state.rate_bytes_per_sec)
    if is_stale(state.updated_at, threshold):
        line = line + " " + _wrap("⚠", YELLOW)
    align = os.environ.get("NETMETER_ALIGN", DEFAULT_ALIGN)
    if align in ("right", "center"):
        line = align_line(line, align, terminal_width(payload))
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

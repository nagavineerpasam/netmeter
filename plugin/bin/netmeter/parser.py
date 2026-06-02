"""Parse nettop -P -J bytes_in,bytes_out -d output into per-sample Row sets.

Actual format observed on macOS (see tests/fixtures/nettop_sample.txt):
  - Whitespace-delimited fixed-width text (NOT comma-separated).
  - Header line: starts with 'time' and contains 'bytes_in' and 'bytes_out'.
  - Sample separator: a new header line marks the start of the next sample.
  - Data rows: '<HH:MM:SS.us> <procname>.<pid>  <value> <unit>  <value> <unit>'
      e.g.  '00:49:42.157210 launchd.1   235 KiB   0 B'
      e.g.  '00:49:43.152754 Code Helper.1480   0 B   0 B'
  - Process names MAY contain spaces and/or dots.
    The PID is the numeric suffix after the LAST dot in the second-to-last
    cluster of tokens (everything between the timestamp and the 4 trailing
    value/unit tokens).
  - Byte values use human-readable units: B, KiB, MiB, GiB.
    These are converted to integer byte counts.

Deviation from the original skeleton:
  - No comma splitting — lines are split on whitespace.
  - Values arrive with units (B / KiB / MiB / GiB); conversion to bytes is needed.
  - The proc+pid field is built from parts[1:-4] (not a fixed column index).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, List

# Match '<name>.<pid>' where name may contain dots and spaces
PROC_PID = re.compile(r"^(?P<name>.+)\.(?P<pid>\d+)$")

# Human-readable byte unit multipliers
_UNIT_MULT: dict[str, int] = {
    "B": 1,
    "KiB": 1024,
    "MiB": 1024 ** 2,
    "GiB": 1024 ** 3,
    "TiB": 1024 ** 4,
}


def _to_bytes(value: str, unit: str) -> int:
    """Convert a human-readable size token pair to an integer byte count.

    Raises ValueError on unknown unit so the caller can skip the row
    instead of silently recording the wrong byte count.
    """
    mult = _UNIT_MULT.get(unit)
    if mult is None:
        raise ValueError(f"unknown nettop unit: {unit!r}")
    try:
        # value may be a float string like '1.5' for large units
        return int(float(value) * mult)
    except ValueError:
        return 0


@dataclass
class Row:
    pid: int
    bytes_in: int
    bytes_out: int


@dataclass
class Sample:
    rows: List[Row] = field(default_factory=list)


def parse_samples(text: str) -> Iterator[Sample]:
    """Yield one Sample per nettop reporting interval found in *text*."""
    sample: Sample | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Header line: 'time ... bytes_in ... bytes_out'
        if "bytes_in" in stripped and "bytes_out" in stripped:
            if sample is not None:
                yield sample
            sample = Sample()
            continue

        if sample is None:
            continue

        # Data row: split on whitespace
        # Layout: [timestamp, proc_token(s)..., b_in_val, b_in_unit, b_out_val, b_out_unit]
        parts = stripped.split()
        if len(parts) < 6:
            # Need at least: timestamp + proc.pid + 4 value tokens
            continue

        # Last 4 tokens are: b_in_value, b_in_unit, b_out_value, b_out_unit
        b_out_unit = parts[-1]
        b_out_val = parts[-2]
        b_in_unit = parts[-3]
        b_in_val = parts[-4]

        # Everything between the timestamp (index 0) and the value tokens is proc+pid
        proc_and_pid = " ".join(parts[1:-4])
        m = PROC_PID.match(proc_and_pid)
        if not m:
            continue

        try:
            pid = int(m.group("pid"))
            b_in = _to_bytes(b_in_val, b_in_unit)
            b_out = _to_bytes(b_out_val, b_out_unit)
        except (ValueError, KeyError):
            continue

        sample.rows.append(Row(pid=pid, bytes_in=b_in, bytes_out=b_out))

    if sample is not None:
        yield sample

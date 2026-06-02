"""Per-session state file: atomic write, safe read."""

from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, os
from typing import Optional

@dataclass
class State:
    session_id: str
    claude_pid: int
    bytes_in: int
    bytes_out: int
    started_at: str
    updated_at: str
    error: Optional[str] = None

def write_state(path: Path, state: State) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(state)
    if data.get("error") is None:
        data.pop("error", None)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.rename(tmp, path)

def read_state(path: Path) -> Optional[State]:
    try:
        with open(path) as f:
            data = json.load(f)
        return State(**data)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return None

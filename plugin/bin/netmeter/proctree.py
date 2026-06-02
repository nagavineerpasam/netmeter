"""Process-tree helpers built on `pgrep -P` and `kill -0`."""

from __future__ import annotations
import os, subprocess
from typing import Set

def _children(pid: int) -> Set[int]:
    try:
        out = subprocess.check_output(
            ["pgrep", "-P", str(pid)], text=True, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return set()
    return {int(line) for line in out.split() if line.strip().isdigit()}

def descendants(root_pid: int) -> Set[int]:
    seen = {root_pid}
    frontier = {root_pid}
    while frontier:
        next_frontier: Set[int] = set()
        for pid in frontier:
            for child in _children(pid):
                if child not in seen:
                    seen.add(child)
                    next_frontier.add(child)
        frontier = next_frontier
    return seen

def is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True

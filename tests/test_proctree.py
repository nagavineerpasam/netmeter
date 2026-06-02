import os, subprocess, time
from netmeter.proctree import descendants, is_alive

def test_root_only_for_leaf_process():
    """A process with no children returns just {pid}."""
    # `cat` reading from a pipe stays alive with no children.
    p = subprocess.Popen(["cat"], stdin=subprocess.PIPE)
    try:
        time.sleep(0.1)
        ds = descendants(p.pid)
        assert ds == {p.pid}
    finally:
        p.stdin.close()
        p.wait(timeout=2)

def test_descendants_two_levels():
    """sh -c 'sleep 5 & sleep 5 & wait' has two child sleeps."""
    p = subprocess.Popen(["sh", "-c", "sleep 5 & sleep 5 & wait"])
    try:
        time.sleep(0.3)
        ds = descendants(p.pid)
        assert p.pid in ds
        assert len(ds) >= 3
    finally:
        p.terminate(); p.wait(timeout=2)

def test_is_alive_true_for_self():
    assert is_alive(os.getpid())

def test_is_alive_false_for_dead():
    p = subprocess.Popen(["true"]); p.wait()
    assert not is_alive(p.pid)

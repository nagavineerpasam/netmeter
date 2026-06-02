from pathlib import Path
from netmeter.parser import parse_samples, Sample, Row

FIXTURE = Path(__file__).parent / "fixtures" / "nettop_sample.txt"


def test_parses_real_fixture():
    text = FIXTURE.read_text()
    samples = list(parse_samples(text))
    assert samples, "no samples parsed from real nettop output"
    assert any(s.rows for s in samples), "no rows parsed in any sample"


def test_row_has_pid_and_deltas():
    text = FIXTURE.read_text()
    saw_any_row = False
    for sample in parse_samples(text):
        for row in sample.rows:
            saw_any_row = True
            assert isinstance(row.pid, int)
            assert row.pid > 0
            assert row.bytes_in >= 0
            assert row.bytes_out >= 0
    assert saw_any_row


def test_synthetic_sample():
    """Hand-crafted minimal input matching the ACTUAL nettop -P -d format observed.

    Real format (whitespace-delimited, fixed-width columns):
      Header: 'time' followed by spaces and 'bytes_in' ... 'bytes_out'
      Data:   '<HH:MM:SS.us> <procname>.<pid>  <value> <unit>  <value> <unit>'

    Units: B, KiB, MiB (GiB not observed but handled).
    Process names can contain spaces and dots; PID is always after the last dot.
    byte values are converted to integer bytes (KiB=1024, MiB=1024**2, etc.)
    """
    raw = (
        "time                                bytes_in       bytes_out\n"
        "00:00:01.000000 Google Chrome.501   1 KiB          2 KiB\n"
        "00:00:01.000001 node.12345          4 KiB          512 B\n"
        "time                                bytes_in       bytes_out\n"
        "00:00:02.000000 node.12345          0 B            256 B\n"
    )
    samples = list(parse_samples(raw))
    assert len(samples) == 2
    # find node.12345 in first sample
    first = next(r for r in samples[0].rows if r.pid == 12345)
    assert first.bytes_in == 4 * 1024
    assert first.bytes_out == 512
    # second sample
    second = next(r for r in samples[1].rows if r.pid == 12345)
    assert second.bytes_in == 0
    assert second.bytes_out == 256

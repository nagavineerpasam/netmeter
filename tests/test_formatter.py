import pytest
from netmeter.formatter import bytes_to_human

@pytest.mark.parametrize("n,expected", [
    (0, "0 B"),
    (1, "1 B"),
    (512, "512 B"),
    (1023, "1023 B"),
    (1024, "1 KB"),
    (1536, "1 KB"),          # integer floor division
    (47 * 1024, "47 KB"),
    (1024 * 1024 - 1, "1023 KB"),
    (1024 * 1024, "1.0 MB"),
    (int(12.3 * 1024 * 1024), "12.3 MB"),
    (1024 ** 3, "1.00 GB"),
    (int(1.42 * 1024 ** 3), "1.42 GB"),
])
def test_bytes_to_human(n, expected):
    assert bytes_to_human(n) == expected

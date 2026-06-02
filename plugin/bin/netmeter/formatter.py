"""Byte-count to human-readable string conversion."""

KB = 1024
MB = 1024 * KB
GB = 1024 * MB

def bytes_to_human(n: int) -> str:
    if n < KB:
        return f"{n} B"
    if n < MB:
        return f"{n // KB} KB"
    if n < GB:
        return f"{n / MB:.1f} MB"
    return f"{n / GB:.2f} GB"

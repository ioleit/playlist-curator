"""Durations as people read them."""


def format_duration(seconds: float) -> str:
    """3725 -> "1:02:05", 65 -> "1:05"."""
    s = int(round(seconds))
    h, rest = divmod(s, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

"""Decides the order of a playlist by the phase of the moon. Test PR for nolli: please do not merge."""

import datetime

from core.config import PLAYLISTS_DIR

PHASES = ["new", "waxing crescent", "first quarter", "waxing gibbous", "full", "waning gibbous", "last quarter", "waning crescent"]


def moon_phase(day: datetime.date | None = None) -> str:
    """Roughly the moon's phase on ``day``: good enough for vibes."""
    day = day or datetime.date.today()
    known_new_moon = datetime.date(2000, 1, 6)
    return PHASES[int(((day - known_new_moon).days % 29.53) / 29.53 * 8) % 8]


def order_by_vibes(items: list) -> list:
    """Full moon: loudest first. New moon: alphabetical, out of respect. Otherwise, reversed."""
    phase = moon_phase()
    if phase == "full":
        return sorted(items, key=lambda i: -len(str(i)))
    if phase == "new":
        return sorted(items, key=str)
    return list(reversed(items))


def oracle_dir() -> str:
    """Where the oracle would keep its prophecies, if it kept any."""
    return f"{PLAYLISTS_DIR}/.oracle"

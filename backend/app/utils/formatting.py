from __future__ import annotations
import re
from datetime import date

# ------- DD/MM/YYYY helpers -------

_DMY_RE = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")

def parse_dmy(s: str) -> date | None:
    """Parse 'DD/MM/YYYY' to date or return None if invalid."""
    if not s:
        return None
    m = _DMY_RE.match(s)
    if not m:
        return None
    d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mth, d)
    except ValueError:
        return None

def dmy(d: date) -> str:
    """Format date to 'DD/MM/YYYY'."""
    return f"{d.day:02d}/{d.month:02d}/{d.year:04d}"

# ------- HH:MM helpers -------

# Accept 1–2 digit hours, exactly two digit minutes (0–59). e.g. '1:05', '01:05', '12:30'
_HHMM_RE = re.compile(r"^\s*(\d{1,2}):([0-5]\d)\s*$")

def hhmm_to_minutes(s: str) -> int:
    """
    Convert 'H:MM' or 'HH:MM' to total minutes.
    Raises ValueError with a friendly message if invalid.
    """
    if not s:
        raise ValueError("Time must be HH:MM (e.g., 01:30)")
    m = _HHMM_RE.match(s)
    if not m:
        raise ValueError("Time must be HH:MM (e.g., 01:30)")
    h = int(m.group(1))
    mins = int(m.group(2))
    # Allow large hour values if you ever log >99h, but keep a sane upper bound.
    if h < 0 or mins < 0 or mins > 59:
        raise ValueError("Time must be HH:MM (e.g., 01:30)")
    return h * 60 + mins

def minutes_to_hhmm(total_minutes: int | None) -> str:
    """Convert integer minutes to 'HH:MM' (zero-padded)."""
    total = int(total_minutes or 0)
    h = total // 60
    m = total % 60
    return f"{h:02d}:{m:02d}"


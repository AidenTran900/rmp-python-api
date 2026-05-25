"""Private utilities shared across the scoring subpackage."""

import math
from datetime import datetime, timezone

from ..models import Rating


def _parse_date(date_str: str) -> datetime | None:
    """
    Parse an RMP timestamp string into an aware datetime.

    Handles the RMP format ``"2026-05-03 20:28:30 +0000 UTC"`` and falls
    back to :func:`datetime.fromisoformat` for other ISO variants.

    Args:
        date_str: Raw date string from a :class:`~models.Rating`.

    Returns:
        Timezone-aware :class:`datetime`, or ``None`` if unparseable.
    """
    if not date_str:
        return None
    try:
        cleaned = date_str.replace(" UTC", "").strip()
        return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return None


def _recency_weight(date_str: str, half_life_days: float = 365.0) -> float:
    """
    Exponential decay weight for a single rating based on its age.

    A rating exactly ``half_life_days`` old receives weight ``0.5``.
    Unparseable dates default to ``0.5``.

    Args:
        date_str: Raw date string from a :class:`~models.Rating`.
        half_life_days: Age (in days) at which weight halves.

    Returns:
        Weight in ``(0, 1]``.
    """
    dt = _parse_date(date_str)
    if dt is None:
        return 0.5
    days_old = max((datetime.now(timezone.utc) - dt).days, 0)
    return math.exp(-math.log(2) * days_old / half_life_days)


def _overall(r: Rating) -> float:
    """Per-rating quality score: mean of helpful and clarity (scale 1–5)."""
    return (r.helpful_rating + r.clarity_rating) / 2

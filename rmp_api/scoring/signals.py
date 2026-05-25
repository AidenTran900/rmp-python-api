"""Individual signal computers. Each takes a list of Rating objects and returns a normalized metric."""

import math
from collections import Counter
from datetime import datetime, timezone

from ..models import Rating
from .helpers import _overall, _parse_date, _recency_weight


def compute_recency_weighted_rating(
    ratings: list[Rating],
    half_life_days: float = 365.0,
) -> float:
    """
    Weighted mean of per-rating overall quality, decayed by age.

    More recent ratings contribute more to the result. Output stays on the 1–5 scale.

    Args:
        ratings: List of :class:`~models.Rating` objects.
        half_life_days: Exponential decay half-life in days.

    Returns:
        Recency-weighted mean in ``[1, 5]``, or ``0.0`` for empty input.
    """
    if not ratings:
        return 0.0
    weights = [_recency_weight(r.date, half_life_days) for r in ratings]
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(_overall(r) * w for r, w in zip(ratings, weights)) / total_w


def compute_reliability_score(num_ratings: int, target: int = 25) -> float:
    """
    Bayesian confidence score based on sample size.

    Uses a logistic curve centred at ``target`` ratings:
    ~0.5 at ``target``, approaches 1 asymptotically, never reaches 0.

    Args:
        num_ratings: Total number of ratings for the professor.
        target: Rating count at which confidence reaches ~0.5 (default ``25``).

    Returns:
        Confidence score in ``(0, 1)``.
    """
    return 1 / (1 + math.exp(-0.15 * (num_ratings - target)))


def compute_easiness_score(ratings: list[Rating]) -> float:
    """
    Inverse of average difficulty, normalised to ``[0, 1]``.

    ``difficulty = 1`` (easiest) -> ``1.0``; ``difficulty = 5`` -> ``0.0``.
    Ratings with ``None`` difficulty are excluded from both sides.

    Args:
        ratings: List of :class:`~models.Rating` objects.

    Returns:
        Easiness in ``[0, 1]``, or ``0.0`` if no difficulty data.
    """
    diffs = [r.difficulty_rating for r in ratings if r.difficulty_rating is not None]
    if not diffs:
        return 0.0
    return (5.0 - (sum(diffs) / len(diffs))) / 4.0


def compute_tag_frequencies(ratings: list[Rating]) -> list[tuple[str, int]]:
    """
    Aggregate and rank all rating tags across a professor's ratings.

    Tags stored as ``"--"``-delimited strings are split automatically;
    list-typed tags are used directly.

    Args:
        ratings: List of :class:`~models.Rating` objects.

    Returns:
        List of ``(tag, count)`` tuples sorted descending by frequency.
    """
    all_tags: list[str] = []
    for r in ratings:
        if not r.rating_tags:
            continue
        if isinstance(r.rating_tags, list):
            all_tags.extend(t.strip() for t in r.rating_tags if t.strip())
        else:
            all_tags.extend(t.strip() for t in r.rating_tags.split("--") if t.strip())
    return Counter(all_tags).most_common()


def compute_difficulty_histogram(ratings: list[Rating]) -> dict[int, int]:
    """
    Count ratings in each integer difficulty bucket from 1 to 5.

    Args:
        ratings: List of :class:`~models.Rating` objects.

    Returns:
        Dict mapping each bucket ``{1, 2, 3, 4, 5}`` to its count.
    """
    hist: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        if r.difficulty_rating is not None:
            bucket = int(round(r.difficulty_rating))
            if bucket in hist:
                hist[bucket] += 1
    return hist


def compute_review_velocity(ratings: list[Rating], window_years: float = 2.0) -> float:
    """
    Average number of reviews posted per year within a rolling window.

    Args:
        ratings: List of :class:`~models.Rating` objects.
        window_years: How many years back to look (default ``2.0``).

    Returns:
        Reviews per year as a float, or ``0.0`` for empty input.
    """
    if not ratings:
        return 0.0
    now = datetime.now(timezone.utc)
    cutoff_ts = now.timestamp() - (window_years * 365.25 * 86400)
    recent = sum(
        1 for r in ratings
        if (dt := _parse_date(r.date)) is not None and dt.timestamp() > cutoff_ts
    )
    return recent / window_years

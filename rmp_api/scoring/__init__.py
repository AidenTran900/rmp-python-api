"""
rmp_api.scoring — professor quality signals and composite scoring.
"""

from .presets import WEIGHT_PRESETS
from .score import compute_score, compute_split_score
from .signals import (
    compute_difficulty_histogram,
    compute_easiness_score,
    compute_recency_weighted_rating,
    compute_reliability_score,
    compute_review_velocity,
    compute_tag_frequencies,
)

__all__ = [
    "compute_score",
    "compute_split_score",
    "WEIGHT_PRESETS",
    "compute_recency_weighted_rating",
    "compute_reliability_score",
    "compute_easiness_score",
    "compute_tag_frequencies",
    "compute_difficulty_histogram",
    "compute_review_velocity",
]

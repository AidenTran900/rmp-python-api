"""
rmp_api

Python wrapper for the RateMyProfessors GraphQL API.
"""

from .client import (
    get_all_ratings,
    get_courses,
    get_professor_summary,
    get_ratings_page,
    get_representative_ratings,
    search_professors,
    search_schools,
)
from .models import ProfessorRating, ProfessorScore, Rating, SplitScore
from .scoring import WEIGHT_PRESETS, compute_score, compute_split_score

__all__ = [
    # Client
    "search_schools",
    "search_professors",
    "get_professor_summary",
    "get_ratings_page",
    "get_all_ratings",
    "get_representative_ratings",
    "get_courses",
    # Models
    "Rating",
    "ProfessorRating",
    # Scoring
    "compute_score",
    "compute_split_score",
    "ProfessorScore",
    "SplitScore",
    "WEIGHT_PRESETS",
]

"""Dataclasses and enums shared across the rmp_api package."""

from dataclasses import dataclass, field
from enum import StrEnum


class TimePeriod(StrEnum):
    """
    Time bucketing granularity for :func:`~scoring.compute_score_over_time`.

    Members compare equal to their string values, so plain strings still work:
    ``TimePeriod.YEAR == "year"`` is ``True``.

    Members:
        YEAR:     Annual buckets — ``"2023"``.
        SEMESTER: Half-year buckets — ``"2023-Spring"`` / ``"2023-Fall"``.
        QUARTER:  Quarterly buckets — ``"2023-Q1"`` … ``"2023-Q4"``.
    """

    YEAR     = "year"
    SEMESTER = "semester"
    QUARTER  = "quarter"


class SortBy(StrEnum):
    """
    :class:`~models.ProfessorScore` field to rank by in
    :func:`~scoring.compare_professors`.

    Members compare equal to their string values, so plain strings still work:
    ``SortBy.COMPOSITE_SCORE == "composite_score"`` is ``True``.

    Higher values are always ranked first. To rank by easiness (lower difficulty
    = better), use :attr:`EASINESS_SCORE` rather than :attr:`AVG_DIFFICULTY`.

    Members:
        COMPOSITE_SCORE:        Weighted composite (default).
        RAW_AVG_RATING:         Mean of ``(helpful + clarity) / 2``.
        AVG_CLARITY:            Mean clarity rating.
        AVG_HELPFULNESS:        Mean helpfulness rating.
        AVG_DIFFICULTY:         Mean difficulty (higher = harder).
        RECENCY_WEIGHTED_RATING: Exponential-decay-weighted quality.
        RELIABILITY_SCORE:      Bayesian confidence from sample size.
        EASINESS_SCORE:         Inverse of average difficulty (higher = easier).
        WOULD_TAKE_AGAIN_PCT:   Fraction who would take again.
        REVIEW_VELOCITY:        Reviews per year (2-year window).
        NUM_RATINGS:            Total rating count.
    """

    COMPOSITE_SCORE          = "composite_score"
    RAW_AVG_RATING           = "raw_avg_rating"
    AVG_CLARITY              = "avg_clarity"
    AVG_HELPFULNESS          = "avg_helpfulness"
    AVG_DIFFICULTY           = "avg_difficulty"
    RECENCY_WEIGHTED_RATING  = "recency_weighted_rating"
    RELIABILITY_SCORE        = "reliability_score"
    EASINESS_SCORE           = "easiness_score"
    WOULD_TAKE_AGAIN_PCT     = "would_take_again_pct"
    REVIEW_VELOCITY          = "review_velocity"
    NUM_RATINGS              = "num_ratings"


@dataclass
class ProfessorRating:
    """
    Aggregate stats for a professor from their RMP profile.

    Sentinel values (returned when no professor is found):
    ``avg_rating``, ``avg_difficulty``, and ``would_take_again_percent`` are
    set to ``-1``; ``num_ratings`` is ``0``; ``link`` is ``""``.

    Attributes:
        avg_rating: Mean overall rating (0.0–5.0).
        avg_difficulty: Mean difficulty rating (0.0–5.0).
        would_take_again_percent: Percentage of students who would take again (0.0–100.0).
            ``-1`` if not enough data.
        num_ratings: Total number of submitted ratings.
        formatted_name: Full name as ``"<firstName> <lastName>"``.
        department: Academic department string (e.g. ``"Computer Science"``).
        link: URL to the professor's RMP page.
    """

    avg_rating: float
    avg_difficulty: float
    would_take_again_percent: float
    num_ratings: int
    formatted_name: str
    department: str
    link: str

@dataclass
class Rating:
    """
    Single student rating for a professor.

    Attributes:
        id: Base64-encoded RMP node ID for this rating.
        legacy_id: Legacy numeric rating ID.
        comment: Student's written review text.
        date: Submission date string (ISO 8601, e.g. ``"2024-03-15 00:00:00 +0000 UTC"``).
        course: Course code the student reviewed for (e.g. ``"CS61A"``).
        helpful_rating: Helpfulness score (1.0–5.0).
        clarity_rating: Clarity score (1.0–5.0).
        difficulty_rating: Difficulty score (1.0–5.0).
        rating_tags: List of tag strings selected by the student (e.g. ``["Tough grader", "Clear grading"]``).
        flag_status: Moderation status (e.g. ``"FLAGGED"``, ``"UNFLAGGED"``).
        attendance_mandatory: Whether attendance was mandatory (``"mandatory"``, ``"non mandatory"``, or ``None``).
        would_take_again: ``1`` if yes, ``0`` if no, ``None`` if not answered.
        grade: Self-reported grade received (e.g. ``"A+"``, ``"B"``), or ``None``.
        textbook_use: Textbook usage score (0–5 scale), or ``None`` if not answered.
        is_for_online_class: ``True`` if the rating is for an online section.
        is_for_credit: ``True`` if the student took the course for credit.
        thumbs_up_total: Number of helpful votes on this rating.
        thumbs_down_total: Number of unhelpful votes on this rating.
        teacher_note: Professor's response comment, or ``None`` if no response.
    """

    id: str
    legacy_id: int
    comment: str
    date: str
    course: str
    helpful_rating: float
    clarity_rating: float
    difficulty_rating: float
    rating_tags: list[str]
    flag_status: str
    attendance_mandatory: str | None
    would_take_again: int | None
    grade: str | None
    textbook_use: int | None
    is_for_online_class: bool
    is_for_credit: bool
    thumbs_up_total: int
    thumbs_down_total: int
    teacher_note: str | None

@dataclass
class ProfessorScore:
    """
    All quality signals computed from a professor's :class:`Rating` list.

    Produced by :func:`~scoring.compute_score`. All scores are normalized
    unless noted otherwise.

    Attributes:
        num_ratings: Total number of ratings used to compute this score.

        raw_avg_rating: Simple mean of ``(helpful + clarity) / 2`` across all ratings (1–5).
        avg_clarity: Mean clarity rating (1–5).
        avg_helpfulness: Mean helpfulness rating (1–5).
        avg_difficulty: Mean difficulty rating (1–5). ``0.0`` if no difficulty data.

        recency_weighted_rating: Exponential-decay-weighted mean of overall quality (1–5).
            Older ratings contribute less; half-life configurable in ``compute_score``.
        reliability_score: Bayesian confidence based on sample size (0–1).
            ~0.5 at 25 ratings, approaches 1 asymptotically.
        easiness_score: Inverse of average difficulty, normalised to 0–1.
            ``1.0`` = easiest (avg difficulty 1), ``0.0`` = hardest (avg difficulty 5).
        would_take_again_pct: Fraction of students who would take the professor again (0–1).

        last_review_date: Date of the most recent rating as ``"YYYY-MM-DD"``, or ``None``.
        review_velocity: Reviews posted per year within a 2-year rolling window.

        top_tags: Up to 10 most common student-selected tags as ``(tag, count)`` pairs.
        difficulty_histogram: Count of ratings per difficulty bucket ``{1: n, 2: n, …, 5: n}``.

        composite_score: Weighted combination of signals, clamped to ``[0, 1]``.
            Weights determined by the preset or custom dict passed to ``compute_score``.
    """

    num_ratings: int

    # Raw aggregates
    raw_avg_rating: float
    avg_clarity: float
    avg_helpfulness: float
    avg_difficulty: float

    # Derived signals
    recency_weighted_rating: float
    reliability_score: float
    easiness_score: float
    would_take_again_pct: float

    # Activity
    last_review_date: str | None
    review_velocity: float

    # Tags & histogram
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    difficulty_histogram: dict[int, int] = field(default_factory=dict)

    # Composite
    composite_score: float = 0.0


@dataclass
class ProfessorComparison:
    """
    Side-by-side comparison of multiple professors ranked by a chosen signal.

    Produced by :func:`~scoring.compare_professors`.

    Attributes:
        ranking: List of ``(label, score)`` pairs sorted best → worst by ``sort_by``.
        scores: ``{label: ProfessorScore}`` mapping for direct lookup.
        sort_by: Name of the :class:`ProfessorScore` field used for ranking.
        best: Label of the top-ranked professor.
        worst: Label of the lowest-ranked professor.
        deltas: ``{label: float}`` showing each professor's ``sort_by`` value minus
            the best professor's value. Best professor has ``delta = 0.0``;
            all others are ``<= 0.0``.
    """

    ranking: list[tuple[str, "ProfessorScore"]]
    scores: dict[str, "ProfessorScore"]
    sort_by: str
    best: str
    worst: str
    deltas: dict[str, float]


@dataclass
class ScoreTimeline:
    """
    Professor scores bucketed over time with a linear trend.

    Produced by :func:`~scoring.compute_score_over_time`. Buckets are sorted
    oldest -> newest; each contains a full :class:`ProfessorScore` computed
    from only the ratings in that period.

    Attributes:
        periods: List of ``(label, score)`` pairs, oldest first.
            Label format depends on the ``period`` argument:
            ``"year"`` -> ``"2023"``;
            ``"semester"`` -> ``"2023-Spring"`` / ``"2023-Fall"``;
            ``"quarter"`` -> ``"2023-Q1"`` … ``"2023-Q4"``.
        trend: Linear-regression slope of ``composite_score`` across bucket
            indices. Positive = improving over time; negative = declining.
        total_span_years: Time span covered by all dated ratings in years.
    """

    periods: list[tuple[str, "ProfessorScore"]]
    trend: float
    total_span_years: float


@dataclass
class SplitScore:
    """
    Professor scores split by delivery format.

    Produced by :func:`~scoring.compute_split_score`. Each field is a full
    :class:`ProfessorScore` computed from the relevant subset of ratings.

    Attributes:
        online: Score from ratings where ``is_for_online_class`` is ``True``.
        in_person: Score from ratings where ``is_for_online_class`` is ``False``.
        combined: Score from all ratings regardless of format.
    """

    online: ProfessorScore
    in_person: ProfessorScore
    combined: ProfessorScore

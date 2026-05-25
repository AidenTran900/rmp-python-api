"""
models.py

shared dataclasses for the RMP API wrapper.
"""

from dataclasses import dataclass, field


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

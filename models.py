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

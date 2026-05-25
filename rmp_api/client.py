"""Functions for searching schools and professors, fetching ratings, and filtering reviews."""

from functools import lru_cache
from pathlib import Path

import requests

from .models import ProfessorRating, Rating


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_LINK = "https://www.ratemyprofessors.com/graphql"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/json",
    "Authorization": "Basic dGVzdDp0ZXN0", # Base64, "test:test"
    "Sec-GPC": "1",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=4",
}

_QUERIES_DIR = Path(__file__).parent / "queries"

TEACHER_QUERY = (_QUERIES_DIR / "teacher_search.graphql").read_text()
SCHOOL_QUERY = (_QUERIES_DIR / "school_search.graphql").read_text()
RATINGS_LIST_QUERY = (_QUERIES_DIR / "rating_list.graphql").read_text()
TEACHER_COURSES_QUERY = (_QUERIES_DIR / "teacher_courses.graphql").read_text()



# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _graphql(query: str, variables: dict) -> dict:
    """
    Execute a GraphQL request against the RMP API.

    Args:
        query: GraphQL query string.
        variables: Variables dict passed alongside the query.

    Returns:
        Parsed JSON response body.

    Raises:
        requests.HTTPError: On non-2xx response.
        requests.RequestException: On network failure.
    """
    response = requests.post(
        API_LINK,
        headers=HEADERS,
        json={"query": query, "variables": variables},
    )
    response.raise_for_status()
    return response.json()


def _parse_rating(edge: dict) -> Rating:
    """
    Map a single GraphQL rating edge to a :class:`~models.Rating`.

    Args:
        edge: A ``ratings.edges`` item from the GraphQL response.

    Returns:
        Populated :class:`~models.Rating` instance.
    """
    n = edge["node"]
    return Rating(
        id=n["id"],
        legacy_id=n["legacyId"],
        comment=n["comment"],
        date=n["date"],
        course=n["class"],
        helpful_rating=n["helpfulRating"],
        clarity_rating=n["clarityRating"],
        difficulty_rating=n["difficultyRating"],
        rating_tags=n["ratingTags"],
        flag_status=n["flagStatus"],
        attendance_mandatory=n["attendanceMandatory"],
        would_take_again=n["wouldTakeAgain"],
        grade=n["grade"],
        textbook_use=n["textbookUse"],
        is_for_online_class=n["isForOnlineClass"],
        is_for_credit=n["isForCredit"],
        thumbs_up_total=n["thumbsUpTotal"],
        thumbs_down_total=n["thumbsDownTotal"],
        teacher_note=n["teacherNote"]["comment"] if n["teacherNote"] else None,
    )



# ---------------------------------------------------------------------------
# API functions
# ---------------------------------------------------------------------------

@lru_cache(maxsize=128)
def search_schools(school_name: str) -> list[dict] | None:
    """
    Search for schools by name.

    Args:
        school_name: Full or partial school name to search.

    Returns:
        List of school edge dicts from the GraphQL response, each containing
        a ``node`` with school metadata (id, name, city, etc.).
        ``None`` on request or parsing failure.
    """
    try:
        data = _graphql(SCHOOL_QUERY, {"query": {"text": school_name}})
        return data["data"]["newSearch"]["schools"]["edges"]
    except Exception as e:
        print(f"Error searching school: {e}")
        return None


@lru_cache(maxsize=128)
def search_professors(
    professor_name: str,
    school_id: str,
) -> list[dict] | None:
    """
    Search for professors by name within a school.

    Args:
        professor_name: Full or partial professor name to search.
        school_id: Base64-encoded RMP school node ID (e.g. ``"U2Nob29sLTEyMw=="``)
            or legacy numeric string accepted by the GraphQL API.

    Returns:
        List of teacher edge dicts from the GraphQL response, each containing
        a ``node`` with professor metadata (id, name, avgRating, etc.).
        ``None`` on request or parsing failure.
    """
    try:
        data = _graphql(
            TEACHER_QUERY,
            {
                "query": {
                    "text": professor_name,
                    "schoolID": school_id,
                    "fallback": True,
                    "departmentID": None,
                },
                "schoolID": school_id,
                "includeSchoolFilter": True,
            },
        )
        return data["data"]["search"]["teachers"]["edges"]
    except Exception as e:
        print(f"Error searching professors: {e}")
        return None


def get_professor_summary(
    professor_name: str,
    school_id: str,
) -> ProfessorRating:
    """
    Fetch aggregate summary for the top search result matching a professor.

    Wraps :func:`search_professors` and extracts the first result's stats.
    When no match is found, returns a sentinel ``ProfessorRating`` with all
    numeric fields set to ``-1`` and ``num_ratings`` set to ``0``.

    Args:
        professor_name: Full or partial professor name.
        school_id: Base64-encoded RMP school node ID.

    Returns:
        ``ProfessorRating`` with fields:
        ``avg_rating``, ``avg_difficulty``, ``would_take_again_percent``,
        ``num_ratings``, ``formatted_name``, ``department``, ``link``.
    """
    results = search_professors(professor_name, school_id)

    if not results:
        return ProfessorRating(
            avg_rating=-1,
            avg_difficulty=-1,
            would_take_again_percent=-1,
            num_ratings=0,
            formatted_name=professor_name,
            department="",
            link="",
        )

    node = results[0]["node"]
    return ProfessorRating(
        avg_rating=node["avgRating"],
        avg_difficulty=node["avgDifficulty"],
        would_take_again_percent=node["wouldTakeAgainPercent"],
        num_ratings=node["numRatings"],
        formatted_name=f"{node['firstName']} {node['lastName']}",
        department=node["department"],
        link=f"https://www.ratemyprofessors.com/professor/{node['legacyId']}",
    )


def get_ratings_page(
    professor_id: str,
    count: int = 20,
    course_filter: str | None = None,
    cursor: str | None = None,
) -> tuple[list[Rating], bool, str | None]:
    """
    Fetch one page of ratings for a professor.

    Args:
        professor_id: Base64-encoded RMP professor node ID.
        count: Max ratings to return per page (default ``20``).
        course_filter: Optional course code string to filter ratings (e.g. ``"CS61A"``).
        cursor: Opaque pagination cursor from a previous call's ``end_cursor``.
            ``None`` fetches the first page.

    Returns:
        3-tuple ``(ratings, has_next_page, end_cursor)`` where:
        ``ratings`` is a list of :class:`~models.Rating` objects,
        ``has_next_page`` signals more pages exist,
        and ``end_cursor`` is passed as ``cursor`` in the next call (``None`` on last page).
        Returns ``([], False, None)`` on failure.
    """
    try:
        data = _graphql(
            RATINGS_LIST_QUERY,
            {
                "id": professor_id,
                "count": count,
                "courseFilter": course_filter,
                "cursor": cursor,
            },
        )
        ratings_data = data["data"]["node"]["ratings"]
        page_info = ratings_data["pageInfo"]
        ratings = [_parse_rating(edge) for edge in ratings_data["edges"]]
        return ratings, page_info["hasNextPage"], page_info["endCursor"]
    except Exception as e:
        print(f"Error fetching ratings: {e}")
        return [], False, None


@lru_cache(maxsize=256)
def _fetch_all_ratings_cached(
    professor_id: str,
    course_filter: str | None,
    page_size: int,
) -> list[Rating]:
    """
    Cached inner fetch for a single course (or all courses when ``None``).

    Not part of the public API — call :func:`get_all_ratings` instead.
    """
    all_ratings = []
    cursor = None

    while True:
        ratings, has_next_page, cursor = get_ratings_page(
            professor_id,
            count=page_size,
            course_filter=course_filter,
            cursor=cursor,
        )
        all_ratings.extend(ratings)

        if not has_next_page:
            break

    return all_ratings


def get_all_ratings(
    professor_id: str,
    course_filter: str | list[str] | None = None,
    page_size: int = 20,
) -> list[Rating]:
    """
    Fetch all ratings for a professor, auto-paginating until exhausted.

    Results are cached per ``(professor_id, course_filter, page_size)`` for
    the lifetime of the process. Call :func:`get_all_ratings.cache_clear` (via
    ``_fetch_all_ratings_cached.cache_clear()``) to invalidate manually.

    Args:
        professor_id: Base64-encoded RMP professor node ID.
        course_filter: Optional course code(s) to filter ratings. Accepts a
            single string (e.g. ``"CS61A"``), a list of strings
            (e.g. ``["CS61A", "CS61B"]``), or ``None`` for all ratings.
            When a list is given, one paginated request sequence is made per
            course and results are concatenated in the same order.
        page_size: Ratings fetched per page (default ``20``).

    Returns:
        Combined list of :class:`~models.Rating` objects across all pages.
        Empty list if the first page fails.
    """
    if isinstance(course_filter, list):
        all_ratings = []
        for course in course_filter:
            all_ratings.extend(_fetch_all_ratings_cached(professor_id, course, page_size))
        return all_ratings

    return list(_fetch_all_ratings_cached(professor_id, course_filter, page_size))


@lru_cache(maxsize=128)
def get_courses(professor_id: str) -> list[dict] | None:
    """
    Fetch all courses a professor has taught, as listed in the RMP review filter.

    Args:
        professor_id: Base64-encoded RMP professor node ID.

    Returns:
        List of dicts with keys ``courseName`` (str) and ``courseCount`` (int),
        sorted by ``courseCount`` descending.
        ``None`` on request or parsing failure.
    """
    try:
        data = _graphql(TEACHER_COURSES_QUERY, {"id": professor_id})
        codes = data["data"]["node"]["courseCodes"]
        return sorted(codes, key=lambda c: c["courseCount"], reverse=True)
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return None


def filter_ratings_by_keywords(
    ratings: list[Rating],
    keywords: str | list[str],
    match_all: bool = False,
    case_sensitive: bool = False,
) -> list[Rating]:
    """
    Filter ratings whose comment contains one or more keywords.

    Args:
        ratings: List of :class:`~models.Rating` objects to filter.
        keywords: Keyword string or list of keyword strings to search for.
            Each keyword is matched as a substring of the comment.
        match_all: When ``True``, a rating must contain **all** keywords
            (AND logic). When ``False`` (default), any single keyword match
            is sufficient (OR logic).
        case_sensitive: When ``True``, matching is case-sensitive.
            Default ``False`` (case-insensitive).

    Returns:
        List of :class:`~models.Rating` objects whose ``comment`` field
        satisfies the keyword filter. Preserves original order.
        Ratings with an empty or ``None`` comment are always excluded.
    """
    if isinstance(keywords, str):
        keywords = [keywords]

    if not keywords:
        return list(ratings)

    if not case_sensitive:
        keywords = [kw.lower() for kw in keywords]

    def _matches(rating: Rating) -> bool:
        comment = rating.comment
        if not comment:
            return False
        text = comment if case_sensitive else comment.lower()
        if match_all:
            return all(kw in text for kw in keywords)
        return any(kw in text for kw in keywords)

    return [r for r in ratings if _matches(r)]


def get_representative_ratings(
    professor_id: str,
    n: int = 12,
    course_filter: str | list[str] | None = None,
) -> list[Rating]:
    """
    Return ``n`` ratings evenly sampled across all available ratings.

    Ratings are ordered newest -> oldest by the API. Sampling is uniform by
    index (stride = total // n), so the result spans the full temporal range.
    If the professor has ``<= n`` ratings, all are returned as-is.

    Args:
        professor_id: Base64-encoded RMP professor node ID.
        n: Number of representative ratings to return (default ``12``).
        course_filter: Optional course code(s) to restrict ratings. Accepts a
            single string or list of strings (e.g. ``["CS61A", "CS61B"``).

    Returns:
        List of up to ``n`` :class:`~models.Rating` objects.
    """
    all_ratings = get_all_ratings(professor_id, course_filter=course_filter)
    if len(all_ratings) <= n:
        return all_ratings
    step = len(all_ratings) // n
    return all_ratings[::step][:n]

"""Shared fixtures, factories, and mock payloads for the test suite."""

from unittest.mock import MagicMock

import pytest

from rmp_api.client import _fetch_all_ratings_cached, get_courses, search_professors, search_schools
from rmp_api.models import Rating


# ---------------------------------------------------------------------------
# Rating factory
# ---------------------------------------------------------------------------

def make_rating(
    *,
    id="UmF0aW5nLTEyMzQ=",
    legacy_id=1234,
    comment="Great professor, clear lectures",
    date="2024-01-15 00:00:00 +0000 UTC",
    course="CS101",
    helpful_rating=4.0,
    clarity_rating=4.0,
    difficulty_rating=3.0,
    rating_tags=None,
    flag_status="UNFLAGGED",
    attendance_mandatory="non mandatory",
    would_take_again=1,
    grade="A",
    textbook_use=0,
    is_for_online_class=False,
    is_for_credit=True,
    thumbs_up_total=5,
    thumbs_down_total=0,
    teacher_note=None,
) -> Rating:
    """Build a Rating with sensible defaults. Override any field via keyword args."""
    return Rating(
        id=id,
        legacy_id=legacy_id,
        comment=comment,
        date=date,
        course=course,
        helpful_rating=helpful_rating,
        clarity_rating=clarity_rating,
        difficulty_rating=difficulty_rating,
        rating_tags=rating_tags if rating_tags is not None else [],
        flag_status=flag_status,
        attendance_mandatory=attendance_mandatory,
        would_take_again=would_take_again,
        grade=grade,
        textbook_use=textbook_use,
        is_for_online_class=is_for_online_class,
        is_for_credit=is_for_credit,
        thumbs_up_total=thumbs_up_total,
        thumbs_down_total=thumbs_down_total,
        teacher_note=teacher_note,
    )


# ---------------------------------------------------------------------------
# Mock HTTP response
# ---------------------------------------------------------------------------

def mock_response(payload: dict) -> MagicMock:
    """Return a mock requests.Response that yields payload from .json()."""
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


# ---------------------------------------------------------------------------
# GraphQL payload constants
# ---------------------------------------------------------------------------

SCHOOL_PAYLOAD = {
    "data": {
        "newSearch": {
            "schools": {
                "edges": [
                    {
                        "cursor": "cursor_school_0",
                        "node": {
                            "id": "U2Nob29sLTEyMw==",
                            "legacyId": 123,
                            "name": "University of California, Berkeley",
                            "city": "Berkeley",
                            "state": "CA",
                            "numRatings": 5000,
                            "avgRatingRounded": 3.9,
                        },
                    },
                    {
                        "cursor": "cursor_school_1",
                        "node": {
                            "id": "U2Nob29sLTQ1Ng==",
                            "legacyId": 456,
                            "name": "UC Berkeley Extension",
                            "city": "Berkeley",
                            "state": "CA",
                            "numRatings": 200,
                            "avgRatingRounded": 3.5,
                        },
                    },
                ]
            }
        }
    }
}

EMPTY_SCHOOL_PAYLOAD = {
    "data": {"newSearch": {"schools": {"edges": []}}}
}

PROFESSOR_PAYLOAD = {
    "data": {
        "search": {
            "teachers": {
                "edges": [
                    {
                        "cursor": "cursor_prof_0",
                        "node": {
                            "id": "VGVhY2hlci0xMjM0NTY=",
                            "legacyId": 123456,
                            "firstName": "John",
                            "lastName": "DeNero",
                            "department": "Computer Science",
                            "avgRating": 4.2,
                            "avgDifficulty": 2.8,
                            "numRatings": 215,
                            "wouldTakeAgainPercent": 92.0,
                            "isSaved": False,
                            "school": {
                                "id": "U2Nob29sLTEyMw==",
                                "name": "University of California, Berkeley",
                            },
                            "__typename": "Teacher",
                        },
                    }
                ]
            }
        }
    }
}

EMPTY_PROFESSOR_PAYLOAD = {
    "data": {"search": {"teachers": {"edges": []}}}
}

# A single GraphQL rating node matching the rating_list.graphql schema.
RATING_NODE = {
    "id": "UmF0aW5nLTEyMzQ=",
    "legacyId": 1234,
    "comment": "Great professor, clear lectures",
    "date": "2024-01-15 00:00:00 +0000 UTC",
    "class": "CS61A",
    "helpfulRating": 4.0,
    "clarityRating": 4.0,
    "difficultyRating": 3.0,
    "ratingTags": ["Respected", "Clear grading"],
    "flagStatus": "UNFLAGGED",
    "createdByUser": False,
    "attendanceMandatory": "non mandatory",
    "wouldTakeAgain": 1,
    "grade": "A",
    "textbookUse": 0,
    "isForOnlineClass": False,
    "isForCredit": True,
    "thumbsUpTotal": 5,
    "thumbsDownTotal": 0,
    "teacherNote": None,
}

RATING_NODE_2 = {
    **RATING_NODE,
    "id": "UmF0aW5nLTU2Nzg=",
    "legacyId": 5678,
    "comment": "Tough but fair",
    "date": "2023-09-01 00:00:00 +0000 UTC",
    "class": "CS61B",
    "helpfulRating": 3.0,
    "clarityRating": 3.0,
    "wouldTakeAgain": 0,
    "isForOnlineClass": True,
}

COURSES_PAYLOAD = {
    "data": {
        "node": {
            "id": "VGVhY2hlci0xMjM0NTY=",
            "courseCodes": [
                {"courseName": "CS61B", "courseCount": 150},
                {"courseName": "CS61A", "courseCount": 65},
                {"courseName": "CS61C", "courseCount": 30},
            ],
        }
    }
}


def make_ratings_page_payload(
    nodes: list[dict],
    has_next: bool = False,
    end_cursor: str | None = None,
) -> dict:
    """Build a ratings page GraphQL response from a list of rating node dicts."""
    return {
        "data": {
            "node": {
                "id": "VGVhY2hlci0xMjM0NTY=",
                "__typename": "Teacher",
                "ratings": {
                    "edges": [
                        {"cursor": f"c{i}", "node": node}
                        for i, node in enumerate(nodes)
                    ],
                    "pageInfo": {
                        "hasNextPage": has_next,
                        "endCursor": end_cursor,
                    },
                },
            }
        }
    }


# ---------------------------------------------------------------------------
# Cache-clearing fixture (autouse -- runs before every test)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_lru_caches():
    """Prevent LRU cache from leaking state between tests."""
    search_schools.cache_clear()
    search_professors.cache_clear()
    get_courses.cache_clear()
    _fetch_all_ratings_cached.cache_clear()
    yield
    search_schools.cache_clear()
    search_professors.cache_clear()
    get_courses.cache_clear()
    _fetch_all_ratings_cached.cache_clear()

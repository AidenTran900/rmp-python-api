"""Tests for rmp_api.client -- all network calls are mocked via requests.post."""

from unittest.mock import patch

import pytest

from rmp_api import (
    ProfessorResult,
    SchoolResult,
    filter_ratings_by_keywords,
    get_all_ratings,
    get_courses,
    get_professor_summary,
    get_ratings_page,
    get_representative_ratings,
    search_professors,
    search_schools,
)

from .conftest import (
    COURSES_PAYLOAD,
    EMPTY_PROFESSOR_PAYLOAD,
    EMPTY_SCHOOL_PAYLOAD,
    PROFESSOR_PAYLOAD,
    RATING_NODE,
    RATING_NODE_2,
    SCHOOL_PAYLOAD,
    make_rating,
    make_ratings_page_payload,
    mock_response,
)

PROFESSOR_ID = "VGVhY2hlci0xMjM0NTY="
SCHOOL_ID = "U2Nob29sLTEyMw=="


# ---------------------------------------------------------------------------
# search_schools
# ---------------------------------------------------------------------------

class TestSearchSchools:
    def test_returns_list_of_school_results(self):
        with patch("requests.post", return_value=mock_response(SCHOOL_PAYLOAD)):
            results = search_schools("UC Berkeley")

        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, SchoolResult) for r in results)

    def test_correct_fields_on_first_result(self):
        with patch("requests.post", return_value=mock_response(SCHOOL_PAYLOAD)):
            results = search_schools("UC Berkeley")

        school = results[0]
        assert school.id == "U2Nob29sLTEyMw=="
        assert school.legacy_id == 123
        assert school.name == "University of California, Berkeley"
        assert school.city == "Berkeley"
        assert school.state == "CA"
        assert school.num_ratings == 5000
        assert school.avg_rating == 3.9

    def test_returns_none_on_network_error(self):
        with patch("requests.post", side_effect=Exception("connection refused")):
            result = search_schools("UC Berkeley")

        assert result is None

    def test_empty_results_returns_empty_list(self):
        with patch("requests.post", return_value=mock_response(EMPTY_SCHOOL_PAYLOAD)):
            results = search_schools("Nonexistent University")

        assert results == []


# ---------------------------------------------------------------------------
# search_professors
# ---------------------------------------------------------------------------

class TestSearchProfessors:
    def test_returns_list_of_professor_results(self):
        with patch("requests.post", return_value=mock_response(PROFESSOR_PAYLOAD)):
            results = search_professors("John DeNero", SCHOOL_ID)

        assert isinstance(results, list)
        assert len(results) == 1
        assert all(isinstance(r, ProfessorResult) for r in results)

    def test_correct_fields_on_first_result(self):
        with patch("requests.post", return_value=mock_response(PROFESSOR_PAYLOAD)):
            results = search_professors("John DeNero", SCHOOL_ID)

        prof = results[0]
        assert prof.id == "VGVhY2hlci0xMjM0NTY="
        assert prof.legacy_id == 123456
        assert prof.first_name == "John"
        assert prof.last_name == "DeNero"
        assert prof.department == "Computer Science"
        assert prof.school_name == "University of California, Berkeley"
        assert prof.avg_rating == 4.2
        assert prof.avg_difficulty == 2.8
        assert prof.num_ratings == 215
        assert prof.would_take_again_percent == 92.0

    def test_returns_none_on_network_error(self):
        with patch("requests.post", side_effect=Exception("timeout")):
            result = search_professors("John DeNero", SCHOOL_ID)

        assert result is None

    def test_empty_results_returns_empty_list(self):
        with patch("requests.post", return_value=mock_response(EMPTY_PROFESSOR_PAYLOAD)):
            results = search_professors("Nobody Here", SCHOOL_ID)

        assert results == []


# ---------------------------------------------------------------------------
# get_professor_summary
# ---------------------------------------------------------------------------

class TestGetProfessorSummary:
    def test_returns_correct_fields(self):
        with patch("requests.post", return_value=mock_response(PROFESSOR_PAYLOAD)):
            summary = get_professor_summary("John DeNero", SCHOOL_ID)

        assert summary.avg_rating == 4.2
        assert summary.avg_difficulty == 2.8
        assert summary.would_take_again_percent == 92.0
        assert summary.num_ratings == 215
        assert summary.formatted_name == "John DeNero"
        assert summary.department == "Computer Science"
        assert summary.link == "https://www.ratemyprofessors.com/professor/123456"

    def test_sentinel_when_no_results(self):
        with patch("requests.post", return_value=mock_response(EMPTY_PROFESSOR_PAYLOAD)):
            summary = get_professor_summary("Nobody", SCHOOL_ID)

        assert summary.num_ratings == 0
        assert summary.avg_rating == -1
        assert summary.avg_difficulty == -1
        assert summary.would_take_again_percent == -1
        assert summary.link == ""

    def test_sentinel_when_search_returns_none(self):
        with patch("requests.post", side_effect=Exception("network error")):
            summary = get_professor_summary("Nobody", SCHOOL_ID)

        assert summary.num_ratings == 0
        assert summary.avg_rating == -1

    def test_formatted_name_combines_first_and_last(self):
        with patch("requests.post", return_value=mock_response(PROFESSOR_PAYLOAD)):
            summary = get_professor_summary("John DeNero", SCHOOL_ID)

        assert summary.formatted_name == "John DeNero"


# ---------------------------------------------------------------------------
# get_ratings_page
# ---------------------------------------------------------------------------

class TestGetRatingsPage:
    def test_returns_ratings_and_page_info(self):
        payload = make_ratings_page_payload([RATING_NODE], has_next=False, end_cursor=None)
        with patch("requests.post", return_value=mock_response(payload)):
            ratings, has_next, cursor = get_ratings_page(PROFESSOR_ID)

        assert len(ratings) == 1
        assert has_next is False
        assert cursor is None

    def test_correct_rating_fields(self):
        payload = make_ratings_page_payload([RATING_NODE])
        with patch("requests.post", return_value=mock_response(payload)):
            ratings, _, _ = get_ratings_page(PROFESSOR_ID)

        r = ratings[0]
        assert r.id == "UmF0aW5nLTEyMzQ="
        assert r.legacy_id == 1234
        assert r.comment == "Great professor, clear lectures"
        assert r.course == "CS61A"
        assert r.helpful_rating == 4.0
        assert r.clarity_rating == 4.0
        assert r.difficulty_rating == 3.0
        assert r.rating_tags == ["Respected", "Clear grading"]
        assert r.would_take_again == 1
        assert r.is_for_online_class is False
        assert r.is_for_credit is True
        assert r.teacher_note is None

    def test_pagination_cursor_forwarded(self):
        payload = make_ratings_page_payload([RATING_NODE], has_next=True, end_cursor="next_cursor")
        with patch("requests.post", return_value=mock_response(payload)):
            ratings, has_next, cursor = get_ratings_page(PROFESSOR_ID)

        assert has_next is True
        assert cursor == "next_cursor"

    def test_returns_empty_on_network_error(self):
        with patch("requests.post", side_effect=Exception("error")):
            ratings, has_next, cursor = get_ratings_page(PROFESSOR_ID)

        assert ratings == []
        assert has_next is False
        assert cursor is None

    def test_teacher_note_parsed_when_present(self):
        node_with_note = {
            **RATING_NODE,
            "teacherNote": {"id": "note1", "teacherId": "t1", "comment": "Thanks for the feedback"},
        }
        payload = make_ratings_page_payload([node_with_note])
        with patch("requests.post", return_value=mock_response(payload)):
            ratings, _, _ = get_ratings_page(PROFESSOR_ID)

        assert ratings[0].teacher_note == "Thanks for the feedback"


# ---------------------------------------------------------------------------
# get_all_ratings
# ---------------------------------------------------------------------------

class TestGetAllRatings:
    def test_single_page_returns_all_ratings(self):
        payload = make_ratings_page_payload([RATING_NODE], has_next=False)
        with patch("requests.post", return_value=mock_response(payload)):
            ratings = get_all_ratings(PROFESSOR_ID)

        assert len(ratings) == 1

    def test_auto_paginates_across_multiple_pages(self):
        page1 = make_ratings_page_payload([RATING_NODE], has_next=True, end_cursor="c1")
        page2 = make_ratings_page_payload([RATING_NODE_2], has_next=False)
        with patch("requests.post", side_effect=[mock_response(page1), mock_response(page2)]):
            ratings = get_all_ratings(PROFESSOR_ID)

        assert len(ratings) == 2
        assert ratings[0].legacy_id == 1234
        assert ratings[1].legacy_id == 5678

    def test_list_course_filter_fetches_each_course(self):
        payload = make_ratings_page_payload([RATING_NODE], has_next=False)
        with patch("requests.post", return_value=mock_response(payload)) as mock_post:
            ratings = get_all_ratings(PROFESSOR_ID, course_filter=["CS61A", "CS61B"])

        # One paginated request sequence per course
        assert mock_post.call_count == 2
        assert len(ratings) == 2

    def test_string_course_filter_passed_through(self):
        payload = make_ratings_page_payload([RATING_NODE], has_next=False)
        with patch("requests.post", return_value=mock_response(payload)) as mock_post:
            ratings = get_all_ratings(PROFESSOR_ID, course_filter="CS61A")

        call_variables = mock_post.call_args.kwargs["json"]["variables"]
        assert call_variables["courseFilter"] == "CS61A"

    def test_returns_empty_list_on_first_page_failure(self):
        with patch("requests.post", side_effect=Exception("error")):
            ratings = get_all_ratings(PROFESSOR_ID)

        assert ratings == []


# ---------------------------------------------------------------------------
# get_courses
# ---------------------------------------------------------------------------

class TestGetCourses:
    def test_returns_sorted_by_count_descending(self):
        with patch("requests.post", return_value=mock_response(COURSES_PAYLOAD)):
            courses = get_courses(PROFESSOR_ID)

        assert courses[0]["courseName"] == "CS61B"
        assert courses[0]["courseCount"] == 150
        assert courses[1]["courseName"] == "CS61A"
        assert courses[1]["courseCount"] == 65

    def test_returns_none_on_network_error(self):
        with patch("requests.post", side_effect=Exception("error")):
            result = get_courses(PROFESSOR_ID)

        assert result is None

    def test_all_courses_present(self):
        with patch("requests.post", return_value=mock_response(COURSES_PAYLOAD)):
            courses = get_courses(PROFESSOR_ID)

        assert len(courses) == 3
        names = [c["courseName"] for c in courses]
        assert "CS61A" in names
        assert "CS61B" in names
        assert "CS61C" in names


# ---------------------------------------------------------------------------
# filter_ratings_by_keywords
# ---------------------------------------------------------------------------

class TestFilterRatingsByKeywords:
    def test_or_logic_returns_any_match(self):
        ratings = [
            make_rating(comment="great professor"),
            make_rating(comment="hard exams"),
            make_rating(comment="boring lectures"),
        ]
        result = filter_ratings_by_keywords(ratings, ["great", "hard"])
        assert len(result) == 2

    def test_and_logic_requires_all_keywords(self):
        ratings = [
            make_rating(comment="great and hard"),
            make_rating(comment="great professor"),
            make_rating(comment="hard exams"),
        ]
        result = filter_ratings_by_keywords(ratings, ["great", "hard"], match_all=True)
        assert len(result) == 1
        assert result[0].comment == "great and hard"

    def test_case_insensitive_by_default(self):
        ratings = [make_rating(comment="GREAT professor")]
        result = filter_ratings_by_keywords(ratings, ["great"])
        assert len(result) == 1

    def test_case_sensitive_mode(self):
        ratings = [
            make_rating(comment="GREAT professor"),
            make_rating(comment="great professor"),
        ]
        result = filter_ratings_by_keywords(ratings, ["great"], case_sensitive=True)
        assert len(result) == 1
        assert result[0].comment == "great professor"

    def test_empty_keywords_returns_all(self):
        ratings = [make_rating(), make_rating(), make_rating()]
        result = filter_ratings_by_keywords(ratings, [])
        assert len(result) == 3

    def test_excludes_none_comments(self):
        ratings = [
            make_rating(comment=None),
            make_rating(comment="great professor"),
        ]
        result = filter_ratings_by_keywords(ratings, ["great"])
        assert len(result) == 1

    def test_excludes_empty_string_comments(self):
        ratings = [
            make_rating(comment=""),
            make_rating(comment="great professor"),
        ]
        result = filter_ratings_by_keywords(ratings, ["great"])
        assert len(result) == 1

    def test_single_keyword_as_string(self):
        ratings = [make_rating(comment="great professor")]
        result = filter_ratings_by_keywords(ratings, "great")
        assert len(result) == 1

    def test_no_match_returns_empty(self):
        ratings = [make_rating(comment="mediocre professor")]
        result = filter_ratings_by_keywords(ratings, ["excellent"])
        assert result == []

    def test_preserves_order(self):
        ratings = [
            make_rating(comment="first great"),
            make_rating(comment="boring"),
            make_rating(comment="second great"),
        ]
        result = filter_ratings_by_keywords(ratings, ["great"])
        assert result[0].comment == "first great"
        assert result[1].comment == "second great"


# ---------------------------------------------------------------------------
# get_representative_ratings
# ---------------------------------------------------------------------------

class TestGetRepresentativeRatings:
    def test_returns_all_when_fewer_than_n(self):
        payload = make_ratings_page_payload([RATING_NODE, RATING_NODE_2], has_next=False)
        with patch("requests.post", return_value=mock_response(payload)):
            sample = get_representative_ratings(PROFESSOR_ID, n=10)

        assert len(sample) == 2

    def test_returns_exactly_n_when_more_exist(self):
        # Build 20 distinct rating nodes
        nodes = [{**RATING_NODE, "legacyId": i, "id": f"id{i}"} for i in range(20)]
        payload = make_ratings_page_payload(nodes, has_next=False)
        with patch("requests.post", return_value=mock_response(payload)):
            sample = get_representative_ratings(PROFESSOR_ID, n=5)

        assert len(sample) == 5

    def test_sample_spans_full_range(self):
        # 20 ratings; sampling 4 should give indices 0, 5, 10, 15 (stride=5)
        nodes = [{**RATING_NODE, "legacyId": i, "id": f"id{i}"} for i in range(20)]
        payload = make_ratings_page_payload(nodes, has_next=False)
        with patch("requests.post", return_value=mock_response(payload)):
            sample = get_representative_ratings(PROFESSOR_ID, n=4)

        ids = [r.legacy_id for r in sample]
        assert ids[0] < ids[-1], "sample should span the full range"

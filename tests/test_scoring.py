"""Tests for scoring functions and individual signal computers."""

import pytest

from rmp_api import (
    SortBy,
    TimePeriod,
    WEIGHT_PRESETS,
    compare_professors,
    compute_score,
    compute_score_over_time,
    compute_split_score,
)
from rmp_api.scoring.signals import (
    compute_difficulty_histogram,
    compute_easiness_score,
    compute_recency_weighted_rating,
    compute_reliability_score,
    compute_review_velocity,
    compute_tag_frequencies,
)

from .conftest import make_rating


# ---------------------------------------------------------------------------
# compute_score
# ---------------------------------------------------------------------------

class TestComputeScore:
    def test_empty_ratings_returns_zero_sentinel(self):
        score = compute_score([])
        assert score.num_ratings == 0
        assert score.composite_score == 0.0
        assert score.raw_avg_rating == 0.0

    def test_num_ratings_matches_input(self):
        ratings = [make_rating() for _ in range(10)]
        score = compute_score(ratings)
        assert score.num_ratings == 10

    def test_raw_avg_rating_is_mean_of_helpful_and_clarity(self):
        ratings = [
            make_rating(helpful_rating=4.0, clarity_rating=2.0),  # overall=3.0
            make_rating(helpful_rating=2.0, clarity_rating=4.0),  # overall=3.0
        ]
        score = compute_score(ratings)
        assert score.raw_avg_rating == pytest.approx(3.0)

    def test_avg_clarity_computed(self):
        ratings = [
            make_rating(clarity_rating=2.0),
            make_rating(clarity_rating=4.0),
        ]
        score = compute_score(ratings)
        assert score.avg_clarity == pytest.approx(3.0)

    def test_avg_helpfulness_computed(self):
        ratings = [
            make_rating(helpful_rating=1.0),
            make_rating(helpful_rating=5.0),
        ]
        score = compute_score(ratings)
        assert score.avg_helpfulness == pytest.approx(3.0)

    def test_avg_difficulty_computed(self):
        ratings = [
            make_rating(difficulty_rating=2.0),
            make_rating(difficulty_rating=4.0),
        ]
        score = compute_score(ratings)
        assert score.avg_difficulty == pytest.approx(3.0)

    def test_avg_difficulty_excludes_none(self):
        ratings = [
            make_rating(difficulty_rating=3.0),
            make_rating(difficulty_rating=None),
        ]
        score = compute_score(ratings)
        assert score.avg_difficulty == pytest.approx(3.0)

    def test_would_take_again_pct_computed(self):
        ratings = [
            make_rating(would_take_again=1),
            make_rating(would_take_again=1),
            make_rating(would_take_again=0),
            make_rating(would_take_again=None),  # excluded from calculation
        ]
        score = compute_score(ratings)
        assert score.would_take_again_pct == pytest.approx(2 / 3)

    def test_would_take_again_pct_zero_when_no_responses(self):
        ratings = [make_rating(would_take_again=None) for _ in range(5)]
        score = compute_score(ratings)
        assert score.would_take_again_pct == 0.0

    def test_composite_score_clamped_to_0_1(self):
        ratings = [make_rating() for _ in range(5)]
        score = compute_score(ratings)
        assert 0.0 <= score.composite_score <= 1.0

    def test_composite_score_with_extreme_weights(self):
        # weights that would sum > 1 -- composite still clamped
        ratings = [make_rating(helpful_rating=5.0, clarity_rating=5.0, would_take_again=1)]
        score = compute_score(ratings, weights={
            "recency_rating": 1.0,
            "would_take_again": 1.0,
            "easiness": 1.0,
            "reliability": 1.0,
        })
        assert score.composite_score <= 1.0

    def test_top_tags_populated_and_sorted(self):
        ratings = [
            make_rating(rating_tags=["Respected", "Clear grading"]),
            make_rating(rating_tags=["Respected", "Tough grader"]),
            make_rating(rating_tags=["Respected"]),
        ]
        score = compute_score(ratings)
        assert score.top_tags[0] == ("Respected", 3)

    def test_top_tags_capped_at_10(self):
        # 11 unique tags
        unique_tags = [[f"Tag{i}"] for i in range(11)]
        ratings = [make_rating(rating_tags=tags) for tags in unique_tags]
        score = compute_score(ratings)
        assert len(score.top_tags) <= 10

    def test_difficulty_histogram_has_buckets_1_to_5(self):
        ratings = [make_rating(difficulty_rating=float(d)) for d in range(1, 6)]
        score = compute_score(ratings)
        assert set(score.difficulty_histogram.keys()) == {1, 2, 3, 4, 5}
        assert all(v == 1 for v in score.difficulty_histogram.values())

    def test_last_review_date_is_most_recent(self):
        ratings = [
            make_rating(date="2023-01-01 00:00:00 +0000 UTC"),
            make_rating(date="2024-06-15 00:00:00 +0000 UTC"),
            make_rating(date="2022-03-20 00:00:00 +0000 UTC"),
        ]
        score = compute_score(ratings)
        assert score.last_review_date == "2024-06-15"

    def test_last_review_date_none_when_no_dates(self):
        ratings = [make_rating(date="")]
        score = compute_score(ratings)
        assert score.last_review_date is None

    def test_all_weight_presets_produce_valid_composite(self):
        ratings = [make_rating() for _ in range(10)]
        for name, weights in WEIGHT_PRESETS.items():
            score = compute_score(ratings, weights=weights)
            assert 0.0 <= score.composite_score <= 1.0, f"preset '{name}' out of bounds"

    def test_higher_quality_ratings_produce_higher_composite(self):
        low_ratings = [
            make_rating(helpful_rating=1.0, clarity_rating=1.0, would_take_again=0, difficulty_rating=5.0)
            for _ in range(10)
        ]
        high_ratings = [
            make_rating(helpful_rating=5.0, clarity_rating=5.0, would_take_again=1, difficulty_rating=1.0)
            for _ in range(10)
        ]
        low_score = compute_score(low_ratings)
        high_score = compute_score(high_ratings)
        assert high_score.composite_score > low_score.composite_score


# ---------------------------------------------------------------------------
# compute_score_over_time
# ---------------------------------------------------------------------------

class TestComputeScoreOverTime:
    def test_year_bucketing_groups_correctly(self):
        ratings = [
            make_rating(date="2022-06-01 00:00:00 +0000 UTC"),
            make_rating(date="2022-09-01 00:00:00 +0000 UTC"),
            make_rating(date="2023-03-01 00:00:00 +0000 UTC"),
        ]
        timeline = compute_score_over_time(ratings, period=TimePeriod.YEAR)

        assert len(timeline.periods) == 2
        labels = [label for label, _ in timeline.periods]
        assert "2022" in labels
        assert "2023" in labels
        # 2022 bucket has 2 ratings
        score_2022 = dict(timeline.periods)["2022"]
        assert score_2022.num_ratings == 2

    def test_semester_bucketing(self):
        ratings = [
            make_rating(date="2023-02-01 00:00:00 +0000 UTC"),  # Spring
            make_rating(date="2023-10-01 00:00:00 +0000 UTC"),  # Fall
        ]
        timeline = compute_score_over_time(ratings, period=TimePeriod.SEMESTER)

        labels = [label for label, _ in timeline.periods]
        assert "2023-Spring" in labels
        assert "2023-Fall" in labels

    def test_quarter_bucketing(self):
        ratings = [
            make_rating(date="2023-01-15 00:00:00 +0000 UTC"),  # Q1
            make_rating(date="2023-07-15 00:00:00 +0000 UTC"),  # Q3
        ]
        timeline = compute_score_over_time(ratings, period=TimePeriod.QUARTER)

        labels = [label for label, _ in timeline.periods]
        assert "2023-Q1" in labels
        assert "2023-Q3" in labels

    def test_periods_sorted_oldest_first(self):
        ratings = [
            make_rating(date="2024-01-01 00:00:00 +0000 UTC"),
            make_rating(date="2021-01-01 00:00:00 +0000 UTC"),
            make_rating(date="2022-01-01 00:00:00 +0000 UTC"),
        ]
        timeline = compute_score_over_time(ratings, period=TimePeriod.YEAR)

        labels = [label for label, _ in timeline.periods]
        assert labels == sorted(labels)

    def test_invalid_period_raises_value_error(self):
        with pytest.raises(ValueError, match="period must be one of"):
            compute_score_over_time([make_rating()], period="monthly")

    def test_no_parseable_dates_returns_empty_timeline(self):
        ratings = [make_rating(date=""), make_rating(date="not a date")]
        timeline = compute_score_over_time(ratings)

        assert timeline.periods == []
        assert timeline.trend == 0.0
        assert timeline.total_span_years == 0.0

    def test_single_period_has_zero_trend(self):
        ratings = [make_rating(date="2023-01-01 00:00:00 +0000 UTC") for _ in range(5)]
        timeline = compute_score_over_time(ratings, period=TimePeriod.YEAR)

        assert timeline.trend == 0.0

    def test_positive_trend_when_quality_improves(self):
        # Early ratings are low quality, recent ratings are high quality
        early = [
            make_rating(
                date="2021-01-01 00:00:00 +0000 UTC",
                helpful_rating=1.0,
                clarity_rating=1.0,
                would_take_again=0,
            )
            for _ in range(5)
        ]
        recent = [
            make_rating(
                date="2024-01-01 00:00:00 +0000 UTC",
                helpful_rating=5.0,
                clarity_rating=5.0,
                would_take_again=1,
            )
            for _ in range(5)
        ]
        timeline = compute_score_over_time(early + recent, period=TimePeriod.YEAR)
        assert timeline.trend > 0

    def test_string_period_accepted(self):
        ratings = [make_rating(date="2023-01-01 00:00:00 +0000 UTC")]
        timeline = compute_score_over_time(ratings, period="year")
        assert len(timeline.periods) == 1


# ---------------------------------------------------------------------------
# compute_split_score
# ---------------------------------------------------------------------------

class TestComputeSplitScore:
    def test_separates_online_and_in_person(self):
        online = [make_rating(is_for_online_class=True) for _ in range(3)]
        in_person = [make_rating(is_for_online_class=False) for _ in range(5)]
        split = compute_split_score(online + in_person)

        assert split.online.num_ratings == 3
        assert split.in_person.num_ratings == 5

    def test_combined_includes_all(self):
        online = [make_rating(is_for_online_class=True) for _ in range(3)]
        in_person = [make_rating(is_for_online_class=False) for _ in range(5)]
        split = compute_split_score(online + in_person)

        assert split.combined.num_ratings == 8

    def test_empty_subset_returns_zero_sentinel(self):
        ratings = [make_rating(is_for_online_class=False) for _ in range(3)]
        split = compute_split_score(ratings)

        assert split.online.num_ratings == 0
        assert split.online.composite_score == 0.0

    def test_different_quality_per_format_reflected_in_scores(self):
        online = [
            make_rating(is_for_online_class=True, helpful_rating=5.0, clarity_rating=5.0)
            for _ in range(5)
        ]
        in_person = [
            make_rating(is_for_online_class=False, helpful_rating=1.0, clarity_rating=1.0)
            for _ in range(5)
        ]
        split = compute_split_score(online + in_person)

        assert split.online.raw_avg_rating > split.in_person.raw_avg_rating


# ---------------------------------------------------------------------------
# compare_professors
# ---------------------------------------------------------------------------

class TestCompareProfessors:
    def test_ranking_sorted_best_to_worst(self):
        strong = [
            make_rating(helpful_rating=5.0, clarity_rating=5.0, would_take_again=1)
            for _ in range(10)
        ]
        weak = [
            make_rating(helpful_rating=2.0, clarity_rating=2.0, would_take_again=0)
            for _ in range(10)
        ]
        comparison = compare_professors({"Strong": strong, "Weak": weak})

        assert comparison.best == "Strong"
        assert comparison.worst == "Weak"
        assert comparison.ranking[0][0] == "Strong"

    def test_best_professor_has_zero_delta(self):
        ratings_a = [make_rating(helpful_rating=5.0, clarity_rating=5.0) for _ in range(5)]
        ratings_b = [make_rating(helpful_rating=3.0, clarity_rating=3.0) for _ in range(5)]
        comparison = compare_professors({"A": ratings_a, "B": ratings_b})

        assert comparison.deltas[comparison.best] == 0.0

    def test_deltas_are_non_positive_except_best(self):
        ratings = {
            "A": [make_rating(helpful_rating=5.0, clarity_rating=5.0) for _ in range(5)],
            "B": [make_rating(helpful_rating=3.0, clarity_rating=3.0) for _ in range(5)],
            "C": [make_rating(helpful_rating=1.0, clarity_rating=1.0) for _ in range(5)],
        }
        comparison = compare_professors(ratings)

        for label, delta in comparison.deltas.items():
            if label == comparison.best:
                assert delta == 0.0
            else:
                assert delta <= 0.0

    def test_sort_by_easiness_score(self):
        easy = [make_rating(difficulty_rating=1.0) for _ in range(5)]
        hard = [make_rating(difficulty_rating=5.0) for _ in range(5)]
        comparison = compare_professors(
            {"Easy": easy, "Hard": hard},
            sort_by=SortBy.EASINESS_SCORE,
        )
        assert comparison.best == "Easy"

    def test_sort_by_string_accepted(self):
        ratings = {
            "A": [make_rating() for _ in range(5)],
            "B": [make_rating() for _ in range(5)],
        }
        comparison = compare_professors(ratings, sort_by="composite_score")
        assert comparison.sort_by == SortBy.COMPOSITE_SCORE

    def test_invalid_sort_by_raises_value_error(self):
        ratings = {"A": [make_rating()]}
        with pytest.raises(ValueError, match="sort_by must be one of"):
            compare_professors(ratings, sort_by="not_a_field")

    def test_empty_input_returns_empty_ranking(self):
        comparison = compare_professors({})
        assert comparison.ranking == []
        assert comparison.best == ""
        assert comparison.worst == ""

    def test_list_of_tuples_input(self):
        ratings_a = [make_rating() for _ in range(3)]
        ratings_b = [make_rating() for _ in range(3)]
        comparison = compare_professors([("A", ratings_a), ("B", ratings_b)])
        labels = [label for label, _ in comparison.ranking]
        assert set(labels) == {"A", "B"}

    def test_scores_dict_has_all_professors(self):
        ratings = {
            "A": [make_rating() for _ in range(3)],
            "B": [make_rating() for _ in range(3)],
        }
        comparison = compare_professors(ratings)
        assert set(comparison.scores.keys()) == {"A", "B"}


# ---------------------------------------------------------------------------
# compute_reliability_score
# ---------------------------------------------------------------------------

class TestComputeReliabilityScore:
    def test_zero_ratings_near_zero(self):
        score = compute_reliability_score(0)
        assert score < 0.1

    def test_at_target_approximately_half(self):
        # Default target is 25
        score = compute_reliability_score(25)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_increases_with_more_ratings(self):
        assert compute_reliability_score(10) < compute_reliability_score(25)
        assert compute_reliability_score(25) < compute_reliability_score(100)

    def test_approaches_one_asymptotically(self):
        score = compute_reliability_score(1000)
        assert score > 0.99

    def test_always_between_0_and_1(self):
        for n in [0, 1, 10, 25, 100, 500]:
            s = compute_reliability_score(n)
            # Upper bound is <= 1 not < 1: at extreme inputs like 500,
            # exp(-71.25) underflows to 0.0, so the result is exactly 1.0.
            assert 0 < s <= 1


# ---------------------------------------------------------------------------
# compute_easiness_score
# ---------------------------------------------------------------------------

class TestComputeEasinessScore:
    def test_minimum_difficulty_returns_one(self):
        ratings = [make_rating(difficulty_rating=1.0) for _ in range(5)]
        assert compute_easiness_score(ratings) == pytest.approx(1.0)

    def test_maximum_difficulty_returns_zero(self):
        ratings = [make_rating(difficulty_rating=5.0) for _ in range(5)]
        assert compute_easiness_score(ratings) == pytest.approx(0.0)

    def test_midpoint_difficulty_returns_half(self):
        ratings = [make_rating(difficulty_rating=3.0) for _ in range(5)]
        assert compute_easiness_score(ratings) == pytest.approx(0.5)

    def test_empty_returns_zero(self):
        assert compute_easiness_score([]) == 0.0

    def test_none_difficulty_excluded(self):
        ratings = [
            make_rating(difficulty_rating=1.0),
            make_rating(difficulty_rating=None),
        ]
        assert compute_easiness_score(ratings) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_tag_frequencies
# ---------------------------------------------------------------------------

class TestComputeTagFrequencies:
    def test_list_tags_counted(self):
        ratings = [
            make_rating(rating_tags=["Respected", "Clear grading"]),
            make_rating(rating_tags=["Respected"]),
        ]
        freqs = compute_tag_frequencies(ratings)
        assert freqs[0] == ("Respected", 2)

    def test_string_tags_split_on_double_dash(self):
        ratings = [make_rating(rating_tags="Respected--Clear grading--Tough grader")]
        freqs = dict(compute_tag_frequencies(ratings))
        assert "Respected" in freqs
        assert "Clear grading" in freqs
        assert "Tough grader" in freqs

    def test_sorted_by_frequency_descending(self):
        ratings = [
            make_rating(rating_tags=["A", "A", "B"]),
            make_rating(rating_tags=["A", "C"]),
        ]
        freqs = compute_tag_frequencies(ratings)
        counts = [count for _, count in freqs]
        assert counts == sorted(counts, reverse=True)

    def test_empty_ratings_returns_empty(self):
        assert compute_tag_frequencies([]) == []

    def test_none_tags_skipped(self):
        ratings = [
            make_rating(rating_tags=None),
            make_rating(rating_tags=["Respected"]),
        ]
        freqs = compute_tag_frequencies(ratings)
        assert len(freqs) == 1


# ---------------------------------------------------------------------------
# compute_difficulty_histogram
# ---------------------------------------------------------------------------

class TestComputeDifficultyHistogram:
    def test_has_buckets_1_to_5(self):
        hist = compute_difficulty_histogram([])
        assert set(hist.keys()) == {1, 2, 3, 4, 5}

    def test_counts_per_bucket(self):
        ratings = [
            make_rating(difficulty_rating=1.0),
            make_rating(difficulty_rating=1.0),
            make_rating(difficulty_rating=5.0),
        ]
        hist = compute_difficulty_histogram(ratings)
        assert hist[1] == 2
        assert hist[5] == 1
        assert hist[2] == 0

    def test_rounds_fractional_difficulty(self):
        ratings = [make_rating(difficulty_rating=1.4), make_rating(difficulty_rating=1.6)]
        hist = compute_difficulty_histogram(ratings)
        assert hist[1] == 1  # 1.4 rounds to 1
        assert hist[2] == 1  # 1.6 rounds to 2

    def test_none_difficulty_excluded(self):
        ratings = [make_rating(difficulty_rating=None)]
        hist = compute_difficulty_histogram(ratings)
        assert all(v == 0 for v in hist.values())


# ---------------------------------------------------------------------------
# compute_recency_weighted_rating
# ---------------------------------------------------------------------------

class TestComputeRecencyWeightedRating:
    def test_empty_returns_zero(self):
        assert compute_recency_weighted_rating([]) == 0.0

    def test_result_within_rating_scale(self):
        ratings = [make_rating(helpful_rating=4.0, clarity_rating=4.0)]
        result = compute_recency_weighted_rating(ratings)
        assert 1.0 <= result <= 5.0

    def test_recent_rating_weighted_more_than_old(self):
        # Two ratings: same quality, one recent and one very old.
        # Mix them together to check that the result leans toward the recent one.
        recent = make_rating(
            helpful_rating=5.0,
            clarity_rating=5.0,
            date="2025-01-01 00:00:00 +0000 UTC",
        )
        old = make_rating(
            helpful_rating=1.0,
            clarity_rating=1.0,
            date="2010-01-01 00:00:00 +0000 UTC",
        )
        result = compute_recency_weighted_rating([recent, old])
        # Unweighted mean would be 3.0; recency weighting should push above 3.0
        assert result > 3.0


# ---------------------------------------------------------------------------
# compute_review_velocity
# ---------------------------------------------------------------------------

class TestComputeReviewVelocity:
    def test_empty_returns_zero(self):
        assert compute_review_velocity([]) == 0.0

    def test_old_ratings_only_returns_zero(self):
        ratings = [make_rating(date="2010-01-01 00:00:00 +0000 UTC") for _ in range(5)]
        velocity = compute_review_velocity(ratings)
        assert velocity == 0.0

    def test_recent_ratings_produce_positive_velocity(self):
        ratings = [make_rating(date="2025-01-01 00:00:00 +0000 UTC") for _ in range(10)]
        velocity = compute_review_velocity(ratings)
        assert velocity > 0.0

    def test_velocity_proportional_to_recent_count(self):
        # 10 recent ratings over 2 years -> ~5/year
        ratings = [make_rating(date="2025-01-01 00:00:00 +0000 UTC") for _ in range(10)]
        velocity = compute_review_velocity(ratings, window_years=2.0)
        assert velocity == pytest.approx(10 / 2.0)

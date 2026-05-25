# Models

Dataclasses and enums used throughout the API. All are exported from `rmp_api` directly.

**Data flow:**

1. `search_*` functions return raw GraphQL dicts.
2. `get_professor_summary` returns a `ProfessorRating`.
3. `get_all_ratings` / `get_ratings_page` return `list[Rating]`.
4. `compute_score` takes `list[Rating]` and returns `ProfessorScore`.
5. `compare_professors` takes multiple rating lists and returns `ProfessorComparison`.
6. `compute_score_over_time` returns `ScoreTimeline`.
7. `compute_split_score` returns `SplitScore`.

---

::: rmp_api.models
    options:
      show_source: false

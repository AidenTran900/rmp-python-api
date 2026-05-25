# rmp-api

Python wrapper for the RateMyProfessors GraphQL API. Fetch professor ratings, compute quality signals, and compare professors programmatically.

> Based on [snow4060/rmp-api](https://github.com/snow4060/rmp-api).

## Installation

```bash
pip install git+https://github.com/youruser/rate-my-prof-api.git
```

Or install locally:

```bash
git clone https://github.com/youruser/rate-my-prof-api.git
cd rate-my-prof-api
pip install -e .
```

## Quick start

```python
from rmp_api import (
    search_schools,
    search_professors,
    get_professor_summary,
    get_all_ratings,
    compute_score,
    WEIGHT_PRESETS,
)

# Find a school
schools = search_schools("UC Berkeley")
school_id = schools[0]["node"]["id"]

# Get aggregate stats for a professor
summary = get_professor_summary("John DeNero", school_id)
print(summary.avg_rating, summary.link)

# Fetch all individual ratings
professor_id = search_professors("John DeNero", school_id)[0]["node"]["id"]
ratings = get_all_ratings(professor_id)

# Compute quality signals
score = compute_score(ratings, weights=WEIGHT_PRESETS["best_teacher"])
print(score.composite_score, score.top_tags)
```

## Key concepts

**IDs.** Two ID formats appear throughout the API. The `school_id` and `professor_id` parameters expect base64-encoded node IDs (e.g. `"U2Nob29sLTEyMw=="`). Retrieve these from the `node.id` field on search results. The `legacy_id` field (plain integer) is used only for constructing profile URLs.

**Pagination.** `get_ratings_page` returns one page at a time with a cursor. `get_all_ratings` wraps it and paginates automatically. Prefer `get_all_ratings` unless you need incremental loading.

**Caching.** `search_schools`, `search_professors`, `get_courses`, and the internal paginator are `lru_cache`-decorated. Results are cached for the process lifetime. Call `_fetch_all_ratings_cached.cache_clear()` to invalidate rating caches manually.

**Rating order.** Ratings are returned newest first by the RMP API.

## Notes

- No authentication required. Uses the public GraphQL endpoint.
- RMP may rate-limit heavy pagination. Add `time.sleep(0.5)` between requests if needed.
- `would_take_again_percent` and `would_take_again_pct` are `-1` or `0.0` respectively when insufficient data is available.

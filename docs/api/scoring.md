# Scoring

Functions for computing quality signals and comparing professors. All functions take a `list[Rating]` as input (from `get_all_ratings`) and return typed dataclasses.

**Weight presets.** `WEIGHT_PRESETS` is a dict of named weight configurations. Pass any entry directly to `weights=`:

```python
from rmp_api import WEIGHT_PRESETS, compute_score

score = compute_score(ratings, weights=WEIGHT_PRESETS["best_teacher"])
```

Available presets:

| Key | Description |
|-----|-------------|
| `"overall"` | Balanced default |
| `"best_teacher"` | Emphasizes recency and would-take-again |
| `"easiest"` | Emphasizes easiness |
| `"most_reliable"` | Emphasizes reliability (sample size) |

**Custom weights.** Supply a dict with any subset of these keys; missing keys default to `0`:

```python
score = compute_score(ratings, weights={
    "recency_rating": 0.4,
    "would_take_again": 0.3,
    "easiness": 0.2,
    "reliability": 0.1,
})
```

Values should sum to approximately `1.0`. The composite score is clamped to `[0, 1]`.

---

::: rmp_api.scoring.score
    options:
      members:
        - compute_score
        - compute_score_over_time
        - compute_split_score
        - compare_professors
      show_source: false

---

::: rmp_api.scoring.signals
    options:
      show_source: false

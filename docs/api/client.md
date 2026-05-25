# Client

Functions for searching schools and professors, fetching ratings, and filtering reviews. All functions communicate with the RateMyProfessors GraphQL API.

**Common parameter notes:**

- `school_id` and `professor_id` are base64-encoded node IDs. Retrieve them from the `node.id` field on search results, not `node.legacyId`.
- Functions that call the network return `None` or `[]` on failure and print the error to stdout.
- `search_schools`, `search_professors`, `get_courses`, and the internal paginator are `lru_cache`-decorated per process.

---

::: rmp_api.client
    options:
      members:
        - search_schools
        - search_professors
        - get_professor_summary
        - get_ratings_page
        - get_all_ratings
        - get_representative_ratings
        - get_courses
        - filter_ratings_by_keywords
      show_source: false

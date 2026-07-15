# PR Response Doc — CineLog Watchlist Feature

## AI Usage
<!-- Fill in at the end — how you used AI tools during this project -->

## Comment 1 — Rename
**What I did:**
I renamed the `save_to_watchlist()` function and all instances throughout the project to `add_to_watchlist()`.
**How I verified:**
I searched the project for all references to `save_to_watchlist` (definition, route handlers, imports, and calls) and renamed each one to `add_to_watchlist`. After renaming, I re-ran the same search and confirmed zero remaining matches for the old name.

## Comment 2 — Deduplication
**What I did:**
`add_to_watchlist()` in `services/watchlist_service.py` was missing the duplicate check that `add_to_collection()` already has. I added the same pattern: query for an existing `WatchlistEntry` with the same `user_id`/`film_id` before inserting, and raise a new `AlreadyInWatchlistError` (mirroring `AlreadyInCollectionError`) if one already exists.
**How I verified:**
I added `tests/test_watchlist.py::test_add_to_watchlist_duplicate_raises`, which adds the same film to a user's watchlist twice and asserts the second call raises `AlreadyInWatchlistError` while only one `WatchlistEntry` row exists in the database. I ran the test suite and confirmed it passes.

## Comment 3 — Missing test
**What I did:**
`services/watchlist_service.py` had no test coverage at all, unlike `services/collection_service.py` (covered by `tests/test_collection.py`). I created `tests/test_watchlist.py`, mirroring the existing collection test suite's fixtures and structure, with the three cases CONTRIBUTING.md requires for a service function: a happy-path test (`test_add_to_watchlist_creates_entry`), a duplicate/conflict test (`test_add_to_watchlist_duplicate_raises`, covering the Comment 2 fix), and a nonexistent-ID test (`test_add_to_watchlist_nonexistent_film_raises`).
**How I verified:**
I ran `pytest tests/test_watchlist.py -v` and confirmed all 3 tests pass.

## Comment 4 — Default visibility
**My position:**
I'd change the default to public=False (opt-in sharing) instead of keeping public=True.
**Reasoning:**
At first, I thought keeping public=True made sense because this flag controls whether a watchlist activity is visible, not the film itself, and discovering what others are watching is a big part of the app. After looking at it more closely, though, I don't think that's enough to justify making everything public by default. A user's watchlist can still reveal personal information, like political, religious, or recovery-related interests. On top of that, users don't currently have any way to opt out since add_film doesn't accept a public field. That means every new entry is automatically public without the user ever making that choice. I think it's better to follow a privacy-by-default approach where users can choose to share later instead of exposing their activity first.
**Tradeoff acknowledged:**
Making the default False does make the social side of the app a little less seamless since users won't automatically appear in activity feeds unless they choose to share. That could reduce engagement, but I think giving users control over their privacy is the better tradeoff, especially since there's no opt-out option right now.

## Comment 5 — Sort order
**My position:**
Rather than switching `get_watchlist()` straight to `date_added.desc()` (matching `get_collection()`) or leaving it as alphabetical, I'd sort by `date_added.desc()` first and use `Film.title.asc()` as a tiebreaker.
**Reasoning:**
`date_added.desc()` alone isn't fully deterministic: if a user adds multiple films in the same request/batch, or the database's timestamp resolution isn't fine enough to distinguish near-simultaneous inserts, entries with an identical `date_added` can come back in an arbitrary order across queries. Adding `Film.title.asc()` as a secondary sort key guarantees a stable, repeatable order for ties without changing the primary ordering the maintainer wants.
**Engagement with reviewer's point:**
I agree with the maintainer's underlying argument: `get_watchlist()` sorting alphabetically while `get_collection()` sorts by recency is an inconsistency that makes the two nearly identical endpoints behave unpredictably differently, which is confusing for anyone consuming the API. My proposal keeps that consistency (recency is still the primary, user facing order) while closing a smaller correcness gap the pure `date_added.desc()` approach leaves open.

## Comment 6 — Rebase
**What conflicted:**
**How I resolved it:**
**How I verified no conflict remains:**

## PR Description
<!-- Written at the end — feature overview, design decisions, manual testing steps -->
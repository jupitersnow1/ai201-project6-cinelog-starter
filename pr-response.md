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
**How I verified:**

## Comment 4 — Default visibility
**My position:**
**Reasoning:**
**Tradeoff acknowledged:**

## Comment 5 — Sort order
**My position:**
**Reasoning:**
**Engagement with reviewer's point:**

## Comment 6 — Rebase
**What conflicted:**
**How I resolved it:**
**How I verified no conflict remains:**

## PR Description
<!-- Written at the end — feature overview, design decisions, manual testing steps -->
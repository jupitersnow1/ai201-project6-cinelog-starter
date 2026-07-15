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
Running `git fetch origin` and `git rebase origin/main` paused with a conflict on `.gitignore` — both branches had independently added the file, `main`'s version additionally ignoring `.pytest_cache/`. Separately (without a git conflict marker, but a real breakage), the rebase's auto-merge silently dropped the entire `WatchlistEntry` class from `models.py`, since `main` had heavily rewritten the surrounding `Film` class as part of migrating `Film.id` from an integer primary key to a UUID (`db.String(36)`). That model class disappearing left `Film.watchlist_entries` referencing an undefined `WatchlistEntry`, and my `services/watchlist_service.py` and `routes/watchlist/watchlist.py` code still assumed `film_id` was an integer.

**How I resolved it:**
For `.gitignore`, I merged both versions' entries into one file. For the dropped model, I restored the `WatchlistEntry` class in `models.py`, updating `film_id` from `db.Integer` to `db.String(36)` to match the new UUID-based `Film.id`. I then updated the stale docstrings in `watchlist_service.py` and `routes/watchlist/watchlist.py` that still described `film_id` as an integer.

**How I verified no conflict remains:**
I ran `git log --oneline --merges origin/main..HEAD` to confirm no merge commits exist in my branch history, and `grep -rn "film_id.*int" services/ routes/` to confirm no remaining integer-ID references. i also ran the full test suite (`pytest tests/ -v`) and confirmed all 8 tests pass against the rebased code.

## PR Description

**Feature overview**
This PR adds a watchlist feature to CineLog. Users can save movies they want to watch later, view their watchlist, and avoid adding the same movie more than once. I followed the same service, route, error handling, and testing patterns as the existing collection feature so both features behave consistently.

Endpoints:
- GET /watchlist/<user_id> – Returns a user's watchlist, sorted by the most recently added movies first. If multiple movies were added at the same time, they're sorted alphabetically by title.

- POST /watchlist/<user_id>/add – Adds a movie to a user's watchlist. Request body: { "film_id": "<uuid>" }.

**Design decisions**
- Deduplication (Comment 2): add_to_watchlist() now raises AlreadyInWatchlistError (409) if a movie is already in the user's watchlist instead of creating a duplicate. This matches how add_to_collection() already works.

- Sort order (Comment 5): get_watchlist() sorts entries by date_added in descending order, with Film.title used as a tiebreaker. This keeps the order consistent even if multiple movies are added at the same timestamp.

- Default visibility (Comment 4): I discussed this but didn't change it in this PR. WatchlistEntry.public still defaults to True. My view is that it should default to False since users currently don't have a way to opt out, but I left it as an open design decision for the maintainer instead of changing a shared model default on my own.

- UUID consistency: During the rebase with main, WatchlistEntry.film_id was updated from db.Integer to db.String(36) to match the project's switch to UUID film IDs (see Comment 6).

**Manual testing steps**
1. Start the app locally (flask run or equivalent) using a fresh or seeded database.

2. Create a user and a movie (or use existing seed data) to get a user_id and film_id.

3. Send a POST /watchlist/<user_id>/add request with { "film_id": "<film_uuid>" }. You should get a 201 response with the new watchlist entry.

4. Send the same request again. 
You should get a 409 error saying the movie is already in the user's watchlist instead of creating a duplicate.

5. Send a POST request with a nonexistent film_id. You should get a 404.

6. Add a few different movies at different times, then call GET /watchlist/<user_id>. Verify the watchlist is ordered from newest to oldest, with alphabetical ordering for movies added at the same time.

7. Run pytest tests/ -v. All 8 tests (4 collection and 4 watchlist) should pass.
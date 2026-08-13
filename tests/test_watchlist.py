"""
tests/test_watchlist.py — CineLog

Tests for the watchlist service.
"""

import pytest
from app import create_app, db
from models import User, Film, WatchlistEntry
from services.watchlist_service import (
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
    AlreadyInWatchlistError,
    NotInWatchlistError,
)
from services.collection_service import FilmNotFoundError


@pytest.fixture
def app():
    """Create an isolated test app with an in-memory database."""
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """A user to use in tests."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    """A film to use in tests."""
    with app.app_context():
        film = Film(title="Paddington 2", year=2017, genre="Comedy")
        db.session.add(film)
        db.session.commit()
        return film.id


# ── basic add ───────────────────────────────────────────────────────────────

def test_add_to_watchlist_creates_entry(app, sample_user, sample_film):
    """
    Adding a valid film should create a WatchlistEntry in the database.
    """
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film)

        assert entry is not None
        assert entry.user_id == sample_user
        assert entry.film_id == sample_film

        # Verify it persisted
        in_db = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).first()
        assert in_db is not None


# ── deduplication ────────────────────────────────────────────────────────────

def test_add_to_watchlist_duplicate_raises(app, sample_user, sample_film):
    """
    Adding the same film twice should raise AlreadyInWatchlistError,
    not silently create a duplicate entry.
    """
    with app.app_context():
        add_to_watchlist(user_id=sample_user, film_id=sample_film)

        with pytest.raises(AlreadyInWatchlistError):
            add_to_watchlist(user_id=sample_user, film_id=sample_film)

        # Confirm only one entry exists
        count = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).count()
        assert count == 1


# ── Nonexistent film ─────────────────────────────────────────────────────────

def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):
    """
    Adding a film_id that doesn't exist in the database should raise
    FilmNotFoundError, not a database integrity error.
    """
    with app.app_context():
        fake_film_id = 999999

        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=fake_film_id)


# ── get_watchlist sort order ─────────────────────────────────────────────────

def test_get_watchlist_sorts_by_date_added_desc_then_title(app, sample_user):
    """
    get_watchlist() should sort by date_added descending (most recent first),
    using title as a tiebreaker when date_added is identical.
    """
    with app.app_context():
        from datetime import datetime, timezone, timedelta

        film_a = Film(title="Zodiac", year=2007, genre="Thriller")
        film_b = Film(title="Amelie", year=2001, genre="Romance")
        film_c = Film(title="Blade Runner", year=1982, genre="Sci-Fi")
        db.session.add_all([film_a, film_b, film_c])
        db.session.commit()

        earlier = datetime.now(timezone.utc) - timedelta(days=5)
        same_time = datetime.now(timezone.utc)

        entry_a = WatchlistEntry(user_id=sample_user, film_id=film_a.id, date_added=earlier)
        # b and c share the same date_added, so title should break the tie
        entry_b = WatchlistEntry(user_id=sample_user, film_id=film_b.id, date_added=same_time)
        entry_c = WatchlistEntry(user_id=sample_user, film_id=film_c.id, date_added=same_time)
        db.session.add_all([entry_a, entry_b, entry_c])
        db.session.commit()

        watchlist = get_watchlist(sample_user)
        titles = [f["title"] for f in watchlist]

        # Amelie and Blade Runner (same date_added) come before Zodiac (older),
        # and are alphabetically ordered between themselves.
        assert titles == ["Amelie", "Blade Runner", "Zodiac"]


# ── remove_from_watchlist ─────────────────────────────────────────────────────

def test_remove_from_watchlist_deletes_entry(app, sample_user, sample_film):
    """
    Removing a film that's in the watchlist should delete its entry.
    """
    with app.app_context():
        add_to_watchlist(user_id=sample_user, film_id=sample_film)

        result = remove_from_watchlist(user_id=sample_user, film_id=sample_film)
        assert result is True

        in_db = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).first()
        assert in_db is None


def test_remove_from_watchlist_nonexistent_entry_raises(app, sample_user, sample_film):
    """
    Removing a film that was never added to the watchlist should raise
    NotInWatchlistError instead of silently succeeding.
    """
    with app.app_context():
        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(user_id=sample_user, film_id=sample_film)


# ── public visibility toggle ──────────────────────────────────────────────────

def test_add_to_watchlist_defaults_to_private(app, sample_user, sample_film):
    """
    Not passing `public` should default the entry to private (public=False),
    per the Comment 4 design decision in pr-response.md.
    """
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film)
        assert entry.public is False


def test_add_to_watchlist_respects_explicit_public_true(app, sample_user, sample_film):
    """
    Callers should be able to explicitly opt an entry into being public.
    """
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film, public=True)
        assert entry.public is True


# ── edge case: entries across different users ────────────────────────────────

def test_get_watchlist_only_returns_requested_users_entries(app, sample_film):
    """
    get_watchlist() should only return entries belonging to the requested
    user, even when other users have entries for the same film. This guards
    against a query that accidentally omits the user_id filter (e.g. a
    regression to `WatchlistEntry.query.join(Film).all()`).
    """
    with app.app_context():
        user_a = User(username="alice", email="alice@example.com")
        user_b = User(username="bob", email="bob@example.com")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        add_to_watchlist(user_id=user_a.id, film_id=sample_film)
        add_to_watchlist(user_id=user_b.id, film_id=sample_film)

        watchlist_a = get_watchlist(user_a.id)
        assert len(watchlist_a) == 1

        watchlist_b = get_watchlist(user_b.id)
        assert len(watchlist_b) == 1


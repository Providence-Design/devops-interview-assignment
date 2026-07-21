"""Tests for the candidate-filtering logic in main.py.

Runs against the real seeded ages this exercise documents in
keycloak/README.md - no live Keycloak needed, since these tests exercise
parse_last_login/is_excluded directly, not the HTTP layer.
"""

from datetime import datetime, timedelta, timezone

from cleaner.main import parse_last_login, is_excluded


def _seeded_user(username: str, days_ago: int, service_account: bool = False) -> dict:
    """Builds a user dict shaped like what list_users() actually returns -
    epoch milliseconds as a string, confirmed against real Keycloak output."""
    epoch_ms = int((datetime.now(timezone.utc) - timedelta(days=days_ago)).timestamp() * 1000)
    user = {
        "id": f"id-{username}",
        "username": username,
        "attributes": {"lastLogin": [str(epoch_ms)]},
    }
    if service_account:
        user["serviceAccountClientId"] = "some-other-client"
    return user


def test_dave_at_124_days_is_over_threshold():
    dave = _seeded_user("dave", 124)
    last_login = parse_last_login(dave)
    inactive_days = (datetime.now(timezone.utc) - last_login).days
    assert inactive_days >= 120


def test_eve_at_116_days_is_under_threshold():
    eve = _seeded_user("eve", 116)
    last_login = parse_last_login(eve)
    inactive_days = (datetime.now(timezone.utc) - last_login).days
    assert inactive_days < 120


def test_break_glass_excluded_despite_being_oldest():
    break_glass = _seeded_user("break-glass", 320)
    assert is_excluded(break_glass, exclusions=["admin", "break-glass"])


def test_exclusion_is_case_insensitive():
    user = _seeded_user("Break-Glass", 320)
    assert is_excluded(user, exclusions=["break-glass"])


def test_service_account_always_excluded_even_if_stale():
    stale_service_account = _seeded_user("some-client", 999, service_account=True)
    assert is_excluded(stale_service_account, exclusions=[])


def test_missing_last_login_is_unparseable_not_a_candidate():
    mystery_user = {"id": "id-mystery", "username": "mystery", "attributes": {}}
    assert parse_last_login(mystery_user) is None


def test_malformed_last_login_is_unparseable_not_a_candidate():
    bad_user = {
        "id": "id-bad",
        "username": "bad",
        "attributes": {"lastLogin": ["not-a-timestamp"]},
    }
    assert parse_last_login(bad_user) is None
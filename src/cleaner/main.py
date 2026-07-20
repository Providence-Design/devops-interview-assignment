"""Entry point.

Run with:
    python -m cleaner.main

Suggested flow:
    1. Load config from environment
    2. Build a Keycloak client
    3. List users, filter for stale ones (respect exclusions)
    4. If dry-run, log the candidates. Otherwise, delete them.
    5. Emit a summary (log line, metric, whatever fits your design)
"""



import sys
from datetime import datetime, timezone

from .config import Config
from .keycloak_client import KeycloakClient


def parse_last_login(user: dict) -> datetime | None:
    """lastLogin is a seeded custom attribute, stored as Unix epoch
    milliseconds (confirmed against real seed data, not ISO 8601).
    Returns None if missing/unparseable - treated as unknown, never
    as a cleanup candidate."""
    attrs = user.get("attributes") or {}
    values = attrs.get("lastLogin")
    if not values:
        return None
    try:
        epoch_ms = int(values[0])
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    except (ValueError, IndexError):
        return None


def is_excluded(user: dict, exclusions: list[str]) -> bool:
    username = (user.get("username") or "").lower()
    if username in exclusions:
        return True
    if user.get("serviceAccountClientId"):
        return True
    return False


def main() -> int:
    config = Config.from_env()
    client = KeycloakClient(
        base_url=config.keycloak_url,
        realm=config.realm,
        client_id=config.client_id,
        client_secret=config.client_secret,
    )

    now = datetime.now(timezone.utc)
    exclusions = [e.lower() for e in config.exclusions]

    candidates = []
    total = 0
    skipped_unknown = 0

    for user in client.list_users():
        total += 1
        if is_excluded(user, exclusions):
            continue

        last_login = parse_last_login(user)
        if last_login is None:
            skipped_unknown += 1
            continue

        inactive_days = (now - last_login).days
        if inactive_days >= config.inactivity_days:
            candidates.append((user, inactive_days))

    print(
        f"Scanned {total} users. {len(candidates)} candidates. "
        f"{skipped_unknown} skipped (unknown activity).",
        file=sys.stderr,
    )

    succeeded = []
    failed = []

    for user, days in candidates:
        print(f"  candidate: {user['username']} (inactive {days} days)", file=sys.stderr)

        if config.dry_run:
            continue

        try:
            client.delete_user(user["id"])
            succeeded.append(user["username"])
        except Exception as exc:
            print(f"  FAILED to disable {user['username']}: {exc}", file=sys.stderr)
            failed.append(user["username"])

    print(
        f"SUMMARY realm={config.realm} dry_run={config.dry_run} "
        f"scanned={total} candidates={len(candidates)} "
        f"disabled={len(succeeded)} failed={len(failed)}",
        file=sys.stderr,
    )

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
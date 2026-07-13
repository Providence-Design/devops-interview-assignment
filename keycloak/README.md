# Keycloak seed data

## What's here

- `realm-export.json`: one realm (`acme`) with:
  - One confidential service client `user-cleanup-service` (client_credentials, secret `cleanup-secret-change-me`)
  - One public client `acme-portal` (illustrative, not required for the task)
  - Nine users (fixed IDs) and `unmanagedAttributePolicy: ENABLED` so a `lastLogin` custom attribute can be stored on them
- `seed.sh`: runs on `make up` (re-run with `make seed`). Sets each user's `lastLogin` attribute **and** inserts a real backdated `LOGIN` event, both computed relative to *now* so ages never go stale.
- `grant-service-account-roles.sh`: runs after realm import to grant the service account the roles it needs (view-users, manage-users, query-users, view-events)

## The `lastLogin` attribute is a deliberate simplification

Keycloak does not natively expose "last login time" as a first-class user field. In production you'd typically use one of:

1. **Event logging.** Keycloak stores `LOGIN` events (when enabled) and you can query them via `/admin/realms/{realm}/events?type=LOGIN&user={id}`. Downside: events have retention limits.
2. **Custom user federation.** Store the last login time in an external store updated on each successful auth.
3. **A login flow authenticator (SPI).** Custom Authenticator SPI that updates a user attribute on every login.

For this exercise we've seeded a `lastLogin` user attribute directly (via `seed.sh`), so you can focus on the cleanup logic rather than building the login-tracking mechanism. Mention in your README that this simplification exists and what you'd do differently in production.

**You can use either signal.** `seed.sh` also inserts a real, backdated `LOGIN` event per user into the events store, so the event-based approach works too:

```bash
# events for one user (needs the view-events role — granted by make grant-roles)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/admin/realms/acme/events?type=LOGIN&user=<user-id>" | jq
```

The `lastLogin` attribute and the latest `LOGIN` event carry the same age for each user, so both paths agree.

## User ages (as seeded)

Ages are computed relative to whenever you last ran `make up` / `make seed`, so they stay correct over time. The two near-boundary users sit a few days off 120 on purpose, so the boundary holds even if you seed once and work across a few days.

| Username    | lastLogin (days ago) | Expected outcome at default 120-day threshold |
|-------------|----------------------|-----------------------------------------------|
| alice       | 210                  | DELETE                                        |
| bob         | 175                  | DELETE                                        |
| carol       | 150                  | DELETE                                        |
| dave        | 124                  | DELETE (just over threshold)                  |
| eve         | 116                  | KEEP (just under threshold)                   |
| frank       |  60                  | KEEP                                          |
| grace       |  21                  | KEEP                                          |
| heidi       |   3                  | KEEP                                          |
| break-glass | 320                  | KEEP (excluded despite age)                   |

The `break-glass` user is deliberately old to test that your exclusion logic actually excludes (it's in the default `EXCLUSIONS` list — see `.env.example`).

## Roles granted to the service account

The `grant-service-account-roles.sh` script grants the following `realm-management` client roles to the service account of `user-cleanup-service`:

| Role | Purpose |
|---|---|
| `view-users` | list and read users |
| `manage-users` | update and delete users |
| `query-users` | search users |
| `view-events` | read login events (if you use the event-based approach) |

## Verifying access

Once `make up` and `make grant-roles` have completed:

```bash
# Get a token
TOKEN=$(curl -s -X POST http://localhost:8080/realms/acme/protocol/openid-connect/token \
  -d grant_type=client_credentials \
  -d client_id=user-cleanup-service \
  -d client_secret=cleanup-secret-change-me | jq -r .access_token)

# List users
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/admin/realms/acme/users | jq '.[].username'
```

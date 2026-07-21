## 1. Approach chosen, approaches rejected

**Signal for "last login":** the `lastLogin` custom user attribute, stored as
Unix epoch milliseconds (confirmed against real seed data, not assumed).
Reading it costs nothing extra it comes back on the same `list_users()`
call as everything else. I considered the events API instead, but that
would mean a second request per user (N+1) for the same answer, so I
didn't use it. In a real deployment, this attribute would need to be
written by something on every login a login-flow SPI is scaffolded in
`spi/` for that; the seed data stands in for it here.

**Disable, not delete.** The job disables stale users (`enabled: false`)
by default rather than hard-deleting them. Disabling is reversible; delete
is not. An unattended CronJob with delete permissions and no human review
is a bad pairing for something as consequential as removing an identity.
`CLEANUP_ACTION` is configurable to `delete` for teams that want a hard
purge, but that's an explicit opt-in, not the default.

**Unknown activity is never a candidate.** A user with a missing or
unparseable `lastLogin` is skipped, not treated as "old enough to clean
up." Silently deleting someone because the job couldn't read their
activity data would be the wrong failure mode for something with delete
permissions.

## 2. Kubernetes deployment

Helm chart in [`deploy/user-cleanup/`](deploy/user-cleanup/): a `CronJob`
(`concurrencyPolicy: Forbid` so two runs can't race the same realm, daily
schedule since inactivity is measured in days), a `ConfigMap` for
non-secret per-realm config, a `ServiceAccount`, and a `secretKeyRef` to
an existing Secret for the Keycloak client credential — never a hardcoded
value in `values.yaml`. `templates/secret.yaml` documents the External
Secrets Operator shape I'd use in production, left as a comment rather
than a live resource since committing a concrete `secretStoreRef` assumes
a specific secrets backend this chart shouldn't hard-couple to.

## 3. Config location and safety rails

Per-realm config (`realm`, `inactivityDays`, `exclusions`, `action`) lives
in `values.yaml` → rendered into the `ConfigMap`. The client secret never
touches either it's a `secretKeyRef` to a Secret this chart doesn't own.

Safety rails: `dryRun: true` by default, must be flipped deliberately;
exclusions matched case-insensitively; service-account users always
excluded regardless of the list; every run emits a structured summary
line (`SUMMARY realm=... dry_run=... scanned=... candidates=...
disabled=... failed=...`) as the audit trail. One user's API failure
doesn't abort the run — it's caught, logged, and reflected in the
summary's `failed` count.

## 4. Multi-realm seam

One Helm release per realm distinguished by release name,
`keycloak.realm`, and `keycloak.existingSecret`. I didn't build a
loop-over-realms mode inside the job itself: different realms plausibly
want different schedules and thresholds, and one realm's Keycloak being
down shouldn't block another realm's cleanup. A `values-<realm>.yaml` per
tenant gets you there without touching the Python. The seam is the Helm
values interface, not code inside `main.py`.

## 5. One thing I'd change in production

Move `lastLogin` off the manually-seeded attribute onto a real signal
the login-flow SPI in `spi/`, or the events API with a documented
retention assumption. The seeded attribute is an explicit simplification
for this exercise; shipping it as-is would mean the job silently stops
finding new stale users the moment nothing else is writing that
attribute.

## 6. AI usage

I used Claude throughout, in a back-and-forth session rather than accepting
a single generated dump. For src/cleaner/, I was given draft
implementations for get_token, list_users, and the disable-based
delete_user, which I typed in and ran myself against my local seeded
Keycloak rather than trusting them unread that's how I caught that
lastLogin is stored as Unix epoch milliseconds, not an ISO date string as
the first draft assumed; I only found that by inspecting the real API
response and had the parsing logic corrected before it went further. I
also introduced and fixed my own bug (a missing comma in the token
request payload) with AI's help reading the traceback, rather than it
writing that code error-free on the first pass.

The disable-vs-delete decision was mine, made deliberately: I asked
specifically for the trade-offs of each before choosing, rather than
accepting whichever the first draft defaulted to. Where I'd push back
in a real work setting the same way: I would want to sanity-check the
Helm chart's resource limits and CronJob schedule against real usage
patterns before trusting them in production, since those were reasonable
defaults, not measured ones. I also debugged a chain of local environment
issues myself (pip version, Python 3.9 vs the 3.11 requirement, a
conda/venv conflict) with AI's help interpreting error messages, since
those were specific to my machine and not something a generated draft
could have anticipated.
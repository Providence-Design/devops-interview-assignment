# Keycloak Stale-User Cleanup: Take-home Exercise

Design and ship a mechanism that cleans up users inactive for a configurable period (default 120 days) on Kubernetes. We assess how you deliver it, not whether you match a canonical solution.

## The whole job

1. Build cleanup logic against the seeded `acme` realm (see `keycloak/`)
2. Ship a Helm chart or manifests in [`deploy/`](deploy/) so it can run on Kubernetes
3. Write a one-page README in your repo covering the six points below
4. Optionally, send us feedback on the exercise — copy the [`FEEDBACK.md`](FEEDBACK.md) template into your submission email (see [Submitting](#submitting))

**Time cap.** If you already know this stack, a working version is roughly a day. If parts are new to you, take up to three days — treat that as a hard ceiling, not a target. You have one calendar week to *submit*: we know you have a job and responsibilities outside this and that the exercise is unpaid, so the week is there to fit it around your schedule, not to spend a week on it. Polish is not required; spend any spare time understanding what you shipped well enough to walk us through it.

## Your one-page README covers

1. Approach chosen, approaches rejected, reasoning
2. How this deploys on K8s (points at `deploy/`)
3. Where per-realm config lives, and safety rails (exclusions, dry-run, audit)
4. How the design would extend to many realms. You don't build it. Show the seam.
5. One thing you'd change in production
6. AI usage. Five to ten lines. Where AI helped, where you accepted its output, where you overrode it.

## Getting started

```bash
cp .env.example .env
make up            # Starts Keycloak + Postgres, imports the realm, seeds login data
make grant-roles   # Grants the service account the realm-management roles
```

Keycloak: `http://localhost:8080`, admin / admin. Realm: `acme`.

Optional, only if you want to test manifests against a real cluster:
```bash
make kind-up
```

## What we assess

| Assessed | Not assessed |
|---|---|
| Approach choice and trade-off reasoning | Whether your Helm chart passes `helm lint` |
| OAuth2 fluency (correct client, correct grant) | Whether the container image builds |
| Deploy shape in `deploy/` (Helm or manifests, applyable) | Test coverage, CI, Dockerfile polish |
| Safety rails (exclusions, dry-run, audit) | Multi-tenancy implementation |
| Tenant-aware seam in the design | Production hardening |
| AI usage maturity (specific, not generic) | Polish |
| Walkthrough performance | Matching a canonical answer |

New to parts of the stack? Fine. Say so in your README, and show us how you learned it.

## The `deploy/` directory is graded

This is where we see your Helm and IaC fluency. Skipping it costs you a whole rubric axis. Details in [`deploy/README.md`](deploy/README.md).

## AI use

Allowed and encouraged. This role will involve working with AI tools going forward, so we want to see you use them well.

In the walkthrough we ask where AI helped, where you accepted its output, and where you pushed back. This isn't a big part of the score — we just want a specific answer over a generic one. What matters far more is that you can explain and defend the code you shipped, whoever or whatever wrote the first draft.

## What's in this repo

```
.
├── docker-compose.yml           Keycloak + Postgres, realm auto-imported
├── Makefile                     Common commands (run `make help`)
├── .env.example                 Copy to .env
├── kind/                        Optional Kind cluster config
├── keycloak/                    Seeded realm + role-grant script
├── src/cleaner/                 Python skeleton (only if you go Python)
├── deploy/                      GRADED. Your chart or manifests go here.
├── spi/                         Placeholder if you go Java SPI
├── pyproject.toml
└── FEEDBACK.md                  Please fill in
```

## About the seeded `lastLogin` attribute

Keycloak does not natively expose "last login time" as a first-class field. In production you'd use event queries, a login-flow authenticator, or user federation. For this exercise `make up` seeds a `lastLogin` custom attribute on each user (and a matching real `LOGIN` event, if you'd rather query events) so you can focus on cleanup logic. Ages are computed relative to now, so they don't go stale. See [`keycloak/README.md`](keycloak/README.md) for the users and their ages, and mention this simplification in your own README.

## Submitting

Push your work to a repo on your own GitHub account — fork this one or start a fresh repo (a fork's git history is a small extra signal, since it shows how you work). Zip is fine if a repo is inconvenient.

**Submit by replying to the take-home email thread with:**

- a link to your GitHub repo
- optionally, your feedback on this exercise — paste the [`FEEDBACK.md`](FEEDBACK.md) template into the email and fill it in there

Keep feedback in the email, not in your repo: it stays separate from the work we assess, and it's genuinely useful to us. We book the 60-minute walkthrough within a few working days of your submission.

## Questions

Reply to the email thread. Raising questions early is a JD line we mean. Don't sit on ambiguity.

## Done

Your submission is complete when:

- [ ] The code runs against the seeded Keycloak and does what your README says
- [ ] `deploy/` contains an applyable Helm chart or manifest set
- [ ] Your one-page README covers all six points above
- [ ] The AI usage section is specific enough that we could pick which parts you wrote
- [ ] You've replied to the email thread with your repo link (and optionally the feedback template)

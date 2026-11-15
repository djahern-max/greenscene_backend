# Greenscene Backend — CLAUDE.md

## What this is
FastAPI backend for Greenscene (greenscene.io) — a multi-tenant recruiting and onboarding tool for green-industry companies (landscaping and similar). Rye Beach Landscaping, LLC is the intended first real tenant. Onboarding (generate a new-hire package, employee signs electronically) is a future module; nothing for it exists yet.

**Origin:** forked 2026-11-15 from `ryzerecruiting_backend` at commit `d3edd13`. Later work in the original repo (tenant restructure parts 1–3, the "Nice ATS" name) is not in this repo and is not the plan here. The original repo and its folder (`/Users/dane/code/ryzerecruiting_backend`) are Dane's preserved fallback — **never modify, commit to, or push from them.**

**The code still says RYZE.** Strings, emails, PDFs and config are un-rebranded; rebranding is a separate queued task. The sections below describe the code as it is today, so they still say RYZE where the code does.

**Tenant model (direction note, no code changed):** in the old product a tenant was a recruiting firm with employer clients and candidates. In Greenscene a tenant is expected to be a company hiring for itself. The data model (`tenants`, `employer_profiles`, `job_orders`, `candidates`) still has the recruiting-firm shape; whether the `employer_profiles` layer survives is an open design question.

## Stack
- **Framework:** FastAPI, routers included in `app/main.py`
- **DB:** PostgreSQL + pgvector, SQLAlchemy models in `app/models/`, Alembic migrations in `alembic/`
- **Auth:** Bearer token (JWT), `Authorization: Bearer <token>` header — not cookie-based
- **AI:** Anthropic Claude for generation/chat/briefs; OpenAI `text-embedding-3-small` for embeddings only — never use OpenAI for generation or Claude for embeddings
- **Integrations:** Zoom API + webhooks (meeting summaries, transcripts), Google Calendar API, Resend (email), Twilio (SMS, A2P 10DLC in progress), Stripe (billing), DigitalOcean Spaces via boto3 (file storage)
- **Scheduling:** APScheduler (ran as a systemd service on the old droplet; no service locally)

## Repo layout
- `app/api/` — route handlers, one file per resource (`bookings.py`, `candidates.py`, `employer_profiles.py`, `job_orders.py`, `chat.py`, `webhooks.py`, `settings.py`, etc.)
- `app/models/` — SQLAlchemy models
- `app/core/` — `config.py`, `database.py`, auth/tenant dependencies
- `app/services/` — external integrations and shared services (`spaces.py` for DO Spaces, `branding.py` for tenant branding resolution, `notifications.py`, `email.py`)
- `alembic/` — migrations; `env.py` imports every model explicitly — new models must be added there or Alembic won't detect them
- `audit_tenant_coverage.py` — static analysis script that walks `app/api/` and flags endpoints missing tenant scoping (SAFE / HARDCODED / REVIEW / PUBLIC / SKIP). Run this after any change touching auth or queries.

## Local development
Facts verified against this machine on 2026-11-15.

- Repo: `/Users/dane/code/greenscene_backend`. Sibling frontend: `/Users/dane/code/greenscene_frontend`.
- Virtualenv at `venv/`, built with Homebrew `python3.12`.
- Postgres is the Homebrew `postgresql@16` service (`postgresql@17` is also installed but in an error state). Local database `greenscene` with the `vector` extension; `alembic current` = `4083c0d3ba12 (head)`.
- Run with `uvicorn app.main:app --reload --port 8000` (verified running by Dane, 2026-11-15).
- `scripts/` is gitignored, so `scripts/create_superadmin.py` exists on disk but not on GitHub.
- Redis is installed via Homebrew and runs as a brew service on `localhost:6379` (hardcoded in `app/api/auth.py` and `app/services/rate_limit.py`). Only OAuth temp storage and the rate limiter for the public signup-firm / demo-request endpoints use it.

## CRITICAL: multi-tenant isolation
This is the single most important rule in this codebase. The platform is multi-tenant, so **every query on tenant-owned data must be scoped by `tenant_id`.**

- Use `get_current_tenant` / `get_current_admin_tenant` or `current_user.tenant_id` — never a hardcoded `RYZE_TENANT` constant for anything but genuinely RYZE-specific defaults.
- `chat_sessions` and `chat_messages` were previously found unscoped — treat any table without an obvious `tenant_id` filter as suspect until proven otherwise.
- Run `python audit_tenant_coverage.py` after touching any endpoint and paste me the new `REVIEW`/`HARDCODED` lines rather than assuming a fix worked.

## GUARDRAIL: `ryze` is a functional tenant slug — do not rename it
The string `ryze` is not just branding. It is a live tenant slug that gates billing, the AI budget, superadmin access and row ownership. **Do not rename, remove, or "clean up" any of the sites below as part of any task unless that task's spec says so in words.** Display-text rebranding and slug changes are different jobs.

Where the slug is functional (files and counts as of the fork):
- **`RYZE_TENANT = "ryze"` is defined four times:** `app/core/deps.py` (also the billing bypass and the NULL-`tenant_id` fallback), `app/services/branding.py`, `app/models/job_order.py`, `app/models/job_interest.py`.
- **Budget exemption:** `app/services/usage.py` (`is_over_budget` imports `RYZE_TENANT` from `deps.py`).
- **22 `or "ryze"` fallbacks:** 11 in `app/api/bookings.py`, 10 in `app/api/job_orders.py`, 1 in `app/api/db_explorer.py`.
- **Column defaults `default="ryze"`:** `app/models/user.py`, `app/models/employer_profile.py`.
- **Superadmin gates on `tenant_id == "ryze"`:** `app/api/admin_invite.py`, `app/api/db_explorer.py`.
- **11 `tenant_id: str = "ryze"` parameter defaults:** `app/services/notifications.py`.

## Tenant branding — resolver EXISTS, use it
The per-tenant branding resolver is **implemented** at `app/services/branding.py` — do not re-implement it or go looking for `app/core/tenant_branding.py` (an older doc referenced that path; it never existed).

- `get_branding(db, tenant_id)` returns a frozen `TenantBranding` dataclass. **Every field falls back individually to RYZE's global defaults** (`app.core.config.settings`), so a tenant with all-NULL override columns behaves exactly like RYZE. It is safe to call with `db=None` or an unknown tenant — you get RYZE defaults.
- Already migrated onto the resolver: `app/services/notifications.py` (all notify functions take `tenant_id` + `db` and resolve branding) and `app/services/email.py` (all senders take a `branding` parameter). Admins can override whitelisted branding fields via `GET/PATCH /api/settings/tenant` in `app/api/settings.py`.
- **Still hardcoded — remaining migration targets:** the PDF templates (`candidate_pdf_template.py`, `employer_pdf_template.py`, `job_order_pdf_template.py`) bake `RYZE.ai` / `RYZE.AI` into their footers. Verify `ai_brief.py` and `calendar.py` before assuming either way.
- **Known risk:** the notify functions default to `tenant_id="ryze"`. A call site that forgets to pass `tenant_id` silently sends RYZE-branded messages for another firm's data. When adding or touching a notify call site, always pass the real `tenant_id` and `db` explicitly. (Making the param required is a queued hardening task for before tenant #2 onboards.)
- **Secret handling:** `tenant.twilio_auth_token` is a credential-column stub for a future per-number model. Do NOT populate it in production until it's encrypted at rest. In the shared-sender model, tenants leave `twilio_*` NULL and ride on RYZE's number.
- **Resend:** `from_email` must be a Resend-verified domain. Until a firm verifies its own domain, leave its `from_email` NULL — mail sends from RYZE's verified address with the firm's display name and the firm's `reply_to`.

## Deploy & migration workflow — no host yet
There is no production server. The droplet that hosted `api.ryze.ai` is gone and hosting is TBD. Until a host exists, a task ends at `git push origin main` plus local verification.

These rules hold wherever the app is hosted next:
- **Always generate migrations locally** (`alembic revision --autogenerate`) and commit them — a server only ever runs `alembic upgrade head`.
- **Always stop the app before a migration** — open connections hold locks that block `ALTER TABLE`.
- Prefer `DELETE` over `TRUNCATE` on live tables — `TRUNCATE` needs an `ACCESS EXCLUSIVE` lock, `DELETE` only needs `ROW EXCLUSIVE`.
- Once a host exists, deploy and migration commands come to Dane as exact commands to run — don't execute them yourself.

### HISTORICAL — old droplet procedure (server no longer exists)
Kept for reference only; nothing below can be run. Production was a DigitalOcean droplet (167.71.93.90, user `dane`). The deploy always happened manually:

```
# local
git push

# on server
git pull
sudo systemctl stop ryze-api      # required before any Alembic migration
alembic upgrade head              # only run migrations on the server, never generate them there
sudo systemctl start ryze-api     # or restart
```

On that server the service to stop before a migration was `ryze-api` (gunicorn).

## Conventions
- **Route ordering matters:** static routes like `/me` must be declared before `/{id}` routes in the same router, or FastAPI treats `me` as a path param.
- **Resend** only sends from the verified `ryze.ai` domain — `from_email` stays fixed, vary `reply_to` and display name instead (see Tenant branding above).
- CORS errors in the browser console almost always mean a server-side 500 — check the uvicorn terminal output, not devtools, first.
- `SKIP_FILES` in `audit_tenant_coverage.py` (webhooks, blog, contact, ai_parser) are intentionally public/infrastructure — don't try to tenant-scope them.
- **PDF generation:** Playwright (`sync_playwright`) must run in plain `def` endpoints (not `async def`) so FastAPI executes it in a thread pool; use `wait_until="networkidle"` so Google Fonts load.

## How I want you to work
- **Audit before you refactor.** For anything beyond a one-line fix: read the relevant files, list what you'd change and why, and don't write code until I confirm.
- **One concern per change.** Don't bundle a tenant-scoping fix with a style cleanup with a rename — separate asks, separate diffs.
- I prefer **complete drop-in replacement files** for anything that's gotten complex, rather than partial diffs — I'll say so when I want that.
- Narrow, clearly-scoped surgical edits are fine without asking.
- Don't invent new abstractions or rename public APIs/endpoints unless I asked for that specifically.
- A task is not done until its commits are pushed to `origin/main` and its local verification passes. There is no deploy target yet (see "Deploy & migration workflow").

## Session workflow — context/current-feature.md
At the start of every session, read `context/current-feature.md` — it holds the active task's Status, Goals, Related Files, and Verification steps. Work from it, don't start unrelated work without checking it first.

- When you finish a meaningful chunk of work, add a dated line to its History section — earliest to latest.
- When a task is fully done and verified, tell me first and wait for my explicit confirmation. **Once I confirm**, archive it yourself: copy its final Goals summary + full History into `context/CHANGELOG.md` as a new entry at the **top**, matching the format of the existing entries, then reset `current-feature.md` — to the blank template, or to the next task's content if I've handed it to you in the same message. **Never archive unprompted or before I confirm.** The confirmation is the gate; nothing moves until I say the word.
- **Blank is a valid resting state.** Resetting `current-feature.md` to the blank template with *no* new task loaded is a normal close-out — Part 1 of a two-part swap (`context/session-opener.md`, Case A-close), not a sign the task was abandoned or that you should infer the next one. The next task may arrive in a later message; when it does, I'll place it in the file and point you at it (Case B). An empty `current-feature.md` is never license to start unrelated work — wait for the next task.
- If I ask you to start something not reflected in `current-feature.md`, ask whether to update the file first before writing code, rather than silently working off-script.
- **Keep this file honest:** when completed work makes any section of this CLAUDE.md inaccurate (a file moved, a "still needs X" item got done, a convention changed), flag it and propose the CLAUDE.md edit in the same session. Stale instructions here mislead every future session.

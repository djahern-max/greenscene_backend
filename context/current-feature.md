# Current Feature

Close the two live bugs from the rebrand audit — reserved `ryze` slug at signup; every notification carries its tenant

## Status
<!-- Not Started | In Progress | Completed -->
In Progress

## Goals
<!-- Goals & requirements -->
**Backend repo only.** Narrow fixes. No rebranding, no slug rename, no tenant
restructure, no change to what the `ryze` tenant is. Do not touch
`greenscene_frontend` or either original folder.

Source: `context/rebrand-audit.md` (commit `6434b11`), section "Live bugs
found", items 1–3. Read that section and its Section A / A.1 rows first; this
spec does not repeat the evidence. Line numbers below are from that commit —
re-locate each site before editing.

Route chosen (Dane, 2026-11-15): **narrow patches**, not a redo of the
November restructure from the original repo. The special `ryze` tenant stays.
The GUARDRAIL in `CLAUDE.md` still applies; this spec authorises, in words,
exactly these changes to guardrail sites and no others:
- the `tenant_id: str = "ryze"` parameter defaults in
  `app/services/notifications.py` (Bug 2, subject to Decision 3);
- the invite gate in `app/api/admin_invite.py` (Bug 3, subject to Decision 5).

### Bug 1 — public firm signup can claim the `ryze` slug
Done means:
1. `POST /api/auth/signup-firm` can never produce a tenant or a user whose slug
   is `ryze`, for any company name (any casing, punctuation or whitespace that
   normalises to it).
2. The same holds for the duplicated generator in `app/api/admin_invite.py`.
3. A slug already in use by any `users.tenant_id` value is treated as taken,
   even when no `tenants` row has it (this is the general form of the hole:
   the generator only looks at `tenants`).
4. Tests prove 1–3 (see Verification).

### Bug 2 — eight of eleven `notify_*` call sites send as the default tenant
Done means:
5. All eight call sites listed in the audit (`app/api/bookings.py` ×7,
   `app/services/scheduler.py` ×1) pass the booking's own tenant and a `db`
   session, the same way the three correct call sites do.
6. It is no longer possible to call a `notify_*` function without saying which
   tenant it is for (Decision 3).
7. A test fails if any `notify_*(` call anywhere under `app/` omits
   `tenant_id` or `db` — a static check over the source, so a future call site
   cannot reintroduce the bug.

### Bug 3 — invite gate (low severity)
8. Handled per Decision 5.

### Decisions to flag in the audit (do not pick — present options and wait)
**Decision 1 — what happens when a signup's slug is reserved or taken.**
  (a) Treat it exactly like today's collision: append a numeric suffix
      (`ryze_1`). No new error path; frontend unchanged.
  (b) Refuse with 409 and a message asking for a different company name.
  Recommend (a).

**Decision 2 — where the reserved list and the check live.** The generator is
  deliberately duplicated in `auth.py` and `admin_invite.py` ("so the
  superadmin invite flow stays completely untouched").
  (a) One shared helper (new small module under `app/services/`), both
      endpoints call it; the duplicate is removed.
  (b) Keep the duplication; add the same check to both.
  Also present the proposed reserved list. Minimum is `ryze`. Say whether you
  would add obvious platform words (for example `admin`, `api`, `platform`,
  `greenscene`) and why or why not — Dane decides the list.
  Recommend (a).

**Decision 3 — the `= "ryze"` defaults on the eleven `notify_*` functions.**
  (a) Remove the defaults so `tenant_id` and `db` are required; a missing
      argument is a `TypeError` at the call site, caught by tests.
  (b) Keep the defaults and fix only the eight call sites.
  Recommend (a). Under (a), list every caller, including seed scripts, tests
  and root-level scripts, and show none is left broken.

**Decision 4 — a booking whose `tenant_id` is NULL.** State first whether the
  column can be NULL in this schema and whether any local row is.
  (a) Coalesce at the call site the way the rest of `bookings.py` does today
      (`booking.tenant_id or RYZE_TENANT`). Consistent; keeps the guardrail.
  (b) Skip the notification and log a warning.
  Recommend (a).

**Decision 5 — the invite gate (`app/api/admin_invite.py:97`).** Its comment
  says "superadmin only"; the dependency is `get_current_admin_user`; it does
  not coalesce NULL the way other sites do.
  (a) Fix in this task as its own commit: require `is_superuser`, and state
      what happens for a NULL `tenant_id`.
  (b) Leave the code, correct the comment, record as a follow-up.
  No recommendation — say which accounts could call it today under each option.

## Related Files
- `app/api/auth.py` — `_generate_firm_slug`, `/signup-firm`
- `app/api/admin_invite.py` — `_generate_slug`, invite gate
- `app/schemas/user.py` — `SignupFirmRequest` (read; change only under Decision 1b)
- `app/services/notifications.py` — eleven `notify_*` signatures
- `app/api/bookings.py`, `app/services/scheduler.py` — eight call sites
- `app/api/job_orders.py` — a correct call site, for reference
- `tests/` — new tests; `tests/conftest.py` for the rolled-back-transaction fixture
- `CLAUDE.md` — only the lines this task makes inaccurate (the "Known risk"
  note under Tenant branding; GUARDRAIL counts if Decision 3a removes the
  eleven defaults). Propose the edits; the other corrections listed in the
  audit are a separate task.
- `context/rebrand-audit.md` — add one line under its header: line numbers are
  as of `6434b11`; this task moved some. Do not re-number the tables.

## Verification
- [ ] BEFORE any edit: `python audit_tenant_coverage.py` output and
      `pytest -m "not semantic"` result saved in the History as the baseline.
- [ ] Audit presented first: current code at each site, proposed change,
      Decisions 1–5 with options. No code before Dane confirms.
- [ ] New test: signup with company names `Ryze`, `RYZE!`, ` ryze ` and
      `R.Y.Z.E` — report the slug each one produces today and after; none is
      `ryze` after.
- [ ] New test: a slug present only in `users.tenant_id` is treated as taken.
- [ ] New test: static check that every `notify_*(` call under `app/` passes
      `tenant_id` and `db`. Show that it fails on the pre-fix code (run it
      against `6434b11` or temporarily revert one call site) and passes after.
- [ ] `pytest -m "not semantic"` → 0 failed, and no test that passed in the
      baseline now fails.
- [ ] `python audit_tenant_coverage.py` → no new REVIEW or HARDCODED lines
      versus the baseline.
- [ ] `uvicorn app.main:app --port 8000` starts clean and `GET /docs` → 200.
- [ ] One concern per commit: Bug 1, Bug 2, Bug 3 (if 5a), docs — separate
      commits. `git status` clean; pushed to `origin/main`.

## Notes
- Out of scope, recorded in the audit, each its own later task:
  - the signup bucket — unmatched self-registrations still land in `ryze`
    (A.1 item 8). Needs a product decision before any public launch;
  - the possible billing-check gap (39 inline tenant derivations that skip
    `_check_tenant_access`) — a lead, not yet traced;
  - the seven `CLAUDE.md` corrections;
  - the recruiting-firm framing in the AI prompts (audit C.1);
  - the rebrand itself.
- Not for Claude Code to change, flagged for Dane: the SMS-consent text and
  two emails name the legal entity "RYZE GROUP, Inc." and must match the
  Twilio registration (audit, Proposed scope 1, "Hold back").
- The original repo fixed both bugs differently in November (house tenant
  removed; notify arguments made required). Do not port that work or read the
  original folder for this task.

## History
<!-- Keep this updated. Earliest to latest -->
- 2026-11-15 — Task drafted (Claude, chat) from `context/rebrand-audit.md` at
  `6434b11` and a read-only look at `app/api/auth.py` and
  `app/services/notifications.py`. No code changed.
- 2026-11-15 — Baseline captured before any edit (Claude Code), at `51a95ca`.
  `python audit_tenant_coverage.py`: 95 endpoints scanned — 76 Safe,
  19 Public/Skip, 0 Hardcoded, 0 Needs review.
  `pytest -m "not semantic"`: **3 failed, 11 passed, 3 skipped, 3 deselected.**
  The 3 failures are all in `tests/test_tenant_isolation.py`
  (`test_owning_tenant_sees_its_calls_by_date`,
  `test_owning_tenant_finds_candidate_calls`,
  `test_candidate_tool_boundary_excludes_employer_contacts`) — they assert
  on `greenpath_recruiting` seed data and the local database is unseeded
  (0 bookings, 0 tenants, 1 user). `pytest` was not installed in `venv/`;
  installed it from `requirements-dev.txt` (pytest==9.1.1) to take the baseline.
  Audit and plan presented to Dane; no code changed.
- 2026-11-15 — Dane confirmed: Decisions 1a, 2a, 3a, 4a, 5a; reserved list
  `ryze, greenscene, admin, api, platform`; close the empty-slug hole in the
  Bug 1 commit with a `firm` fallback; pytest bar is "no new failures against
  the baseline"; do not seed.
  Baseline failures and causes (all three call the Intelligence chat tools in
  `app/api/chat.py` against `greenpath_recruiting` seed rows that the unseeded
  local database does not have; none imports or calls signup, the bookings
  endpoints, notifications or the scheduler — two of them do read the
  `bookings` table through those chat tools):
  - `test_owning_tenant_sees_its_calls_by_date` — `tool_get_meetings_by_date`
    returned 0 calls; expects the 2 seeded 2026-07-09 calls.
  - `test_owning_tenant_finds_candidate_calls` — `tool_get_candidate_calls`
    returned 0; expects seeded candidate Renata Voss.
  - `test_candidate_tool_boundary_excludes_employer_contacts` — same tool,
    same missing candidate.
- 2026-11-15 — Bug 1 fixed, commit `b896344`. New
  `app/services/tenant_slug.py` (`generate_tenant_slug`) replaces
  `_generate_firm_slug` in `auth.py` and `_generate_slug` in
  `admin_invite.py`. Reserved slugs are never issued; a slug in any
  `users.tenant_id` counts as taken; an empty base becomes `firm`.
  Slugs before → after: `Ryze` `ryze` → `ryze_1`; `RYZE!` `ryze` → `ryze_1`;
  ` ryze ` `ryze` → `ryze_1`; `R.Y.Z.E` `r_y_z_e` → `r_y_z_e` (unchanged, never
  was `ryze`); `!!!` and empty `""` → `firm`. `tests/test_tenant_slug.py`,
  26 tests, tested at the generator plus a check that both endpoints call it
  (the endpoints commit and need Redis, so they are not driven over HTTP).
- 2026-11-15 — Bug 2 fixed, commit `fb1fb01`. The eight call sites pass
  `tenant_id=booking.tenant_id or RYZE_TENANT, db=db`; the eleven `notify_*`
  signatures now end `*, tenant_id: str, db: Session` (no defaults).
  `tests/test_notify_call_sites.py` (static AST check + signature check) was
  run against the pre-fix code first: 2 failed, naming exactly the eight call
  sites and the 22 defaults; 3 passed after. The `or "ryze"` literal count in
  `bookings.py` is unchanged at 11 (new sites use the constant).
- 2026-11-15 — Bug 3 fixed, commit `52dca4e`. Invite endpoint depends on
  `get_current_superuser` and gates on
  `(tenant_id or RYZE_TENANT) == RYZE_TENANT`. `tests/test_invite_gate.py`,
  6 tests.
- 2026-11-15 — Verification. `pytest -m "not semantic"`: 3 failed, 46 passed,
  3 skipped, 3 deselected — the same 3 baseline failures, no new ones, 35 new
  tests pass. `python audit_tenant_coverage.py`: output byte-identical to the
  baseline (76 Safe, 19 Public/Skip, 0 Hardcoded, 0 Needs review).
  `uvicorn app.main:app` started clean and `GET /docs` → 200 (run on port
  8011 because Dane's `--reload` server holds 8000; that one also returned
  200 after reloading). Fix commits pushed to `origin/main`.

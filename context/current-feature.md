# Current Feature

Narrow rebrand (backend) — "Greenscene" on screen, greenscene.io in config; the `ryze` slug and the SMS-consent wording stay

## Status
<!-- Not Started | In Progress | Completed -->
Completed

## Goals
<!-- Goals & requirements -->
**Backend repo only.** Scope comes from `context/rebrand-audit.md`, section
"Proposed scope for the narrow rebrand", lists 1 and 2. Read that section and
the B, C and D tables first. The audit's line numbers are as of `6434b11`;
the bug-fix task moved some — re-locate every site before editing.

Decisions already made by Dane (2026-11-15) — do not reopen:
- Name on screen: **Greenscene** — that exact spelling everywhere, replacing
  both "RYZE.ai" and "RYZE" as a product name. Not "GreenScene", not
  "Greenscene.io".
- Domain: **greenscene.io**. Sending address: **hello@greenscene.io**.
- **Twilio / SMS consent: leave as is.** The registration was hard to get
  approved. Nothing tied to it changes in this task (see Decision 1 for the
  exact boundary).
- The `ryze` tenant slug stays (GUARDRAIL in `CLAUDE.md`). Nothing in audit
  Section A changes. This spec authorises no guardrail site.

Done means:
1. **B** — the default brand name in `app/services/branding.py`
   (`brand_name="RYZE.ai"`) is `"Greenscene"`. Confirm by reading the resolver
   which surfaces this one line changes, and list them.
2. **C, platform-facing** — the two platform welcome emails in
   `app/services/email.py` (from-name, subjects, wordmark, greeting, button
   label, reason-for-email line) and the FastAPI title in `app/main.py` say
   Greenscene. `APP_NAME` in `app/core/config.py` is renamed (it is unused;
   do not delete it in this task).
3. **C, tenant-facing** — the public booking-response pages, Zoom topic,
   calendar title and PDF download filename get a **plain rename** to
   Greenscene. Routing them through `get_branding` is the better fix and is a
   separate queued task; do not do it here. Exception: anything inside the
   SMS-consent boundary set by Decision 1.
4. **D, code** — `FROM_EMAIL` default is `hello@greenscene.io`; the CORS list
   in `app/main.py` no longer contains any `ryze.ai` or `ryzerecruiting.com`
   origin and contains the greenscene.io origins (Decision 2); the hardcoded
   links in `app/services/email.py` and the decline-page button in
   `app/api/bookings.py` use `settings.FRONTEND_URL` (href and visible text);
   the `ryze.ai` link text in the cancellation email is fixed.
5. **D, examples and comments** — `.env.example` shows `greenscene` as the
   example database name and greenscene.io in its commented production URLs
   and OAuth redirect examples. Comment-only examples in `app/` that show the
   old domain are updated where they are in a file this task already edits.
6. **Not changed, by design** — and listed in the final report as still
   present, with the reason:
   - everything in audit Section A (the slug);
   - "RYZE GROUP, Inc." wherever it appears (legal entity);
   - the SMS-consent wording per Decision 1;
   - the AI-prompt framing in audit C.1;
   - seed scripts, `manual_test_tenant_isolation.py`, `seed_cleanup.py`,
     tests' fixture addresses (`@ryze.ai` identities), applied migrations,
     `scripts/create_superadmin.py`;
   - internal names (`_ryze_defaults`, `RYZE_TENANT`, env-var names).
7. Tests that assert the old brand *string* (not the slug) are updated; tests
   that assert the slug are untouched. Add one test that the resolver's
   default `brand_name` is `"Greenscene"` and that `get_branding(None, "ryze")`
   still resolves (the slug still works under the new name).
8. Dane gets, in the final report, the exact list of things only he can do —
   nothing in this list is performed by Claude Code, and no outside service is
   logged in to or called:
   - the lines to check in his local `.env` (variable names only — do not open
     or print `.env`): at least `FROM_EMAIL`, `FRONTEND_URL`, `BACKEND_URL`;
   - Resend: verify greenscene.io as a sending domain (DNS records) before any
     mail from hello@greenscene.io can send;
   - later, at hosting time: Google and LinkedIn OAuth redirect URIs, Stripe
     webhook destination, Zoom webhook endpoint, DNS.

### Decisions to flag in the audit (do not pick — present options and wait)
**Decision 1 — where exactly the "leave Twilio alone" boundary sits.** Show
  the public consent form in `app/api/bookings.py` as it is today (the lines
  the audit lists at 776, 784, 803, 805 and anything else rendered on that
  same page) and say which lines are (i) the consent sentence itself, (ii) the
  privacy-policy link inside it, (iii) the page title and wordmark around it.
  Options:
  (a) Leave the entire consent page byte-for-byte: title, wordmark, sentence
      and link.
  (b) Leave the consent sentence and its link; rename only the page title and
      wordmark to Greenscene.
  (c) As (b), and also point the privacy link at `{FRONTEND_URL}/privacy`.
  Facts to state with the options, no recommendation: the privacy link
  currently points at `https://ryze.ai/privacy`, a domain Dane no longer
  controls; under (b) or (c) the page would show a Greenscene wordmark above a
  sentence naming "RYZE GROUP, Inc. (RYZE.ai)". This is a compliance call and
  is Dane's alone. Also say whether the frontend has a matching consent text
  (the audit mentions `BookingCard.jsx`) so the two can be kept consistent —
  read-only, do not edit the frontend.

**Decision 2 — the CORS list.** Proposed: keep the localhost entries as they
  are; remove the five old origins; add `https://greenscene.io` and
  `https://www.greenscene.io`. Say whether an API origin
  (`https://api.greenscene.io`) belongs in a CORS list at all, and whether the
  list should stay hardcoded or move to a setting (moving it is a separate
  task — just say which you would recommend later). Hosting is still TBD;
  Dane confirms the list.

**Decision 3 — the from-name on platform emails.** `"RYZE.ai <…>"` becomes
  `"Greenscene <hello@greenscene.io>"` — confirm that is how it will read, and
  state what the tenant-branded emails will show as their from-name and
  address once item 1 and item 4 land (trace it through `get_branding`).

**Decision 4 — the line `Your call with Dane at RYZE.ai is set for …`**
  (public confirmation page, shown to every tenant's contact). A plain rename
  leaves "Dane" hardcoded.
  (a) Plain rename only ("…with Dane at Greenscene…"), fix properly in the
      routing task.
  (b) Reword now to drop the name ("Your call is set for …").
  Recommend (b) — it is still display text only and stops a wrong name being
  shown — but present both.

## Related Files
- `app/services/branding.py` — default brand name
- `app/services/email.py` — two platform welcome emails; hardcoded links;
  cancellation-email link text
- `app/api/bookings.py` — public response pages, Zoom topics, decline button,
  consent form (Decision 1)
- `app/services/calendar.py` — calendar title
- `app/api/candidates.py` — PDF download filename
- `app/main.py` — FastAPI title, CORS list
- `app/core/config.py` — `APP_NAME`, `FROM_EMAIL` default
- `.env.example`
- `tests/` — brand-string assertions; one new test
- `CLAUDE.md` — only lines this task makes inaccurate ("The code still says
  RYZE", "RYZE defaults" wording in Tenant branding, the Resend-domain
  convention line). Show the edits before committing.
- `context/rebrand-audit.md` — add one dated line under the header saying
  which categories this task acted on. Do not rewrite the tables.

## Verification
- [ ] BEFORE any edit: `pytest -m "not semantic"` and
      `python audit_tenant_coverage.py` saved in History as the baseline
      (expected: the same three `tests/test_tenant_isolation.py` failures
      recorded by the bug-fix task — if the baseline differs, stop and say so).
- [ ] Audit presented first: every site re-located with its current text and
      proposed text, Decisions 1–4 with options. No code before Dane confirms.
- [ ] After: `git grep -nIi "ryze" -- app` — every remaining hit is listed in
      the report under one of the Done-means 6 reasons. No remaining hit is
      unexplained.
- [ ] After: `git grep -nI "ryze\.ai\|ryzerecruiting\.com" -- app .env.example`
      → only hits allowed by Decision 1 and fixture addresses outside `app/`.
- [ ] `git diff` touches no line in audit Section A. State how you checked.
- [ ] `pytest -m "not semantic"` → no new failures versus the baseline; the
      new test passes.
- [ ] `python audit_tenant_coverage.py` → identical to the baseline.
- [ ] App starts; `GET /docs` → 200 and its title reads Greenscene. Use a
      spare port if 8000 is in use.
- [ ] One concern per commit: display text (items 1–3), domains and config
      (items 4–5), tests, docs. `git status` clean; pushed to `origin/main`.

## Notes
- Email will not send locally after this task until greenscene.io is verified
  in Resend. That is expected and correct: the previous default sender was an
  address on a domain Dane no longer owns.
- Queued after this, each its own task: frontend narrow rebrand (from
  `greenscene_frontend/context/rebrand-audit.md`, including
  `.env.production`); route the public booking pages, Zoom topic and calendar
  title through `get_branding`; the seven `CLAUDE.md` corrections; the three
  baseline failures in `tests/test_tenant_isolation.py`; the unmatched-signup
  bucket; the possible billing-check gap; AI-prompt framing; then the
  onboarding module.
- Do not read or modify either original folder
  (`/Users/dane/code/ryzerecruiting_backend`, `…_frontend`).

## History
<!-- Keep this updated. Earliest to latest -->
- 2026-11-15 — Task drafted (Claude, chat) from `context/rebrand-audit.md` and
  a read-only look at `greenscene_backend` at `bb42bf9`. No code changed.
- 2026-11-15 — Baseline at `bb42bf9`, before any edit. `pytest -m "not
  semantic"`: 3 failed, 46 passed, 3 skipped, 3 deselected — the failures are
  the expected three in `tests/test_tenant_isolation.py`
  (`test_owning_tenant_sees_its_calls_by_date`,
  `test_owning_tenant_finds_candidate_calls`,
  `test_candidate_tool_boundary_excludes_employer_contacts`).
  `python audit_tenant_coverage.py`: 95 endpoints, 76 Safe, 19 Public/Skip,
  0 Hardcoded, 0 Needs review. Audit presented to Dane; no code changed.
- 2026-11-15 — Dane confirmed: Decision 2 (four-origin CORS list), Decision 3,
  Decision 4 (b); house-tenant comments left and reported; two comment fixes
  in site 5 made; `email.py` cancellation link text reads "our website".
- 2026-11-15 — Follow-ups recorded at Dane's direction, not part of this task:
  - The from-line does not quote the display name; a company name with a
    comma may be parsed as two addresses. Test before the first tenant sends.
  - SMS bodies carry the tenant or platform name but send from one registered
    number; the Twilio registration needs reviewing before any tenant texts.
- 2026-11-15 — Domains and config committed (`59e452e`): `FROM_EMAIL` default,
  CORS list, `FRONTEND_URL` links, `.env.example`.
- 2026-11-15 — Dane answered the two open items: Decision 1 (c); SMS wording
  change accepted.
- 2026-11-15 — Display text committed (`954a34f`): resolver default, welcome
  emails, public booking and consent pages (title and wordmark), Zoom topic,
  calendar title, PDF filename, FastAPI title, `APP_NAME`. Consent-page
  privacy link → `{FRONTEND_URL}/privacy` (`b4aad93`). New test
  `tests/test_branding_default.py` (`61d3ac6`).
- 2026-11-15 — Verification: `pytest -m "not semantic"` 3 failed (the same
  three), 52 passed, 3 skipped; `audit_tenant_coverage.py` output identical
  to baseline; `git grep "ryze\.ai\|ryzerecruiting\.com" -- app .env.example`
  → no hits; no changed line contains `"ryze"`, `RYZE_TENANT` or
  `_ryze_defaults`; app started on port 8765, `GET /docs` → 200, title
  "Greenscene API". 183 `ryze` lines remain in `app/`: 139 slug / internal
  names, 3 legal entity / consent sentence, 41 comments, docstrings and one
  log line that refer to the house tenant.
- 2026-11-15 — Dane approved the four `CLAUDE.md` edits and added one item:
  the five docstring lines FastAPI publishes on `/docs`
  (`app/api/job_orders.py:118`, four in `app/api/settings.py`) say "the
  platform" or "the firm" (`2f899da`). Code comments, the scheduler log line
  and `spaces.py:40` left. Re-checked: no changed line touches Section A;
  `pytest -m "not semantic"` 3 failed (the same three), 52 passed, 3 skipped;
  the generated OpenAPI schema contains no "ryze" in any casing. 178 `ryze`
  lines remain in `app/`: 139 slug / internal names, 3 legal entity / consent
  sentence, 36 comments, docstrings and one log line.
- 2026-11-15 — Docs committed: `CLAUDE.md` (four edits), one dated line in
  `context/rebrand-audit.md`, this History.

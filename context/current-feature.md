# Current Feature

Backend rebrand audit — classify every `ryze` occurrence (findings only, no code changes)

## Status
<!-- Not Started | In Progress | Completed -->
Completed — awaiting Dane's confirmation before archiving

## Goals
<!-- Goals & requirements -->
**Backend repo only. Findings only.** The single deliverable is a new file,
`context/rebrand-audit.md`. No file under `app/`, `alembic/`, `tests/`,
`scripts/`, no root-level script, no `.env*` file and no `CLAUDE.md` change in
this task. Nothing is renamed. Do not touch `greenscene_frontend` or either
original folder.

Context: the name on screen is becoming **Greenscene** (greenscene.io). Before
any rename, Dane needs an inventory that separates harmless display text from
configuration and from the functional tenant slug (see the GUARDRAIL section of
`CLAUDE.md`). The frontend already has this inventory:
`greenscene_frontend/context/rebrand-audit.md` (copied across 2026-11-15).
Read it first and mirror its structure, categories and table columns so the two
audits can be read side by side. Its "Appendix A" is a partial cross-reference
of this backend, done from the frontend's point of view on 2026-11-02 against
the original repo — treat it as a lead to verify, not as a finding.

Done means:
1. `context/rebrand-audit.md` exists and states its date, scope and exact
   method (the commands run), like the frontend's.
2. Every case-insensitive `ryze` occurrence in the repo is listed with file,
   line, matching text and "what breaks or changes if this is renamed".
   Search everything tracked by git plus the on-disk `scripts/` folder
   (gitignored, so say which hits are untracked). Exclude `.git/`, `venv/`,
   `__pycache__/` and the audit file itself. Also run a filename search
   (`find . -iname '*ryze*'` with the same exclusions).
3. Each occurrence is in exactly one category, using the frontend audit's six:
   - **A. TENANT-SLUG** — the literal is compared, defaulted or stored as a
     tenant identifier. For each: is the value only in code, or also in the
     database (column default, existing rows, migration data)?
   - **B. BRANDING-RESOLVED** — text that already flows through
     `get_branding()` / `app.core.config.settings`, so one default changes it.
   - **C. BRANDING-HARDCODED** — literal display text a person reads: email
     subjects and bodies, PDF templates, SMS text, AI prompts and system
     messages, API response messages, `APP_NAME`.
   - **D. DOMAIN-URL** — `ryze.ai`, `ryzerecruiting.com`, email addresses, CORS
     origins, OAuth redirect URIs, webhook URLs, CDN/storage hosts.
   - **E. INTERNAL-ID** — names no user sees: service names, database names,
     logger names, comments, variable and function names, test fixtures, seed
     data.
   - **F. DOCS** — `CLAUDE.md`, `context/`, README-type files. Counts by file
     are enough here; do not list every row of `context/CHANGELOG.md`.
4. Section A answers, with evidence, the question the frontend's Appendix A
   could only sketch: **which endpoints and background jobs behave differently
   for a tenant whose slug is not `ryze`?** List each code path, what the
   `ryze` tenant gets that others do not (billing bypass, AI-budget exemption,
   superadmin views, invite rights, default row ownership), and the file.
5. Section D separates three things for each value: (i) it is in code, (ii) it
   is only a default that `.env` overrides, (iii) it also has to change in an
   outside service (Resend verified domain, Google OAuth console, Stripe
   webhook destination, Zoom app, Twilio, DigitalOcean Spaces, DNS). For (iii)
   name the service; do not log in to or call any of them.
6. AI prompts get their own sub-table inside C: every place the model is told
   it is "RYZE" or is given recruiting-firm framing (`app/api/chat.py`,
   `app/services/ai_brief.py`, `app/services/ai_parser.py`, `app/api/webhooks.py`,
   and anywhere else found). Quote the sentence. These change product
   behaviour, not just labels.
7. A "Counts" section (per category, per top-level folder) and a "Files with
   hits in more than one category" section, as in the frontend audit.
8. A final section, **"Proposed scope for the narrow rebrand"**, that sorts the
   categories into three lists and stops there — it proposes, Dane decides:
   - safe to rename in one pass (display text with no logic attached),
   - must change before any deploy (D, and why),
   - do not touch in the rebrand (A, and anything in E that would break a
     migration, a seed script or a test if renamed).
9. `git diff --stat` for the task shows `context/rebrand-audit.md` and
   `context/current-feature.md` only.

### Decisions to flag in the audit (do not pick — present options and wait)
None before the audit is written. The audit itself ends with the proposed
scope in Done-means 8; Dane decides from that. If, while auditing, you find
something that looks like a live bug or a leaked secret, stop and report it
instead of folding it into a table.

## Related Files
- New: `context/rebrand-audit.md`
- Model to mirror: `/Users/dane/code/greenscene_frontend/context/rebrand-audit.md` (read-only)
- Starting points, not a complete list: `app/services/email.py`,
  `app/services/branding.py`, `app/services/notifications.py`,
  `app/core/config.py`, `app/core/deps.py`, `app/main.py` (CORS),
  `app/api/chat.py`, `app/api/bookings.py`, `app/api/job_orders.py`,
  `app/api/*_pdf_template.py`, `app/services/usage.py`, `.env.example`,
  `seed_full.py`, `seed_greenpath_demo.py`, `manual_test_tenant_isolation.py`,
  `alembic/versions/`

## Verification
- [x] Plan presented first: the exact search commands and exclusions, the
      raw hit count they return, and the category definitions as you read
      them. No file written before Dane confirms.
- [x] The total of the per-category counts equals the raw hit count from the
      stated command (minus the documented exclusions). Show the arithmetic.
- [x] Every row's file and line resolves: a scripted check confirms each
      listed `file:line` contains `ryze` (case-insensitive). Report the result.
- [x] The functional-slug sites listed in `CLAUDE.md`'s GUARDRAIL section all
      appear in Section A. If the audit finds slug sites the guardrail does not
      list, report them — do not edit `CLAUDE.md` in this task.
- [x] `git diff --stat` → only `context/rebrand-audit.md` and
      `context/current-feature.md`
- [x] `git status` clean; commits pushed to `origin/main`

## Notes
- A rough count on 2026-11-15 (Claude, chat; `grep -rniI ryze`, not verified
  row by row) found the heaviest files to be `manual_test_tenant_isolation.py`,
  `seed_full.py`, `app/services/email.py`, `app/api/bookings.py`,
  `app/services/branding.py` and `app/api/chat.py`. Use it only as a sanity
  check on your own count.
- Known leftover from the housekeeping task: `.env.example` still shows
  `ryzerecruiting` as the database name and ryzerecruiting.com URLs. It belongs
  in this audit (category D / E).
- Follow-ups recorded elsewhere, not part of this task: the "Session workflow"
  section of `CLAUDE.md` names sections the blank template no longer uses (both
  repos); frontend `README.md` is still Vite starter text.
- Queued after this: the narrow rebrand itself (both repos, scoped from the two
  audits), then the onboarding module.

## History
<!-- Keep this updated. Earliest to latest -->
- 2026-11-15 — Task drafted (Claude, chat) from a read-only inspection of
  `greenscene_backend` at `aca0b4e`. No code changed.
- 2026-11-15 — Audit-first step: ran the three search commands, presented the
  raw count, category definitions and plan. Dane confirmed, adding a
  "visible to an end user?" column to Section A and a "CLAUDE.md corrections
  needed" section (no `CLAUDE.md` edit).
- 2026-11-15 — Stopped before writing, per the Decisions rule: found two live
  bugs (public firm signup can claim the platform slug; 8 of 11 `notify_*`
  call sites omit `tenant_id`/`db`) and a lower-severity invite-gate
  inconsistency. Dane chose "record and continue"; fixes are separate tasks
  after this one is archived.
- 2026-11-15 — Wrote `context/rebrand-audit.md`. Raw count 543 lines in 56
  files, all tracked (`scripts/create_superadmin.py` turned out to be tracked,
  so its 5 lines are not added separately; the plan's 548 double-counted
  them). Categories: A 201, B 1, C 29, D 34, E 177, F 101 = 543. Scripted
  check: 442 of 442 line-numbered rows resolve. All 46 GUARDRAIL sites are in
  Section A. Read-only SELECTs on the local database only; `.env` not opened.

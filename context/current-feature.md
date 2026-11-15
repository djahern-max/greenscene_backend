# Current Feature

Housekeeping after the fork — make CLAUDE.md and context/ tell the truth about this repo (docs only)

## Status
<!-- Not Started | In Progress | Completed -->
In Progress — edits committed and pushed; awaiting Dane's review before archive

## Goals
<!-- Goals & requirements -->
**Backend repo only. Docs only.** No file under `app/`, `alembic/`, `tests/`,
or `scripts/` changes in this task. No rebranding of code, strings, emails,
PDFs, or config — that is the next task. Do not touch `greenscene_frontend`.

Context: on 2026-11-15 this repo was created as a copy of
`ryzerecruiting_backend` at commit `d3edd13` ("docs: archive local dev
environment task to CHANGELOG", 2026-11-05) and pushed to
`github.com/djahern-max/greenscene_backend`. The original repo and its folder
(`/Users/dane/code/ryzerecruiting_backend`) are Dane's preserved fallback and
must never be modified from here. The later November work in the original repo
(tenant restructure parts 1–3, the "Nice ATS" name) is **not** in this repo and
is not the plan here.

Product direction (Dane, 2026-11-15):
- Name on screen: **Greenscene**. Domain: **greenscene.io**.
- A recruiting **and onboarding** tool usable by any green-industry company
  (landscaping and similar). Still multi-tenant. Rye Beach Landscaping, LLC is
  the intended first real tenant.
- Onboarding (generate a new-hire package from name / address / position / rate
  of pay, employee logs in and signs electronically) is a future module, not
  part of this task.

The docs copied from the old repo are now wrong in ways that would mislead
every future session. Fix them.

Done means:
1. `CLAUDE.md` title and "What this is" describe this repo: Greenscene backend,
   forked from `ryzerecruiting_backend` at `d3edd13` on 2026-11-15, the product
   direction above, and the rule that the original repo/folder is never touched.
2. `CLAUDE.md` "Deploy & migration workflow" no longer claims a live server.
   The droplet (167.71.93.90) that hosted `api.ryze.ai` is gone and hosting is
   TBD; until a host exists a task ends at `git push origin main` plus local
   verification. See Decision 1 for what happens to the old procedure text.
3. Every other sentence in `CLAUDE.md` that depends on the droplet is corrected:
   the "deploy is not verified until the droplet's HEAD matches" clause under
   "How I want you to work", and the `journalctl -u ryze-api` tip under
   Conventions (locally the place to look is the uvicorn output).
4. `CLAUDE.md` gains a short "Local development" section stating the facts
   below. Verify each against the machine before writing it; do not copy them
   on trust:
   - repo path `/Users/dane/code/greenscene_backend`; sibling frontend at
     `/Users/dane/code/greenscene_frontend`
   - venv at `venv/`, built with Homebrew `python3.12`
   - local Postgres database `greenscene` with the `vector` extension;
     `alembic current` = `4083c0d3ba12 (head)`
   - run with `uvicorn app.main:app --reload --port 8000`
   - `scripts/` is gitignored, so `scripts/create_superadmin.py` exists on disk
     but not on GitHub
   - Redis is not installed; only OAuth and the public signup-firm /
     demo-request endpoints need it
5. `CLAUDE.md` gains an explicit guardrail: the string `ryze` is still a
   **functional tenant slug** in this codebase (`RYZE_TENANT` in
   `app/core/deps.py`, `or "ryze"` fallbacks, the budget exemption in
   `app/services/usage.py`). It must not be renamed, removed, or "cleaned up"
   as part of any task unless that task's spec says so in words. Display-text
   rebranding and slug changes are different jobs.
6. `CLAUDE.md` and `context/session-opener.md` contain no stale repo names
   (`ryzerecruiting_backend`, `ryzerecruiting_frontend`). A 2026-11-15 check
   found none in either file — confirm, and fix any that turn up. The product
   name "RYZE.ai" in the `CLAUDE.md` title and prose is covered by item 1.
   `context/CHANGELOG.md`,
   `context/dead-code-audit.md` and `context/tenant-assignment-problem.md` are
   historical records — leave their text alone (see Decision 3).
7. `git diff --stat` for the task shows only `CLAUDE.md` and files under
   `context/`.

### Decisions to flag in the audit (do not pick — present options and wait)
**Decision 1 — the old deploy procedure text.**
  (a) Keep it under a heading marked HISTORICAL, because the migration rules
      (generate locally, stop the service before `ALTER TABLE`, prefer `DELETE`
      over `TRUNCATE`) still hold wherever the app is hosted next.
  (b) Delete it; write a new procedure when hosting is chosen.
  Recommend (a).

**Decision 2 — how CLAUDE.md describes tenants.** In the old product a tenant
  was a recruiting firm with employer clients and candidates. In Greenscene a
  tenant is expected to be a green-industry company hiring for itself. The data
  model (`tenants`, `employer_profiles`, `job_orders`, `candidates`) has not
  changed.
  (a) State the new direction and record "tenant = hiring company; the
      employer_profiles layer is an open design question" as a note, changing
      no code.
  (b) Describe only what the code does today and say nothing about direction.
  Recommend (a) — but present both and wait.

**Decision 3 — `context/tenant-assignment-problem.md` and
  `context/dead-code-audit.md`.**
  (a) Leave untouched.
  (b) Add a one-line header to each: "Written for ryzerecruiting_backend before
      the 2026-11-15 fork; line numbers still valid at d3edd13."
  Recommend (b).

## Related Files
- `CLAUDE.md` — title, "What this is", "Deploy & migration workflow",
  Conventions, "How I want you to work"; new "Local development" section; new
  slug guardrail
- `context/session-opener.md` — repo names only
- `context/tenant-assignment-problem.md`, `context/dead-code-audit.md` —
  Decision 3
- Read-only, to verify facts for Done-means 4 and 5: `app/core/deps.py`,
  `app/services/usage.py`, `app/core/config.py`, `.gitignore`, `alembic/versions/`

## Verification
- [x] Audit presented: current text of each section to be changed, proposed
      replacement, Decisions 1–3 with options. No edits before Dane confirms.
- [x] `alembic current` → `4083c0d3ba12 (head)` (confirms the Local development
      section is accurate)
- [x] `grep -n "167.71.93.90\|journalctl" CLAUDE.md` → hits only inside the
      section marked historical (or none, under Decision 1b)
- [ ] `grep -rn "ryzerecruiting_" CLAUDE.md context/session-opener.md` → no output
      — NOT literally met: one hit, CLAUDE.md line 6, the intentional Origin /
      never-touch-the-original sentence that Done-means 1 requires. No stale
      names; `session-opener.md` has none. Dane to accept or reword.
- [x] `git diff --stat` → only `CLAUDE.md` and `context/` files
- [ ] `git status` clean; commits pushed to `origin/main`

## Notes
- The previous occupant of this file (Local dev environment, completed
  2026-11-05) is already archived at the top of `context/CHANGELOG.md`, so
  overwriting it lost nothing.
- Not in this task, queued next: (1) the same housekeeping for
  `greenscene_frontend`; (2) backend rebrand audit — classify every `ryze`
  occurrence as display text / configuration / tenant slug, findings only;
  (3) the narrow rebrand itself; (4) onboarding module.
- `.env.example` still shows `ryzerecruiting` as the example database name and
  ryzerecruiting.com URLs. That is configuration, not docs — leave it for the
  rebrand task and list it in the audit as a known leftover.

## History
<!-- Keep this updated. Earliest to latest -->
- 2026-11-15 — Task drafted (Claude, chat) from a read-only inspection of
  `greenscene_backend` at `d3edd13`. No code changed.
- 2026-11-15 — Audit presented (Claude Code). Found the spec's "Redis is not
  installed" fact false on this machine (Homebrew Redis 8.10.3 running as a brew
  service) and the `ryze` slug functional in more sites than the spec listed.
  Dane confirmed: Decision 1 (a), Decision 2 (a) incl. softening the
  multi-tenant sentence, Decision 3 (b) without the line-numbers clause;
  corrected Redis wording; include APScheduler line and Postgres 16 line;
  uvicorn command recorded as verified by Dane.
- 2026-11-15 — `CLAUDE.md` rewritten for the fork: title / What this is / origin
  / tenant-direction note, Local development section, `ryze` slug guardrail
  (files and counts, no line numbers), Deploy section split into live rules +
  HISTORICAL droplet procedure, journalctl tip and droplet-HEAD clause
  corrected, APScheduler line. One-line pre-fork header added to
  `context/tenant-assignment-problem.md` and `context/dead-code-audit.md`.
  `context/session-opener.md` needed no change. Verification: `alembic current`
  = `4083c0d3ba12 (head)`; IP appears only in the HISTORICAL block, `journalctl`
  nowhere; diff touches only `CLAUDE.md` and `context/`. Known leftover for the
  rebrand task: `.env.example` (ryzerecruiting DB name and URLs).

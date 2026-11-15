# Rebrand Audit — "ryze" occurrences (Backend)

> **Line numbers are as of commit `6434b11`.** The live-bugs fix task (commits `b896344`, `fb1fb01`, `52dca4e`, 2026-11-15) moved some lines in `app/api/auth.py`, `app/api/admin_invite.py`, `app/api/bookings.py`, `app/services/notifications.py` and `app/services/scheduler.py`, and fixed live bugs 1–3 below. The tables have not been re-numbered.

> **2026-11-15 — narrow rebrand acted on B, C (except the SMS-consent sentence, "RYZE GROUP, Inc." and the C.1 prompt framing) and D in `app/` and `.env.example`** (commits `59e452e`, `954a34f`, `b4aad93`, `61d3ac6`, `2f899da`). A, E, F and the D rows outside `app/` (seed, manual-test and script addresses, `spaces.py:40`) were not touched. The tables below still show the text as it was.

Date: 2026-11-15
Repo: `greenscene_backend`, working tree at commit `aca0b4e` plus this task's edit to `context/current-feature.md`.
Scope: findings only. No file under `app/`, `alembic/`, `tests/`, `scripts/`, no root-level script, no `.env*` file and not `CLAUDE.md` was changed. Nothing was renamed. `greenscene_frontend` and both original folders were not touched.
Companion: `greenscene_frontend/context/rebrand-audit.md` (same six categories, same table columns). Its Appendix A was used as a lead and re-verified here; where this audit disagrees with it, this audit was checked against the code on the date above.

**Method.** Three commands, run from the repo root:

```
git grep -niI ryze -- . ':!context/rebrand-audit.md'      # every tracked file; this file excluded
grep -rniI ryze scripts --exclude-dir=__pycache__         # scripts/ is gitignored, so searched on disk
find . -iname '*ryze*' -not -path './.git/*' -not -path './venv/*' -not -path '*/__pycache__/*'
```

- `git grep` reads tracked files only, so `.git/`, `venv/`, `__pycache__/` and the ignored `.env` are excluded by construction. `.env` was not opened at any point.
- Raw result: **543 matching lines across 56 files**, all tracked. No binary file matches. The filename search returns nothing.
- **Untracked hits: 0.** The `scripts/` search returns 5 lines, all in `scripts/create_superadmin.py`. That file is tracked (commit `0c00bcc`, present on `origin/main`) even though `.gitignore:28` ignores `scripts/`, so the first command already counts those lines and they are not added again. `scripts/` holds no other file.
- **One row per matching line** (as in the frontend audit), so the category totals sum to 543. A line with two kinds of hit is placed in the category with the higher consequence (A > D > C > B > E > F) and the note names the other.
- Every hit outside category F was read in context before it was classified. Category F is counted by file.
- Database evidence comes from read-only `SELECT`s against the local `greenscene` database (PostgreSQL 16): `information_schema.columns` for every `tenant_id` column, `SELECT tenant_id, count(*) … GROUP BY 1` on each of those tables, and `SELECT slug FROM tenants`. Result: seven tables have a `tenant_id` column (`bookings`, `candidates`, `employer_profiles`, `job_interests`, `job_orders`, `usage_events`, `users`); **none has a server-side default**; the only row in any of them is one `users` row with `tenant_id = 'ryze'` (the superadmin); `tenants` has zero rows.
- Two extra greps were used for evidence and are not part of the count: `git grep -nIiE 'recruit|staffing'` over the four AI-prompt files (section C.1), and an AST walk of every `notify_*(` call to list which keyword arguments each passes (Live bugs, item 2).

**How branding works in this repo.** `app/services/branding.py::get_branding(db, tenant_id)` returns a `TenantBranding`. For any slug other than `ryze` it reads the `tenants` row and falls back field by field to defaults; for `ryze`, for `db=None`, or for an unknown slug it returns the defaults. The defaults are one literal (`brand_name="RYZE.ai"`, `branding.py:67`), one literal signature name (`"Dane"`), and values from `app.core.config.settings` (`FROM_EMAIL`, `REPLY_TO_EMAIL`, `ADMIN_EMAIL`, `TWILIO_*`). Already on the resolver: all tenant-facing emails and SMS, the three PDF footers, the chat system prompt's firm name, and `tenant_brand_name` in `/api/auth/me`.

---

## Live bugs found

Found while auditing, reported to Dane on 2026-11-15 before this file was written, and recorded here at his direction. **None was fixed in this task**; each is its own follow-up. All three were found by reading code, not by running the app. Current exposure is nil — there is no production host, `tenants` is empty and the only user is the `ryze` superadmin — but 1 and 2 become real as soon as the app is hosted or a second tenant exists.

### 1. Public firm signup can claim the `ryze` slug — severity: high

- **Where:** `POST /api/auth/signup-firm`, slug generator `app/api/auth.py:88-101` (duplicated at `app/api/admin_invite.py:50-65`). These lines contain no `ryze` literal, so they have no table row.
- **What:** the slug is the lower-cased company name with non-alphanumerics collapsed to `_`. The only collision check is against the `tenants` table, and the `ryze` slug has no `tenants` row by design. A company name of "Ryze" (any casing or punctuation) therefore yields slug `ryze`, and the new ADMIN user is created with `tenant_id="ryze"`. Neither the endpoint nor `SignupFirmRequest` (`app/schemas/user.py:38`) has a reserved-name check. The only brakes are a rate limit (5 per hour per IP) and a honeypot field.
- **What the stranger gets:** everything in A.1 that is gated on the slug alone — the billing bypass (row `app/core/deps.py:79`), the AI-budget exemption (row `app/services/usage.py:102`), the right to onboard further firms (row `app/api/admin_invite.py:97`), and read/write access to every row owned by `ryze`, which includes every self-registered candidate and employer with no firm match (rows `app/services/tenant_resolution.py:25-56`) and every legacy row backfilled by migration `11ae0fa76851`. They do **not** get the global DB Explorer view, which also requires `is_superuser`.
- **Section A rows:** `app/core/deps.py:23, 79`; `app/services/usage.py:102`; `app/api/admin_invite.py:97`; `app/services/branding.py:89`; `app/services/tenant_resolution.py:25, 42, 55, 56`. A.1 items 1, 2, 3, 5 and 8.

### 2. Eight of eleven `notify_*` call sites send as the default tenant — severity: high once a second tenant exists

- **Where:** the call sites below. They contain no `ryze` literal, so they have no table row; the rows that carry the bug are the eleven `tenant_id: str = "ryze"` parameter defaults in `app/services/notifications.py` (Section A).
- **What:** each call omits both `tenant_id` and `db`, so the function resolves branding for `"ryze"` with `db=None`. For a booking owned by any other tenant, the message goes out under the default brand name, from the default sender address and SMS number, and the admin copy goes to the global `ADMIN_EMAIL` instead of that tenant's inbox — so one tenant's booking details are delivered to the platform inbox. `CLAUDE.md` lists this as a "known risk"; this is the list of places where it actually happens.

| call site | function | when it fires |
|---|---|---|
| `app/api/bookings.py:224` | `notify_recruiter_invite_sent` | admin sends a meeting invite |
| `app/api/bookings.py:284` | `notify_invite_declined` | invitee declines (public link) |
| `app/api/bookings.py:432` | `notify_invite_accepted_admin` | invitee accepts (public link) |
| `app/api/bookings.py:571` | `notify_candidate_confirmed` | admin confirms a candidate booking |
| `app/api/bookings.py:583` | `notify_booking_confirmed` | admin confirms an employer booking |
| `app/api/bookings.py:607` | `notify_booking_cancelled` | admin cancels a booking |
| `app/api/bookings.py:657` | `notify_candidate_booking_received` | candidate books a call |
| `app/services/scheduler.py:75` | `notify_reminder` | background job, every minute: 15-minute reminder email and SMS |

The three call sites that pass both arguments correctly: `app/api/bookings.py:169`, `app/api/bookings.py:414`, `app/api/job_orders.py:282`.

- **Section A rows:** `app/services/notifications.py:57, 102, 144, 182, 240, 300, 350, 385, 416, 466, 505`. A.1 item 10.

### 3. Invite gate is looser and stricter than its comment — severity: low

- **Where:** `app/api/admin_invite.py:96-97` (rows in Sections E and A).
- **What:** two inconsistencies on one line. (a) The comment says "RYZE superadmin only", but the dependency is `get_current_admin_user`, so any ADMIN user on the `ryze` slug passes — `is_superuser` is never checked. This is what turns bug 1 into a way to create more tenants. (b) The comparison is `current_user.tenant_id != "ryze"` with no NULL coalescing, while every other site treats a NULL `tenant_id` as `ryze`; a NULL-tenant admin gets the billing bypass and budget exemption but a 403 here.

---

## A. TENANT-SLUG

201 rows. The literal `"ryze"` (or the constant `RYZE_TENANT`, defined four times) used as a tenant identifier: definitions, comparisons, `or` fallbacks, parameter defaults, column defaults, and migration, seed and test data. `import` lines are included because they break if the constant is renamed.

**Is the value only in code, or also in the database?** Both, but thinly:

- **Column defaults are Python-side only.** `default="ryze"` on the four models is applied by SQLAlchemy at insert time. The database columns have no `DEFAULT` clause, so no migration is needed to change what new rows get.
- **Existing rows (local):** one — the superadmin in `users`. Every other tenant-scoped table is empty and `tenants` has no rows.
- **Migration data:** `alembic/versions/11ae0fa76851…` backfills NULL to `'ryze'` on five tables. On the local database it had nothing to backfill. Any database restored from the old product would carry the value in every legacy row.
- **Outside the database:** Stripe checkout metadata (`tenant_slug`) and the frontend's PostHog person property.

**Would leaving the slug alone ever show the word to a customer?** No, not as text. The slug is never interpolated into a URL, an email, an SMS, a PDF or an HTML page. It leaves the server in three places, none of them rendered to a customer: the `tenant_id` field of API JSON (`/api/auth/me`, and the candidate and job-order schemas — visible in a browser's network tab), the PostHog person property the frontend sets from it (analytics, Dane-only), and Stripe session metadata (Stripe dashboard, Dane-only). What a customer *does* see is the consequence of the slug: a user or row on the `ryze` slug gets the default brand name, which today is the string "RYZE.ai" (`app/services/branding.py:67`, category B). Change that one string and the slug can stay `ryze` indefinitely without the word reaching a customer through any resolved surface. The hardcoded surfaces in C and D are separate and do not depend on the slug.

| file | line | matching text | what breaks or changes if renamed | code only, or also in the database? | visible to an end user? |
|---|---|---|---|---|---|
| `alembic/versions/11ae0fa76851_ep16_add_tenant_id_to_bookings_backfill_.py` | 28 | `op.execute("UPDATE bookings SET tenant_id = 'ryze' WHERE tenant_id IS NULL")` | Historical migration: backfills NULL `tenant_id` to `'ryze'` on five tables. **Do not edit** — an applied migration must stay byte-stable; editing it changes what a fresh `alembic upgrade head` writes versus what existing databases hold. | Also DB: migration data. Every row that existed when this ran carries `'ryze'` | No |
| `alembic/versions/11ae0fa76851_ep16_add_tenant_id_to_bookings_backfill_.py` | 29 | `op.execute("UPDATE candidates SET tenant_id = 'ryze' WHERE tenant_id IS NULL")` | Historical migration: backfills NULL `tenant_id` to `'ryze'` on five tables. **Do not edit** — an applied migration must stay byte-stable; editing it changes what a fresh `alembic upgrade head` writes versus what existing databases hold. | Also DB: migration data. Every row that existed when this ran carries `'ryze'` | No |
| `alembic/versions/11ae0fa76851_ep16_add_tenant_id_to_bookings_backfill_.py` | 31 | `"UPDATE employer_profiles SET tenant_id = 'ryze' WHERE tenant_id IS NULL"` | Historical migration: backfills NULL `tenant_id` to `'ryze'` on five tables. **Do not edit** — an applied migration must stay byte-stable; editing it changes what a fresh `alembic upgrade head` writes versus what existing databases hold. | Also DB: migration data. Every row that existed when this ran carries `'ryze'` | No |
| `alembic/versions/11ae0fa76851_ep16_add_tenant_id_to_bookings_backfill_.py` | 33 | `op.execute("UPDATE job_orders SET tenant_id = 'ryze' WHERE tenant_id IS NULL")` | Historical migration: backfills NULL `tenant_id` to `'ryze'` on five tables. **Do not edit** — an applied migration must stay byte-stable; editing it changes what a fresh `alembic upgrade head` writes versus what existing databases hold. | Also DB: migration data. Every row that existed when this ran carries `'ryze'` | No |
| `alembic/versions/11ae0fa76851_ep16_add_tenant_id_to_bookings_backfill_.py` | 34 | `op.execute("UPDATE users SET tenant_id = 'ryze' WHERE tenant_id IS NULL")` | Historical migration: backfills NULL `tenant_id` to `'ryze'` on five tables. **Do not edit** — an applied migration must stay byte-stable; editing it changes what a fresh `alembic upgrade head` writes versus what existing databases hold. | Also DB: migration data. Every row that existed when this ran carries `'ryze'` | No |
| `analyze_webhook_logs.py` | 38 | `python analyze_webhook_logs.py --tenant ryze # assume this tenant when judging visibility` | Usage example for the `--tenant` flag. Pair with line 180. | Code only | No (developer terminal) |
| `analyze_webhook_logs.py` | 180 | `default="ryze",` | argparse default for `--tenant`: the diagnostic judges call visibility as the `ryze` tenant unless told otherwise. | Code; compared with `tenant_id` values read from the DB | No (developer terminal) |
| `analyze_webhook_logs.py` | 181 | `help="Tenant to assume for the querying recruiter (default: ryze)",` | Help text for the same flag. Pair with line 180. | Code only | No (developer terminal) |
| `app/api/admin_invite.py` | 97 | `if current_user.tenant_id != "ryze":` | **Invite gate.** `POST /api/admin/invite` returns 403 unless `tenant_id == "ryze"`. No NULL coalescing here, unlike every other site. If the slug is renamed in the data but not here, nobody can onboard a firm through this endpoint. | Code; compared with `users.tenant_id` in the DB | No |
| `app/api/billing.py` | 14 | `from app.core.deps import get_current_user, get_current_superuser, RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/api/billing.py` | 62 | `slug = user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in `_get_tenant()` (billing status / checkout lookup). If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. For `ryze` the lookup finds no `tenants` row and status is reported as `active`. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/billing.py` | 67 | `return user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in `_tenant()` (usage endpoint). If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/billing.py` | 142 | `"tenant_slug": current_user.tenant_id or RYZE_TENANT,` | Slug written into Stripe checkout `metadata.tenant_slug`; the Stripe webhook (`billing.py:196-206`) reads it back to activate the tenant. | Code; also stored in Stripe session metadata | Operator only: Stripe dashboard metadata. Not shown on the checkout page |
| `app/api/bookings.py` | 19 | `from app.core.deps import get_current_admin_tenant, RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/api/bookings.py` | 73 | `tenant_id = booking.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in `_generate_brief_background` (background task). If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. The result feeds `is_over_budget`, so a NULL-tenant booking is treated as budget-exempt. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 152 | `tenant_id=current_user.tenant_id or "ryze",` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. Here the value is written to the new booking or passed to a notify call. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 178 | `tenant_id=current_user.tenant_id or "ryze",` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. Here the value is written to the new booking or passed to a notify call. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 206 | `tenant_id=current_user.tenant_id or "ryze",` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. Here the value is written to the new booking or passed to a notify call. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 379 | `tenant_id = booking.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. Here the value is passed to candidate / employer stub creation, so it becomes the stub row's owner. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 395 | `tenant_id = booking.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. Here the value is passed to candidate / employer stub creation, so it becomes the stub row's owner. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 424 | `tenant_id=booking.tenant_id or "ryze",` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. Here the value is written to the new booking or passed to a notify call. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 468 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 641 | `tenant_id=current_user.tenant_id or "ryze",` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. Here the value is written to the new booking or passed to a notify call. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 738 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 755 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/bookings.py` | 931 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/candidates.py` | 25 | `from app.core.deps import get_current_admin_user, RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/api/candidates.py` | 73 | `return user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/candidates.py` | 90 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/candidates.py` | 145 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/candidates.py` | 233 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/chat.py` | 14 | `from app.core.deps import RYZE_TENANT, get_current_admin_tenant` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/api/chat.py` | 337 | `tenant_id: str = RYZE_TENANT, # EP16: added tenant_id param` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 363 | `db, query: str, limit: int = 5, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 404 | `db, query: str, limit: int = 5, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 445 | `db, query: str, limit: int = 5, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 483 | `def tool_get_todays_meetings(db: Session, tenant_id: str = RYZE_TENANT) -> dict:` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 514 | `tenant_id: str = RYZE_TENANT,` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 547 | `db: Session, name: str, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 580 | `db: Session, name: str, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 631 | `db: Session, job_title: str, limit: int = 5, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 637 | `db: Session, query: str, limit: int = 5, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 668 | `db: Session, name: str, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 746 | `db: Session, booking_id: int, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat.py` | 771 | `db: Session, name: str, limit: int = 5, tenant_id: str = RYZE_TENANT` | Parameter default on a chat tool function. `make_tool_dispatch(tenant_id)` (`chat.py:864-895, 1002`) always passes the caller's tenant, so the default is not reached from the endpoint. | Code only | No |
| `app/api/chat_sessions.py` | 20 | `from app.core.deps import RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/api/chat_sessions.py` | 250 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/db_explorer.py` | 12 | `from app.core.deps import get_current_superuser, RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/api/db_explorer.py` | 353 | `return user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in `_tenant()` (DB Explorer scoping for non-owners). If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/db_explorer.py` | 360 | `return (user.tenant_id or RYZE_TENANT) == RYZE_TENANT` | **Platform-owner gate.** A superuser whose slug is `ryze` (or NULL) browses, edits, deletes and exports every tenant's rows unscoped (`db_explorer.py:382, 424, 516, 552, 589`). Any other superuser is scoped to their own tenant. | Code; compared with `users.tenant_id` in the DB | Operator only: the DB Explorer shows raw `tenant_id` values to the superadmin |
| `app/api/employer_profiles.py` | 14 | `from app.core.deps import get_current_user, RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/api/employer_profiles.py` | 56 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/employer_profiles.py` | 329 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/employer_profiles.py` | 349 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/employer_profiles.py` | 375 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/employer_profiles.py` | 409 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/employer_profiles.py` | 460 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/employer_profiles.py` | 508 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/employer_profiles.py` | 638 | `tenant_id = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 86 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 131 | `tenant_id = current_user.tenant_id or "ryze" # EP16` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 243 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 306 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 322 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 343 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 363 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 389 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 409 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/job_orders.py` | 556 | `tenant_id = current_user.tenant_id or "ryze"` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/search.py` | 15 | `from app.core.deps import get_current_admin_user, get_current_admin_tenant, RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/api/search.py` | 95 | `tenant_id: str = RYZE_TENANT, # EP16: new param, defaults to "ryze"` | Parameter default on `_cosine_search`. All three callers pass `tenant_id` (lines 137, 184, 229), so the default is never used today. | Code only | No |
| `app/api/search.py` | 131 | `tenant_id = current_user.tenant_id or RYZE_TENANT # EP16` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/search.py` | 178 | `tenant_id = current_user.tenant_id or RYZE_TENANT # EP16` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/search.py` | 223 | `tenant_id = current_user.tenant_id or RYZE_TENANT # EP16` | NULL-`tenant_id` fallback in an endpoint that derives the tenant inline. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/api/webhooks.py` | 23 | `from app.core.deps import RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/api/webhooks.py` | 137 | `tenant_id = booking.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in the Zoom-transcript summary background task. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. The result feeds `is_over_budget`, so a NULL-tenant booking is summarised without a budget check. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/core/deps.py` | 23 | `RYZE_TENANT = "ryze"` | **The primary definition.** Imported by 14 files (9 in `app/api/`, 3 in `app/services/`, `backfill_signup_tenants.py`, one test). Changing the value without migrating stored rows orphans every row and user that holds `'ryze'`. | Code; the value is stored in `users.tenant_id` (1 local row) and was written by migration `11ae0fa76851` | Indirectly: `users.tenant_id` is returned by `/api/auth/me` and reaches PostHog as a person property (frontend `AuthContext.jsx:56`). Never rendered on a page |
| `app/core/deps.py` | 79 | `if tenant_slug == RYZE_TENANT:` | **Billing bypass.** `_check_tenant_access` returns early for this slug, so no trial or subscription check and never a 402. | Code; compared with `users.tenant_id` in the DB | No |
| `app/core/deps.py` | 130 | `slug = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in `get_current_tenant` / `get_current_admin_tenant`. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. A NULL-tenant user therefore also gets the billing bypass. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/core/deps.py` | 142 | `slug = current_user.tenant_id or RYZE_TENANT` | NULL-`tenant_id` fallback in `get_current_tenant` / `get_current_admin_tenant`. If the literal changes and existing rows do not, users with a NULL `tenant_id` are scoped to a bucket that holds none of the old `ryze` rows. A NULL-tenant user therefore also gets the billing bypass. | Code; the value it yields is compared with or written to `tenant_id` columns | No |
| `app/models/employer_profile.py` | 42 | `tenant_id = Column(String(100), nullable=True, default="ryze", index=True)` | Python-side column default: an `EmployerProfile` created without an explicit tenant is owned by `ryze`. | Code only today: the database column has **no** server default (`information_schema.columns.column_default` is NULL) and the local table is empty | No |
| `app/models/job_interest.py` | 14 | `RYZE_TENANT = "ryze"` | Fourth independent definition of the constant, used only for the column default on line 28. | Code only | No |
| `app/models/job_interest.py` | 28 | `tenant_id = Column(String(100), nullable=True, default=RYZE_TENANT, index=True)` | Python-side column default for `job_interests.tenant_id`. | Code only today: no server default; local table empty | No |
| `app/models/job_order.py` | 8 | `RYZE_TENANT = "ryze"` | Third independent definition of the constant. Imported by `seed_landscaping_jobs.py:49`. | Code only | No |
| `app/models/job_order.py` | 16 | `tenant_id = Column(String(100), nullable=True, default=RYZE_TENANT, index=True)` | Python-side column default for `job_orders.tenant_id`. | Code only today: no server default; local table empty | No |
| `app/models/user.py` | 32 | `tenant_id = Column(String(100), nullable=True, default="ryze", index=True)` | Python-side column default: a `User` created without an explicit tenant belongs to `ryze` and therefore gets the billing bypass and budget exemption. | Code, plus 1 existing row: `users` holds one row with `tenant_id='ryze'`. No server default on the column | Indirectly: returned as `tenant_id` by `/api/auth/me`; the frontend sends it to PostHog and uses it to gate three cosmetic surfaces (frontend audit, A.1) |
| `app/services/branding.py` | 34 | `RYZE_TENANT = "ryze"` | Second independent definition of the constant (not imported from `deps.py`). Must change in step with `deps.py:23` or the resolver and the auth layer disagree about which tenant is the platform. | Code only | No |
| `app/services/branding.py` | 86 | `tid = tenant_id or RYZE_TENANT` | NULL-slug fallback inside the resolver. | Code only | Indirectly: a NULL slug resolves to the default brand name |
| `app/services/branding.py` | 89 | `if db is None or tid == RYZE_TENANT:` | **Resolver short-circuit.** For this slug the `tenants` table is never read; hardcoded defaults are returned. A `tenants` row with slug `ryze` would be ignored (and Live bug 1 can create one). | Code; compared with the slug passed in from DB rows | Indirectly: decides that the platform tenant's messages, PDFs and chat say the default brand name |
| `app/services/email.py` | 83 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 154 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 246 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 425 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 552 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 633 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 743 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 821 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 898 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 1015 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 1094 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 1159 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 1226 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 1270 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 1305 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 1532 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/email.py` | 1605 | `branding = branding or get_branding(None, "ryze")` | Fallback when a sender is called without `branding`: resolves the platform defaults. Only reached if a caller omits the argument; `notifications.py` always passes it. | Code only | Indirectly: the email would carry the default brand name and sender |
| `app/services/embedding_service.py` | 19 | `from app.core.deps import RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/services/embedding_service.py` | 481 | `tenant_id=result.tenant_id or RYZE_TENANT,` | NULL-`tenant_id` fallback when recording embedding usage: the OpenAI cost of embedding a NULL-tenant row is booked to `ryze`, which is budget-exempt. | Code; the value is written to `usage_events.tenant_id` (NOT NULL column) | No |
| `app/services/embedding_service.py` | 548 | `tenant_id=result.tenant_id or RYZE_TENANT,` | NULL-`tenant_id` fallback when recording embedding usage: the OpenAI cost of embedding a NULL-tenant row is booked to `ryze`, which is budget-exempt. | Code; the value is written to `usage_events.tenant_id` (NOT NULL column) | No |
| `app/services/embedding_service.py` | 603 | `text, db=db, tenant_id=candidate.tenant_id or RYZE_TENANT, source="embed_sync"` | NULL-`tenant_id` fallback when recording embedding usage: the OpenAI cost of embedding a NULL-tenant row is booked to `ryze`, which is budget-exempt. | Code; the value is written to `usage_events.tenant_id` (NOT NULL column) | No |
| `app/services/embedding_service.py` | 625 | `text, db=db, tenant_id=employer.tenant_id or RYZE_TENANT, source="embed_sync"` | NULL-`tenant_id` fallback when recording embedding usage: the OpenAI cost of embedding a NULL-tenant row is booked to `ryze`, which is budget-exempt. | Code; the value is written to `usage_events.tenant_id` (NOT NULL column) | No |
| `app/services/embedding_service.py` | 647 | `text, db=db, tenant_id=job.tenant_id or RYZE_TENANT, source="embed_sync"` | NULL-`tenant_id` fallback when recording embedding usage: the OpenAI cost of embedding a NULL-tenant row is booked to `ryze`, which is budget-exempt. | Code; the value is written to `usage_events.tenant_id` (NOT NULL column) | No |
| `app/services/notifications.py` | 57 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 102 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 144 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 182 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 240 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 300 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 350 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 385 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 416 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 466 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/notifications.py` | 505 | `tenant_id: str = "ryze",` | Parameter default on a `notify_*` function. **Live bug 2:** 8 of the 11 call sites omit `tenant_id`, so this default decides the branding of real messages for every tenant. | Code only | Indirectly, and for the wrong tenant: the slug is never printed, but defaulting to it puts the default brand name, sender address and SMS number on another tenant's email/SMS |
| `app/services/tenant_resolution.py` | 9 | `from app.core.deps import RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/services/tenant_resolution.py` | 25 | `return RYZE_TENANT` | **Signup bucket.** A self-registering candidate or employer with no single matching firm is assigned to `ryze`. Follows the constant. | Code; the returned value is written to `users.tenant_id` at signup | Indirectly: becomes the user's `tenant_id` in `/api/auth/me` |
| `app/services/tenant_resolution.py` | 42 | `return RYZE_TENANT` | **Signup bucket.** A self-registering candidate or employer with no single matching firm is assigned to `ryze`. Follows the constant. | Code; the returned value is written to `users.tenant_id` at signup | Indirectly: becomes the user's `tenant_id` in `/api/auth/me` |
| `app/services/tenant_resolution.py` | 44 | `firms = {t for (t,) in rows if t and t != RYZE_TENANT}` | Excludes `ryze` when collecting the firms an email already belongs to, so a platform-bucket profile never counts as a firm match. | Code; compared with `candidates.tenant_id` / `employer_profiles.tenant_id` | No |
| `app/services/tenant_resolution.py` | 53 | `f"leaving in {RYZE_TENANT} for manual assignment"` | Warning log that interpolates the constant. | Code only | No (operator logs) |
| `app/services/tenant_resolution.py` | 55 | `return RYZE_TENANT` | **Signup bucket.** A self-registering candidate or employer with no single matching firm is assigned to `ryze`. Follows the constant. | Code; the returned value is written to `users.tenant_id` at signup | Indirectly: becomes the user's `tenant_id` in `/api/auth/me` |
| `app/services/tenant_resolution.py` | 56 | `return RYZE_TENANT` | **Signup bucket.** A self-registering candidate or employer with no single matching firm is assigned to `ryze`. Follows the constant. | Code; the returned value is written to `users.tenant_id` at signup | Indirectly: becomes the user's `tenant_id` in `/api/auth/me` |
| `app/services/usage.py` | 29 | `from app.core.deps import RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `app/services/usage.py` | 102 | `if tenant_id == RYZE_TENANT:` | **AI-budget exemption.** `is_over_budget` is always `False` for this slug, so `check_ai_budget` never returns 429 and the two background AI tasks never skip. | Code; compared with a `tenant_id` read from the DB | No |
| `audit_tenant_coverage.py` | 115 | `"RYZE_TENANT",` | Pattern the static audit searches for to flag an endpoint HARDCODED. If the slug or constant is renamed and this list is not, the audit silently stops flagging hardcoded-tenant endpoints. | Code only | No (developer terminal) |
| `audit_tenant_coverage.py` | 116 | `'"ryze"',` | Pattern the static audit searches for to flag an endpoint HARDCODED. If the slug or constant is renamed and this list is not, the audit silently stops flagging hardcoded-tenant endpoints. | Code only | No (developer terminal) |
| `audit_tenant_coverage.py` | 117 | `"'ryze'",` | Pattern the static audit searches for to flag an endpoint HARDCODED. If the slug or constant is renamed and this list is not, the audit silently stops flagging hardcoded-tenant endpoints. | Code only | No (developer terminal) |
| `backfill_signup_tenants.py` | 31 | `from app.core.deps import RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `backfill_signup_tenants.py` | 42 | `or_(User.tenant_id.is_(None), User.tenant_id == RYZE_TENANT),` | Selects candidate/employer users whose `tenant_id` is NULL or `ryze` for re-assignment to a firm. One-off maintenance script. | Code; compared with `users.tenant_id` in the DB | No |
| `scripts/create_superadmin.py` | 49 | `tenant_id="ryze",` | Creates the platform-owner user with `tenant_id="ryze"`. This is how the one row in the local database got its slug. | Also DB: writes `users.tenant_id`; the local `users` table has exactly one row and it is this one | No |
| `seed_full.py` | 163 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 174 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 211 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 277 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 292 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 314 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 341 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 367 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 393 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 417 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 442 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 468 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 490 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 514 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 539 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 563 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 586 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 609 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 633 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 657 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 680 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 704 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 730 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 756 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 778 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 802 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 827 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1247 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1263 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1280 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1296 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1311 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1327 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1342 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1358 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1373 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1389 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1406 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1422 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1437 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1453 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1468 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1484 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1499 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1513 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1526 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1540 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1555 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1569 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1582 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1594 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1609 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1627 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1642 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_full.py` | 1658 | `tenant_id="ryze",` | Seed row owned by the platform tenant. If the slug changes and the seed does not, seeded demo data lands in a tenant nobody logs in as. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `seed_greenpath_demo.py` | 149 | `admin.tenant_id = "ryze"` | Teardown sets user #1 back to `tenant_id='ryze'`. If the slug changes and this does not, the superadmin loses platform-owner status after a demo teardown. | Also DB: writes `users.tenant_id` when run | No (operator terminal) |
| `seed_landscaping_jobs.py` | 49 | `from app.models.job_order import JobOrder, RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. Imports from `app/models/job_order.py`, not `deps.py`. | Code only | No |
| `seed_landscaping_jobs.py` | 203 | `return RYZE_TENANT` | Default tenant for seeded job orders when `--tenant` is omitted. | Also DB: writes `tenant_id='ryze'` rows when the script is run | No |
| `tests/conftest.py` | 54 | `"blind_tenant": "ryze",` | Fixture: the tenant that must *not* see greenpath's calls. Rename only together with the slug or the isolation suite tests the wrong tenant. | Code; compared with `tenant_id` values in the test DB | No |
| `tests/test_signup_tenant_resolution.py` | 25 | `from app.core.deps import RYZE_TENANT` | Import of the constant. Breaks at import time only if the constant's *name* changes; a value change follows `app/core/deps.py:23`. | Code only | No |
| `tests/test_signup_tenant_resolution.py` | 60 | `assert resolve_signup_tenant(db, email, UserType.CANDIDATE) == RYZE_TENANT` | Asserts that signup resolution returns the constant. Follows the constant; breaks only if the import is renamed. | Code only | No |
| `tests/test_signup_tenant_resolution.py` | 72 | `assert result == RYZE_TENANT` | Asserts that signup resolution returns the constant. Follows the constant; breaks only if the import is renamed. | Code only | No |
| `tests/test_signup_tenant_resolution.py` | 95 | `assert resolve_signup_tenant(db, email, UserType.ADMIN) == RYZE_TENANT` | Asserts that signup resolution returns the constant. Follows the constant; breaks only if the import is renamed. | Code only | No |

### A.1 Endpoints and background jobs that behave differently for a tenant whose slug is not `"ryze"`

Each item was traced in the code on 2026-11-15.

| # | what the `ryze` tenant gets | what any other tenant gets | code path | file |
|---|---|---|---|---|
| 1 | **Billing bypass.** `_check_tenant_access` returns before looking anything up: no trial check, no subscription check, never a 402. | The `tenants` row is read; an expired trial or an inactive subscription raises 402. A slug with no `tenants` row is also let through as "legacy". | Every endpoint that depends on `get_current_tenant` or `get_current_admin_tenant`: 2 in `bookings.py`, 1 in `chat.py`, 2 in `settings.py`. | `app/core/deps.py:79` |
| 2 | **AI-budget exemption.** `is_over_budget` is always `False`. Usage is still recorded. | Month-to-date AI cost is compared with `AI_MONTHLY_BUDGET_USD` (default $8.00). Over the cap: synchronous AI endpoints return 429 `ai_usage_limit`; background AI tasks skip silently. | Synchronous (via `check_ai_budget`): `candidates.py:537, 563` (parse, parse-file), `chat.py:1157` (chat), `chat_sessions.py:251` (generate-title), `employer_profiles.py:639` (parse), `job_orders.py:557` (parse). Background: `bookings.py:74` (`_generate_brief_background`, pre-call brief), `webhooks.py:138` (Zoom transcript summary). | `app/services/usage.py:102` |
| 3 | **Invite rights.** May call `POST /api/admin/invite` to create a new tenant plus its admin user. | 403. | `invite` endpoint. See Live bugs, item 3, for who actually passes. | `app/api/admin_invite.py:97` |
| 4 | **Global DB Explorer.** A superuser on this slug browses, counts, edits, deletes and exports every tenant's rows unscoped. | A superuser on any other slug is scoped to their own tenant. | `GET /admin/db/counts`, table browse, row `PATCH`, row `DELETE`, CSV export (`db_explorer.py:382, 424, 516, 552, 589`). | `app/api/db_explorer.py:360` |
| 5 | **Hardcoded branding.** `get_branding` never reads the `tenants` table for this slug; it returns the defaults. A `tenants` row with slug `ryze` would be ignored. | The `tenants` row overrides the defaults field by field (`company_name`, `signature_name`, `from_email`, `reply_to_email`, `admin_email`, `support_email`, `twilio_*`). | Everything on the resolver: `/api/auth/me` (`api/auth.py:77, 241`, `services/auth.py:73`), PDF footers (`candidates.py:769`, `employer_profiles.py:520`, `job_orders.py:418`), chat system prompt (`chat.py:1007`), brief generation (`bookings.py:83`), `bookings.py:932`, all of `notifications.py`. | `app/services/branding.py:89` |
| 6 | **No Branding settings page.** `GET` and `PATCH /api/settings/tenant` return 404 "No tenant record for this account." | Returns and updates the tenant's own branding fields. | Not a literal comparison: a consequence of the slug having no `tenants` row. The frontend turns the 404 into "This account isn't linked to a firm". | `app/api/settings.py:118-125, 143-147` |
| 7 | **Billing status always "active".** `GET /api/billing/status` finds no `tenants` row and reports `active` with no trial dates. | Real status, trial end date and days remaining. | Same cause as item 6. Checkout metadata uses the slug (`billing.py:142`); the Stripe webhook then looks for a `tenants` row by that slug and would find none for `ryze`. | `app/api/billing.py:62, 82-90` |
| 8 | **Signup bucket.** Receives every self-registering candidate or employer whose email matches no firm, or more than one. | Receives only people whose email already has a profile in exactly that one tenant. | `POST /api/auth/register` and the OAuth signup path (`services/auth.py:42, 162`). | `app/services/tenant_resolution.py:25-56` |
| 9 | **Default row ownership.** Any `User`, `EmployerProfile`, `JobOrder` or `JobInterest` created without an explicit tenant, and any request from a user whose `tenant_id` is NULL, lands here. | Rows are owned by the tenant only when code passes it explicitly. | Model defaults (`user.py:32`, `employer_profile.py:42`, `job_order.py:16`, `job_interest.py:28`) and the 39 inline `tenant_id or …` fallbacks in `app/api/` (rows above). | several |
| 10 | **Correctly branded notifications, by accident.** The eight call sites in Live bugs item 2 default to this slug, which is right only for this tenant. | Messages for its bookings carry the default brand, sender and admin inbox. | Seven booking endpoints and the one background job, `send_upcoming_reminders` (`scheduler.py:32`, run every minute by `scheduler_runner.py:27`). | `app/services/notifications.py` (11 defaults) |
| 11 | **Embedding cost for NULL-tenant rows** is booked to this slug, which is exempt from the cap. | Cost is booked to the row's own tenant. | Embedding sync and background embed (`embedding_service.py:481, 548, 603, 625, 647`). | `app/services/embedding_service.py` |
| 12 | **Frontend cosmetics.** `/api/auth/me` returns `tenant_id`; the frontend hides "powered by RYZE" and two "working with / prepared by" lines for this slug. | Sees those three lines. | Frontend audit, A.1. Nothing in the backend differs; listed so the two audits join up. | `app/schemas/user.py:61` |

**The scheduler is the only background job with tenant-relevant behaviour** (item 10). The other background work is `BackgroundTasks` started from endpoints: the pre-call brief (item 2), the Zoom transcript summary (item 2) and embeddings (item 11).

**Observed while tracing item 1, not slug-dependent:** only five endpoint dependencies use `get_current_tenant` / `get_current_admin_tenant`; 39 other places derive the tenant inline as `current_user.tenant_id or …` and therefore never run `_check_tenant_access`. On those endpoints an expired-trial tenant would not receive a 402. This is from a grep of `Depends(…)` lines, not an endpoint-by-endpoint trace, and is recorded as a lead for a later task, not as a confirmed bug.

---

## B. BRANDING-RESOLVED

1 row. The only literal that sits *behind* the resolver.

| file | line | matching text | what breaks or changes if renamed |
|---|---|---|---|
| `app/services/branding.py` | 67 | `brand_name="RYZE.ai",` | **The one resolved brand default.** Every surface that goes through `get_branding` shows this string for the `ryze` slug, for an unknown slug, and for any tenant whose `company_name` is empty: all tenant-branded emails and SMS, the three PDF footers, the chat system prompt's firm name, and `tenant_brand_name` in `/api/auth/me`. Change this one line and all of them change. |

Related, counted elsewhere: `FROM_EMAIL = "dane@ryze.ai"` (`app/core/config.py:28`) is also a single default that moves every sender, but it is an address on a domain, so it is in D. The `get_branding(None, "ryze")` fallbacks in `email.py` and the `tenant_id: str = "ryze"` defaults in `notifications.py` are the slug, so they are in A.

---

## C. BRANDING-HARDCODED

29 rows. Text a person reads that does not go through `get_branding`. Three groups: the public booking-response pages in `bookings.py` (shown to every tenant's contacts), the two platform welcome emails at the end of `email.py` (deliberately platform-branded), and five one-offs (Zoom topic, calendar title, PDF download filename, API docs title, the unused `APP_NAME`).

| file | line | matching text | what breaks or changes if renamed |
|---|---|---|---|
| `app/api/bookings.py` | 297 | `"You've declined this meeting request. No worries — if you change your mind, reach out to RYZE.ai directly.",` | Message on the public accept/decline response page (`GET /api/bookings/respond`, `POST /respond/confirm`). Shown to any tenant's contact; not resolved through `get_branding`. |
| `app/api/bookings.py` | 338 | `topic=f"RYZE.ai — {booking.company_name or booking.employer_name}",` | Zoom meeting topic. Visible to the invitee in Zoom and in Zoom's own emails, for every tenant. |
| `app/api/bookings.py` | 348 | `"We couldn't set up the Zoom meeting. Please contact RYZE.ai directly.",` | Message on the public accept/decline response page (`GET /api/bookings/respond`, `POST /respond/confirm`). Shown to any tenant's contact; not resolved through `get_branding`. |
| `app/api/bookings.py` | 449 | `f"Your call with Dane at RYZE.ai is set for {booking.date.strftime('%B %d, %Y')} at {booking.time_slot} EST. Check your…` | Confirmation page text. Hardcodes both "Dane" and "RYZE.ai" for every tenant's contact. |
| `app/api/bookings.py` | 489 | `topic=f"RYZE.ai — {booking.company_name or booking.employer_name}",` | Zoom meeting topic. Visible to the invitee in Zoom and in Zoom's own emails, for every tenant. |
| `app/api/bookings.py` | 776 | `<title>Confirm your call — RYZE.ai</title>` | `<title>` of the public consent / response page. Browser tab text. |
| `app/api/bookings.py` | 784 | `color:#0a66c2;margin-bottom:8px;text-align:center;">RYZE.ai</div>` | Wordmark at the top of the public consent / response page. |
| `app/api/bookings.py` | 803 | `RYZE GROUP, Inc. (RYZE.ai). Message frequency varies. Message and data rates may apply.` | SMS-consent legal text (TCPA sender identity) on the public consent form. Must match the Twilio sender's registered entity; this is a compliance statement, not a label. Mirrors frontend `BookingCard.jsx:356`. |
| `app/api/bookings.py` | 848 | `Visit RYZE.ai` | Label of that button. |
| `app/api/bookings.py` | 856 | `<title>{title} — RYZE.ai</title>` | `<title>` of the public consent / response page. Browser tab text. |
| `app/api/bookings.py` | 865 | `color:{accent};margin-bottom:12px;">RYZE.ai</div>` | Wordmark at the top of the public consent / response page. |
| `app/api/candidates.py` | 920 | `"Content-Disposition": f'attachment; filename="{safe_name}_RYZE_Profile.pdf"'` | Download filename of the candidate PDF (`Content-Disposition`). The person downloading sees it; the PDF footer itself is already resolved. |
| `app/core/config.py` | 11 | `APP_NAME: str = "RYZE.ai API"` | `APP_NAME` default. **Unused** — nothing in `app/` reads `settings.APP_NAME`. Changing it changes nothing; deleting it is safe. |
| `app/main.py` | 30 | `app = FastAPI(title="RYZE.ai API")` | FastAPI title. Shown as the heading of `/docs` and in `/openapi.json`, both publicly reachable. |
| `app/services/calendar.py` | 63 | `"summary": f"RYZE.ai — {company_name or employer_name}",` | Google Calendar event title. Visible on the calendar that `GOOGLE_CALENDAR_ID` points at (the admin's), for every tenant's booking. Not resolved through `get_branding`. |
| `app/services/email.py` | 1373 | `"from": f"RYZE.ai <{settings.FROM_EMAIL}>",` | `from` display name of a platform welcome email (invite / self-serve signup). Deliberately not tenant-branded: the platform is speaking. |
| `app/services/email.py` | 1375 | `"subject": "You're invited to RYZE.ai — your 60-day trial starts today",` | Subject line of a platform welcome email. |
| `app/services/email.py` | 1378 | `<h1 style="color:#0a66c2;margin-bottom:8px;">RYZE.ai</h1>` | Wordmark heading in a platform welcome email. |
| `app/services/email.py` | 1381 | `<h2 style="color:#111827;margin-bottom:4px;">Welcome to RYZE.ai, {full_name}! 🎉</h2>` | Greeting line in a platform welcome email. |
| `app/services/email.py` | 1419 | `Log In to RYZE.ai →` | Login button label in a platform welcome email. |
| `app/services/email.py` | 1430 | `© 2026 RYZE GROUP, Inc. · Manchester, NH<br />` | Footer legal line naming the legal entity ("RYZE GROUP, Inc."). An entity name, not a product name: changing it is a legal decision. |
| `app/services/email.py` | 1431 | `You received this email because you were invited to RYZE.ai.` | Footer reason-for-email line in a platform welcome email. |
| `app/services/email.py` | 1456 | `"from": f"RYZE.ai <{settings.FROM_EMAIL}>",` | `from` display name of a platform welcome email (invite / self-serve signup). Deliberately not tenant-branded: the platform is speaking. |
| `app/services/email.py` | 1458 | `"subject": "Welcome to RYZE.ai — your 60-day trial starts today",` | Subject line of a platform welcome email. |
| `app/services/email.py` | 1461 | `<h1 style="color:#0a66c2;margin-bottom:8px;">RYZE.ai</h1>` | Wordmark heading in a platform welcome email. |
| `app/services/email.py` | 1464 | `<h2 style="color:#111827;margin-bottom:4px;">Welcome to RYZE.ai, {full_name}! 🎉</h2>` | Greeting line in a platform welcome email. |
| `app/services/email.py` | 1497 | `Log In to RYZE.ai →` | Login button label in a platform welcome email. |
| `app/services/email.py` | 1507 | `© 2026 RYZE GROUP, Inc. · Manchester, NH<br />` | Footer legal line naming the legal entity ("RYZE GROUP, Inc."). An entity name, not a product name: changing it is a legal decision. |
| `app/services/email.py` | 1508 | `You received this email because you signed up for RYZE.ai.` | Footer reason-for-email line in a platform welcome email. |

### C.1 AI prompts

**No AI prompt contains the word.** The spec expected the model to be told it is "RYZE"; that was already fixed before the fork. The chat system prompt takes its firm name from the resolver, and the other prompts never name a brand. The four `ryze` hits in the prompt files are comments or docstrings and are listed in E (`app/api/chat.py:915`, `app/api/webhooks.py:86`, `app/services/ai_brief.py:6, 209`); `app/services/ai_parser.py` has no hit.

What remains is **recruiting-firm framing**, which changes product behaviour for a tenant that is a company hiring for itself. These lines have no `ryze` literal, so they are **not counted** in this section's 29 rows or in the 543 total. Found with `git grep -nIiE 'recruit|staffing'` over the four files, prompt lines only.

| file | line | sentence given to the model | what it does to behaviour |
|---|---|---|---|
| `app/api/chat.py` | 937 | `You are {firm} Intelligence — the AI assistant for {firm}, a recruiting firm.` | System prompt, every chat turn. `{firm}` is resolved; "a recruiting firm" is not. Also fixes the product name as "{firm} Intelligence". |
| `app/api/chat.py` | 931 | `{firm} recruits across whatever industries, roles, and seniority levels appear in its own data. Do not assume a vertical.` | Used when the tenant has no `specialty`. Frames the tenant as recruiting across industries for others. |
| `app/api/chat.py` | 947 | `Respond in the voice of an experienced recruiter at this firm.` | Voice instruction. |
| `app/api/chat.py` | 949 | `Write as if a senior recruiter is replying to a colleague — confident, specific, and conversational.` | Voice instruction. |
| `app/api/chat.py` | 961 | `Never volunteer doubts about a record's provenance unless the recruiter asks directly.` | Names the user as "the recruiter". |
| `app/api/chat.py` | 84, 204, 283 | Tool descriptions: `…if the recruiter needs the…`, `Use when the recruiter asks about a specific named candidate.`, `Only call this when the recruiter asks about the detail of what was…` | Tool-selection hints; the user is "the recruiter". |
| `app/api/webhooks.py` | 152 | `You are summarizing a recruiting call transcript for a recruiter's CRM.` | Background Zoom-transcript summary. Decides what the summary treats as important. |
| `app/services/ai_brief.py` | 97, 119 | `You are an expert recruiting researcher preparing a pre-call brief for a recruiter at {brand_name}, who places candidates across a variety of industries and roles.` | Pre-call brief (two variants). `{brand_name}` is resolved; "places candidates" describes an agency, not an employer. |
| `app/services/ai_parser.py` | 55 | `You are an expert recruiter reviewing a candidate profile or resume.` | Candidate / resume parser. |
| `app/services/ai_parser.py` | 66, 80 | `…2-3 sentences from a recruiter's perspective…`; `…the most valuable field for recruiting purposes` | Field instructions inside the same parser prompt. |
| `app/services/ai_parser.py` | 90 | `You are an expert recruiter reviewing a job description or job posting from any industry.` | Job-order parser. |
| `app/services/ai_parser.py` | 132 | `You are an expert recruiter analyzing a company or job posting for prospecting purposes.` | Employer-profile parser. "Prospecting" and line 144's `talking points a recruiter should use when reaching out to this company` assume the employer is a sales target, which has no meaning when the tenant *is* the employer. |

All generation calls use Anthropic models (`claude-sonnet-4-6`; `claude-haiku-4-5-20251001` for chat titles); embeddings use OpenAI `text-embedding-3-small`. That matches the rule in `CLAUDE.md`.

---

## D. DOMAIN-URL

34 rows. `ryze.ai` and `ryzerecruiting.com` hosts, addresses on them, CORS origins, redirect URIs and the Spaces bucket host. The three right-hand columns answer, for each value: (i) is it in code, (ii) is it only a default that `.env` overrides, (iii) which outside service also has to change. No outside service was logged in to or called.

| file | line | matching text | what breaks or changes if renamed | (i) in code | (ii) default that `.env` overrides | (iii) outside service that must also change |
|---|---|---|---|---|---|---|
| `.env.example` | 27 | `# - Production: https://ryzerecruiting.com/api/auth/oauth/google/callback` | Comment listing the Google OAuth redirect URIs for the old production domain. The real URI is built from `BACKEND_URL` (`app/api/auth.py:249`). | No (comment) | Yes: `BACKEND_URL` | Google OAuth console (authorised redirect URIs) |
| `.env.example` | 28 | `# - Production (www): https://www.ryzerecruiting.com/api/auth/oauth/google/callback` | Comment listing the Google OAuth redirect URIs for the old production domain. The real URI is built from `BACKEND_URL` (`app/api/auth.py:249`). | No (comment) | Yes: `BACKEND_URL` | Google OAuth console (authorised redirect URIs) |
| `.env.example` | 40 | `# - Production: https://ryzerecruiting.com/api/auth/oauth/linkedin/callback` | Comment listing the LinkedIn OAuth redirect URIs for the old production domain. The real URI is built from `BACKEND_URL` (`app/api/auth.py:314,351`). | No (comment) | Yes: `BACKEND_URL` | LinkedIn developer app (redirect URLs) |
| `.env.example` | 41 | `# - Production (www): https://www.ryzerecruiting.com/api/auth/oauth/linkedin/callback` | Comment listing the LinkedIn OAuth redirect URIs for the old production domain. The real URI is built from `BACKEND_URL` (`app/api/auth.py:314,351`). | No (comment) | Yes: `BACKEND_URL` | LinkedIn developer app (redirect URLs) |
| `.env.example` | 55 | `# FRONTEND_URL=https://ryzerecruiting.com` | Commented-out production value for `FRONTEND_URL` / `BACKEND_URL`. These two settings drive every OAuth redirect, the Stripe success/cancel URLs and every dashboard or accept/decline link in emails. | No (comment) | Yes: this *is* the `.env` value | DNS for the new domain; Stripe (success/cancel URLs follow `FRONTEND_URL`) |
| `.env.example` | 56 | `# BACKEND_URL=https://ryzerecruiting.com` | Commented-out production value for `FRONTEND_URL` / `BACKEND_URL`. These two settings drive every OAuth redirect, the Stripe success/cancel URLs and every dashboard or accept/decline link in emails. | No (comment) | Yes: this *is* the `.env` value | DNS for the new domain; Stripe (success/cancel URLs follow `FRONTEND_URL`) |
| `.env.example` | 58 | `# If using /api prefix: BACKEND_URL=https://ryzerecruiting.com` | Commented-out production value for `FRONTEND_URL` / `BACKEND_URL`. These two settings drive every OAuth redirect, the Stripe success/cancel URLs and every dashboard or accept/decline link in emails. | No (comment) | Yes: this *is* the `.env` value | DNS for the new domain; Stripe (success/cancel URLs follow `FRONTEND_URL`) |
| `.env.example` | 59 | `# If using api subdomain: BACKEND_URL=https://api.ryzerecruiting.com` | Commented-out production value for `FRONTEND_URL` / `BACKEND_URL`. These two settings drive every OAuth redirect, the Stripe success/cancel URLs and every dashboard or accept/decline link in emails. | No (comment) | Yes: this *is* the `.env` value | DNS for the new domain; Stripe (success/cancel URLs follow `FRONTEND_URL`) |
| `app/api/bookings.py` | 805 | `<a href="https://ryze.ai/privacy" target="_blank" style="color:#0a66c2;">Privacy Policy</a></span>` | Privacy Policy link on the public consent form, pointing at a domain no longer controlled. Dead link inside a legal consent. | Yes (hardcoded) | No | DNS; Twilio A2P 10DLC campaign (registered privacy-policy URL) |
| `app/api/bookings.py` | 844 | `<a href="https://ryzerecruiting.com"` | "Visit" button on the decline page, hardcoded to the old marketing domain instead of `FRONTEND_URL`. | Yes (hardcoded) | No | DNS |
| `app/core/config.py` | 28 | `FROM_EMAIL: str = "dane@ryze.ai"` | `FROM_EMAIL` default. This is the sender for every email (via `get_branding` → `from_email`) and for the two platform welcome emails. `.env.example` has no `FROM_EMAIL` line, so a fresh setup silently gets this default. Also a B-type value: one change moves every sender. | Yes (default) | Yes: `FROM_EMAIL` | Resend (verified sending domain); DNS (SPF/DKIM records for the new domain) |
| `app/main.py` | 43 | `"https://ryze.ai",` | CORS allowed origin. A frontend served from any other domain is blocked by the browser until its origin is added here. Hardcoded: there is no setting for it. | Yes (hardcoded list) | No | DNS (the new frontend origin has to exist before it can be listed) |
| `app/main.py` | 44 | `"https://www.ryze.ai",` | CORS allowed origin. A frontend served from any other domain is blocked by the browser until its origin is added here. Hardcoded: there is no setting for it. | Yes (hardcoded list) | No | DNS (the new frontend origin has to exist before it can be listed) |
| `app/main.py` | 45 | `"https://api.ryze.ai",` | CORS allowed origin. A frontend served from any other domain is blocked by the browser until its origin is added here. Hardcoded: there is no setting for it. | Yes (hardcoded list) | No | DNS (the new frontend origin has to exist before it can be listed) |
| `app/main.py` | 46 | `"https://ryzerecruiting.com",` | CORS allowed origin. A frontend served from any other domain is blocked by the browser until its origin is added here. Hardcoded: there is no setting for it. | Yes (hardcoded list) | No | DNS (the new frontend origin has to exist before it can be listed) |
| `app/main.py` | 47 | `"https://www.ryzerecruiting.com",` | CORS allowed origin. A frontend served from any other domain is blocked by the browser until its origin is added here. Hardcoded: there is no setting for it. | Yes (hardcoded list) | No | DNS (the new frontend origin has to exist before it can be listed) |
| `app/services/branding.py` | 52 | `# Resend "from" header, e.g. 'Acme Recruiting <dane@ryze.ai>'` | Comment showing an example `from` header with the old address. Nothing at runtime. | No (comment) | n/a | None |
| `app/services/email.py` | 466 | `Visit <a href="{settings.FRONTEND_URL}" style="color: #0a66c2;">ryze.ai</a>` | Link *text* in the cancellation email reads `ryze.ai` while the `href` is `FRONTEND_URL`. Sent to every tenant's contact, inside an otherwise tenant-branded email. | Yes (hardcoded text) | No (the href is; the visible text is not) | None for the text itself |
| `app/services/email.py` | 1395 | `<a href="https://ryze.ai/auth" style="color:#0a66c2;font-weight:600;">https://ryze.ai/auth</a>` | Login link (href and text) in a platform welcome email, hardcoded to the old domain instead of `FRONTEND_URL`. A new firm's first email would point at a site no longer controlled. | Yes (hardcoded) | No | DNS |
| `app/services/email.py` | 1416 | `<a href="https://ryze.ai/auth"` | Login button href in a platform welcome email. Same problem as the link above it. | Yes (hardcoded) | No | DNS |
| `app/services/email.py` | 1479 | `<a href="https://ryze.ai/auth" style="color:#0a66c2;font-weight:600;">https://ryze.ai/auth</a>` | Login link (href and text) in a platform welcome email, hardcoded to the old domain instead of `FRONTEND_URL`. A new firm's first email would point at a site no longer controlled. | Yes (hardcoded) | No | DNS |
| `app/services/email.py` | 1494 | `<a href="https://ryze.ai/auth"` | Login button href in a platform welcome email. Same problem as the link above it. | Yes (hardcoded) | No | DNS |
| `app/services/spaces.py` | 40 | `# → "https://ryzerecruiting.nyc3.cdn.digitaloceanspaces.com/candidates/42/photo/photo.jpg"` | Docstring example showing the old Spaces bucket host. The real host comes from `DO_SPACES_BUCKET` / `DO_SPACES_CDN_BASE` in `.env`. Mirrors the three hardcoded bucket URLs in frontend `Landing.jsx:9-13`. | No (comment) | Yes: `DO_SPACES_BUCKET`, `DO_SPACES_CDN_BASE` | DigitalOcean Spaces (bucket name); stored file URLs already saved in DB rows keep the old host |
| `manual_test_tenant_isolation.py` | 30 | `BASE_URL=https://api.ryze.ai RYZE_EMAIL=dane@ryze.ai RYZE_PASSWORD=secret python test_tenant_isolation.py` | Usage example with the old API host and admin address. Docstring only. | No (docstring) | Yes: `BASE_URL`, `RYZE_EMAIL` env vars | None |
| `manual_test_tenant_isolation.py` | 39 | `RYZE_EMAIL = os.getenv("RYZE_EMAIL", "dane@ryze.ai")` | Default login address for the manual test's platform admin. The script fails to log in unless a user with this email exists or `RYZE_EMAIL` is set. | Yes (default) | Yes: `RYZE_EMAIL` env var | None |
| `scripts/create_superadmin.py` | 10 | `python scripts/create_superadmin.py --email you@ryze.ai` | Usage example address. Nothing is sent. | Yes (docstring) | No | None |
| `seed_cleanup.py` | 22 | `"test_employer@ryze.ai",` | Seed test-account address. Must stay identical to `seed_full.py:48-49` or cleanup stops finding the rows it seeded. | Yes | No | None (never mailed; fixture identity only) |
| `seed_cleanup.py` | 23 | `"test_candidate@ryze.ai",` | Seed test-account address. Must stay identical to `seed_full.py:48-49` or cleanup stops finding the rows it seeded. | Yes | No | None (never mailed; fixture identity only) |
| `seed_full.py` | 16 | `Employer : test_employer@ryze.ai / TestPassword123` | Seed test-account address (login identity or a note that quotes it). Must stay identical to `seed_cleanup.py:22-23` and to what `manual_test` users type. | Yes | No | None (never mailed; fixture identity only) |
| `seed_full.py` | 17 | `Candidate: test_candidate@ryze.ai / TestPassword123` | Seed test-account address (login identity or a note that quotes it). Must stay identical to `seed_cleanup.py:22-23` and to what `manual_test` users type. | Yes | No | None (never mailed; fixture identity only) |
| `seed_full.py` | 48 | `TEST_EMPLOYER_EMAIL = "test_employer@ryze.ai"` | Seed test-account address (login identity or a note that quotes it). Must stay identical to `seed_cleanup.py:22-23` and to what `manual_test` users type. | Yes | No | None (never mailed; fixture identity only) |
| `seed_full.py` | 49 | `TEST_CANDIDATE_EMAIL = "test_candidate@ryze.ai"` | Seed test-account address (login identity or a note that quotes it). Must stay identical to `seed_cleanup.py:22-23` and to what `manual_test` users type. | Yes | No | None (never mailed; fixture identity only) |
| `seed_full.py` | 201 | `"Test employer profile linked to test_employer@ryze.ai login."` | Seed test-account address (login identity or a note that quotes it). Must stay identical to `seed_cleanup.py:22-23` and to what `manual_test` users type. | Yes | No | None (never mailed; fixture identity only) |
| `seed_full.py` | 233 | `notes=mark("Test candidate account — linked to test_candidate@ryze.ai login."),` | Seed test-account address (login identity or a note that quotes it). Must stay identical to `seed_cleanup.py:22-23` and to what `manual_test` users type. | Yes | No | None (never mailed; fixture identity only) |

**Outside services, by name, and what in this repo points at each:**

| service | what has to change there | driven from |
|---|---|---|
| DNS | Records for the new frontend and API hosts; SPF/DKIM for the mail domain. | `FRONTEND_URL`, `BACKEND_URL` (`.env`), CORS list (`app/main.py:43-47`), hardcoded links (`bookings.py:805, 844`, `email.py:1395, 1416, 1479, 1494`) |
| Resend | A verified sending domain for whatever `FROM_EMAIL` becomes. Until then mail can only send from the old verified domain. | `FROM_EMAIL` (`app/core/config.py:28`, `.env`) |
| Google OAuth console | Authorised redirect URI `{BACKEND_URL}/api/auth/oauth/google/callback`. | `BACKEND_URL` (`app/api/auth.py:249`) |
| LinkedIn developer app | Redirect URL `{BACKEND_URL}/api/auth/oauth/linkedin/callback`. | `BACKEND_URL` (`app/api/auth.py:314, 351`) |
| Stripe | Webhook destination `{API host}/api/billing/webhook`; product name shown at checkout. Success and cancel URLs follow `FRONTEND_URL` automatically. | No `ryze` literal in code; the frontend CHANGELOG records the old destination as `ryze-production` → `https://api.ryze.ai/…` |
| Zoom app | Webhook endpoint `{API host}/api/webhooks/zoom`. | No `ryze` literal in code (`app/api/webhooks.py:198`) |
| Twilio | A2P 10DLC brand and campaign are registered to a legal entity and a privacy-policy URL; the consent text and link at `bookings.py:803, 805` must match what is registered. | Hardcoded |
| DigitalOcean Spaces | Bucket name appears in every stored file URL. Renaming the bucket breaks URLs already saved in rows; the code itself reads the bucket from `.env`. | `DO_SPACES_BUCKET`, `DO_SPACES_CDN_BASE` (`.env`) |

---

## E. INTERNAL-ID

177 rows. Names and text no customer sees: comments, docstrings, function and variable names, developer-script banners, old service names, the example database name. The two largest blocks are `manual_test_tenant_isolation.py` (local variable names and terminal labels) and docstrings in `app/`.

Two things in this table are not purely internal: endpoint docstrings are published in `/docs` and `/openapi.json` (`app/api/job_orders.py:118`, `app/api/settings.py:115, 116, 140`), and `audit_tenant_coverage.py:433` prints advice that recommends adding more slug fallbacks.

| file | line | matching text | what breaks or changes if renamed |
|---|---|---|---|
| `.env.example` | 8 | `DATABASE_URL=postgresql://postgres:password@localhost:5432/ryzerecruiting` | Example database name. The real local database is `greenscene` (CLAUDE.md); the example is stale. Changing it changes nothing at runtime. |
| `.gitignore` | 20 | `RYZE_CREDENTIALS_ACTUAL.md` | Ignore rule for a credentials note from the old server. The file is not on disk and not tracked. Removing the rule is harmless; keeping it costs nothing. |
| `analyze_webhook_logs.py` | 2 | `analyze_webhook_logs.py — RYZE Intelligence recollection diagnostic` | Docstring of a developer diagnostic script. Nothing. |
| `analyze_webhook_logs.py` | 9 | `per meeting, *exactly* why RYZE Intelligence would or would not "remember"` | Docstring of a developer diagnostic script. Nothing. |
| `analyze_webhook_logs.py` | 203 | `print(f"RYZE Intelligence recollection diagnostic")` | Banner printed by a developer script. Nothing. |
| `app/api/admin_invite.py` | 96 | `# Restrict to RYZE superadmin only` | Comment. Says "superadmin only" but the dependency is `get_current_admin_user` — see Live bugs, item 3. |
| `app/api/billing.py` | 84 | `# No tenant row — legacy account or RYZE itself` | Comment explaining the no-`tenants`-row case. Nothing. |
| `app/api/chat.py` | 915 | `1. The firm identity and vertical belong to the tenant, not to RYZE.` | Docstring of `build_system_prompt`. Nothing. (The prompt itself has no hit — see C.1.) |
| `app/api/chat_sessions.py` | 3 | `Chat session persistence endpoints — RYZE Intelligence history.` | Module docstring. Nothing. |
| `app/api/db_explorer.py` | 19 | `# (RYZE's own superadmin, _is_platform_owner()), who gets an unscoped, global` | Comment / docstring describing the platform-owner view. Nothing. |
| `app/api/db_explorer.py` | 201 | `# RYZE branding via get_branding()'s per-field default. Superuser beware.` | Comment / docstring describing the platform-owner view. Nothing. |
| `app/api/db_explorer.py` | 357 | `"""RYZE's own superadmin (tenant_id == 'ryze') gets a global, unscoped view` | Comment / docstring describing the platform-owner view. Nothing. |
| `app/api/job_order_pdf_template.py` | 4 | `Banner from linked employer, logo overlapping, two-column body, RYZE footer.` | Stale docstring. The footer is `{footer_brand}`, filled from `get_branding` at `app/api/job_orders.py:526`. |
| `app/api/job_orders.py` | 118 | `and engage RYZE to proceed.` | Endpoint docstring. FastAPI publishes endpoint docstrings in `/docs` and `/openapi.json`, which are enabled (no `docs_url=None` in `app/main.py`), so this sentence is readable by anyone who opens the API docs. |
| `app/api/settings.py` | 79 | `Intentionally EXCLUDED (platform-owned — only RYZE controls these):` | Docstring. Lines 115, 116 and 140 are endpoint docstrings, so they are published in `/docs`. |
| `app/api/settings.py` | 115 | `NULL fields mean "use the RYZE default for this field" — the UI should` | Docstring. Lines 115, 116 and 140 are endpoint docstrings, so they are published in `/docs`. |
| `app/api/settings.py` | 116 | `show them as empty inputs with the RYZE fallback as placeholder text.` | Docstring. Lines 115, 116 and 140 are endpoint docstrings, so they are published in `/docs`. |
| `app/api/settings.py` | 120 | `# RYZE's own admins resolve to slug "ryze", which intentionally has no` | Comment documenting a real behaviour: the `ryze` slug has no `tenants` row, so `GET /api/settings/tenant` returns 404 for it (A.1, item 6). The code on the next lines is not slug-aware; it reacts to the missing row. |
| `app/api/settings.py` | 140 | `normalized to NULL, which restores the RYZE fallback for that field.` | Docstring. Lines 115, 116 and 140 are endpoint docstrings, so they are published in `/docs`. |
| `app/api/settings.py` | 162 | `# RYZE fallback rather than sending an empty "from" address.` | Comment. Nothing. |
| `app/api/webhooks.py` | 86 | `RYZE Intelligence can find them by what was said on the call.` | Docstring. Nothing. |
| `app/core/config.py` | 56 | `# separate from the $20/mo subscription price (revenue). The 'ryze' tenant` | Comment describing the budget exemption. Nothing. |
| `app/core/deps.py` | 22 | `# Default tenant slug — RYZE Recruiting's own data` | Comment / docstring. Nothing. |
| `app/core/deps.py` | 74 | `RYZE's own tenant slug bypasses billing checks — it is always active.` | Comment / docstring. Nothing. |
| `app/core/deps.py` | 120 | `Falls back to RYZE_TENANT for legacy rows where tenant_id is NULL.` | Comment / docstring. Nothing. |
| `app/models/candidate.py` | 74 | `# Transcript copied from the linked booking's Zoom call so RYZE` | Comment. Nothing. |
| `app/models/employer_profile.py` | 41 | `# Multi-tenancy scaffold (NULL = RYZE.ai)` | Comment. Nothing. |
| `app/models/job_order.py` | 15 | `# Multi-tenancy — 'ryze' = RYZE Recruiting (default tenant)` | Comment. Nothing. |
| `app/models/tenant.py` | 29 | `# ── White-label sender overrides (nullable → fall back to RYZE globals) ──` | Comment describing the fallback-to-defaults design. Nothing. |
| `app/models/tenant.py` | 30 | `# Resolved by app/services/branding.py. Leave NULL to use RYZE's shared` | Comment describing the fallback-to-defaults design. Nothing. |
| `app/models/tenant.py` | 31 | `# sender — a tenant with all-null overrides behaves exactly like RYZE today.` | Comment describing the fallback-to-defaults design. Nothing. |
| `app/models/tenant.py` | 39 | `# NULL to ride on RYZE's shared number + A2P campaign.` | Comment describing the fallback-to-defaults design. Nothing. |
| `app/models/user.py` | 31 | `# Multi-tenancy — which firm this user belongs to ('ryze' = RYZE Recruiting)` | Comment. Nothing. |
| `app/services/ai_brief.py` | 6 | `on behalf of the calling tenant's branded firm name, not RYZE.ai specifically,` | Docstring saying the brand name is resolved by the caller. Nothing. |
| `app/services/ai_brief.py` | 209 | `generated (the tenant's branded name, not RYZE.ai) — resolve it via` | Docstring saying the brand name is resolved by the caller. Nothing. |
| `app/services/auth.py` | 35 | `# RYZE_TENANT, so importing tenant_resolution (which imports` | Comment explaining a lazy import. Names the constant; nothing breaks. |
| `app/services/auth.py` | 36 | `# RYZE_TENANT from deps) at module load time would cycle back here.` | Comment explaining a lazy import. Names the constant; nothing breaks. |
| `app/services/branding.py` | 7 | `belong to the *firm the message is about*, not to RYZE globally.` | Module / function docstring. Nothing. |
| `app/services/branding.py` | 10 | `back, individually, to RYZE's global defaults (app.core.config.settings).` | Module / function docstring. Nothing. |
| `app/services/branding.py` | 12 | `like RYZE does today — this layer is regression-safe by construction, and is` | Module / function docstring. Nothing. |
| `app/services/branding.py` | 13 | `safe to call with db=None or an unknown tenant (you get RYZE defaults).` | Module / function docstring. Nothing. |
| `app/services/branding.py` | 18 | `every tenant leaves the twilio_* columns NULL and rides on RYZE's number.` | Module / function docstring. Nothing. |
| `app/services/branding.py` | 21 | `verifies its own domain, leave from_email NULL — messages then send from RYZE's` | Module / function docstring. Nothing. |
| `app/services/branding.py` | 40 | `brand_name: str # display name: "RYZE.ai" or "Acme Recruiting"` | Comment on a dataclass field. Nothing. |
| `app/services/branding.py` | 64 | `def _ryze_defaults(tenant_id: str) -> TenantBranding:` | Function name `_ryze_defaults`. Rename both lines together. |
| `app/services/branding.py` | 80 | `"""Resolve branding for a tenant; every field falls back to RYZE globals.` | Module / function docstring. Nothing. |
| `app/services/branding.py` | 87 | `defaults = _ryze_defaults(tid)` | Function name `_ryze_defaults`. Rename both lines together. |
| `app/services/email.py` | 1353 | `# Platform email — sent by RYZE itself when onboarding a new firm.` | Comment / docstring stating these emails are deliberately platform-branded. Nothing. |
| `app/services/email.py` | 1448 | `chose their own at signup). Hardcoded to RYZE branding intentionally:` | Comment / docstring stating these emails are deliberately platform-branded. Nothing. |
| `app/services/email.py` | 1449 | `this onboards a new firm onto RYZE.ai itself, not a tenant emailing` | Comment / docstring stating these emails are deliberately platform-branded. Nothing. |
| `app/services/email.py` | 1530 | `"""Notify RYZE's admin inbox that someone requested a demo from the` | Comment / docstring stating these emails are deliberately platform-branded. Nothing. |
| `app/services/email.py` | 1531 | `landing page. Always RYZE-side — no tenant exists yet for the requester."""` | Comment / docstring stating these emails are deliberately platform-branded. Nothing. |
| `app/services/embedding_service.py` | 3 | `Embedding service for RYZE.ai RAG / PGVector functionality.` | Module docstring. Nothing. |
| `app/services/notifications.py` | 27 | `no Twilio config resolved (null tenant creds with no RYZE fallback)."""` | Comment / docstring. Nothing. |
| `app/services/notifications.py` | 199 | `# Admin copy — routed to this tenant's admin inbox (falls back to RYZE's` | Comment / docstring. Nothing. |
| `app/services/scheduler_runner.py` | 4 | `Started and managed by systemd (ryze-scheduler.service).` | Docstring naming the old systemd unit `ryze-scheduler.service`. The server is gone; a future unit can take any name. |
| `app/services/scheduler_runner.py` | 24 | `logger.info("RYZE Scheduler starting...")` | Log line at scheduler start. Operator logs only. |
| `app/services/tenant_resolution.py` | 19 | `their email. No prior firm association → RYZE's own book (RYZE_TENANT).` | Docstring / comment describing the signup bucket. Nothing. |
| `app/services/tenant_resolution.py` | 50 | `# one tenant. Don't silently pick a winner; leave in ryze and flag.` | Docstring / comment describing the signup bucket. Nothing. |
| `app/services/usage.py` | 16 | `Imports nothing from app.core.deps except the RYZE_TENANT constant — this` | Docstring. Nothing. |
| `app/services/usage.py` | 101 | `"""RYZE_TENANT is always exempt. Never raises — fails open (False) on error."""` | Docstring. Nothing. |
| `audit_tenant_coverage.py` | 13 | `⚠ HARDCODED — uses RYZE_TENANT constant instead of dynamic tenant` | Docstring legend for the HARDCODED verdict. Nothing. |
| `audit_tenant_coverage.py` | 19 | `cd ~/projects/ryzerecruiting/backend` | Docstring path to the old checkout. Stale, harmless. |
| `audit_tenant_coverage.py` | 367 | `f"{BOLD} RYZE.ai — Multi-Tenant Endpoint Coverage Audit {RESET}"` | Banner printed by the audit script. Nothing. |
| `audit_tenant_coverage.py` | 433 | `print(f" 2. Add {GREEN}tenant_id = current_user.tenant_id or 'ryze'{RESET}")` | Suggested-fix text printed by the audit script; it recommends the `or 'ryze'` fallback pattern. Advice text only, but it tells the reader to add more slug sites. |
| `backfill_signup_tenants.py` | 6 | `tenant for existing CANDIDATE/EMPLOYER users still sitting in ryze/NULL.` | Docstring. Nothing. |
| `extract_call_data.py` | 164 | `print("RYZE — webhook log content extraction (READ-ONLY)")` | Banner printed by a read-only developer script. Nothing. |
| `manual_test_tenant_isolation.py` | 22 | `• seed_full.py must have been run (creates RYZE bookings)` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 29 | `# Override URL or RYZE credentials without editing the file:` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 40 | `RYZE_PASS = os.getenv("RYZE_PASSWORD", "YourPasswordHere") # ← set this` | Env-var / module-constant name (`RYZE_EMAIL`, `RYZE_PASSWORD`, `RYZE_PASS`). Rename every use in this file together; anyone's shell history or notes that set the old names stop working. |
| `manual_test_tenant_isolation.py` | 112 | `print(f"{BOLD} RYZE.ai — EP16 Multi-Tenant Isolation Test Suite {RESET}")` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 117 | `if not RYZE_PASS:` | Env-var / module-constant name (`RYZE_EMAIL`, `RYZE_PASSWORD`, `RYZE_PASS`). Rename every use in this file together; anyone's shell history or notes that set the old names stop working. |
| `manual_test_tenant_isolation.py` | 118 | `print(f" {RED}✗{RESET} RYZE_PASSWORD environment variable is not set.")` | Env-var / module-constant name (`RYZE_EMAIL`, `RYZE_PASSWORD`, `RYZE_PASS`). Rename every use in this file together; anyone's shell history or notes that set the old names stop working. |
| `manual_test_tenant_isolation.py` | 120 | `f" Run as: RYZE_PASSWORD=yourpassword FIRM_B_PASSWORD=yourpassword python test_tenant_isolation.py"` | Env-var / module-constant name (`RYZE_EMAIL`, `RYZE_PASSWORD`, `RYZE_PASS`). Rename every use in this file together; anyone's shell history or notes that set the old names stop working. |
| `manual_test_tenant_isolation.py` | 126 | `f" Run as: RYZE_PASSWORD=yourpassword FIRM_B_PASSWORD=yourpassword python test_tenant_isolation.py"` | Env-var / module-constant name (`RYZE_EMAIL`, `RYZE_PASSWORD`, `RYZE_PASS`). Rename every use in this file together; anyone's shell history or notes that set the old names stop working. |
| `manual_test_tenant_isolation.py` | 135 | `ryze_token = login(RYZE_EMAIL, RYZE_PASS)` | Env-var / module-constant name (`RYZE_EMAIL`, `RYZE_PASSWORD`, `RYZE_PASS`). Rename every use in this file together; anyone's shell history or notes that set the old names stop working. |
| `manual_test_tenant_isolation.py` | 136 | `ok(f"RYZE admin login ({RYZE_EMAIL})")` | Env-var / module-constant name (`RYZE_EMAIL`, `RYZE_PASSWORD`, `RYZE_PASS`). Rename every use in this file together; anyone's shell history or notes that set the old names stop working. |
| `manual_test_tenant_isolation.py` | 138 | `fail(f"RYZE admin login ({RYZE_EMAIL})", str(e))` | Env-var / module-constant name (`RYZE_EMAIL`, `RYZE_PASSWORD`, `RYZE_PASS`). Rename every use in this file together; anyone's shell history or notes that set the old names stop working. |
| `manual_test_tenant_isolation.py` | 139 | `print("\n Cannot continue without RYZE credentials. Exiting.")` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 152 | `ryze_candidates = requests.get(` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 153 | `f"{BASE_URL}/api/candidates", headers=hdrs(ryze_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 158 | `ryze_employers = requests.get(` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 159 | `f"{BASE_URL}/api/employer-profiles", headers=hdrs(ryze_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 164 | `ryze_jobs = requests.get(` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 165 | `f"{BASE_URL}/api/job-orders", headers=hdrs(ryze_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 170 | `ryze_bookings = requests.get(` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 171 | `f"{BASE_URL}/api/bookings", headers=hdrs(ryze_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 174 | `ryze_cids = (` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 175 | `{c["id"] for c in ryze_candidates}` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 176 | `if isinstance(ryze_candidates, list)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 184 | `ryze_eids = (` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 185 | `{e["id"] for e in ryze_employers} if isinstance(ryze_employers, list) else set()` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 192 | `ryze_jids = {j["id"] for j in ryze_jobs} if isinstance(ryze_jobs, list) else set()` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 194 | `ryze_bids = (` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 195 | `{b["id"] for b in ryze_bookings} if isinstance(ryze_bookings, list) else set()` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 201 | `overlap = ryze_cids & fb_cids` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 206 | `ok(f"RYZE sees {len(ryze_cids)} candidate(s)")` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 225 | `overlap_e = ryze_eids & fb_eids` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 230 | `ok(f"RYZE sees {len(ryze_eids)} employer(s)")` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 236 | `overlap_j = ryze_jids & fb_jids` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 241 | `ok(f"RYZE sees {len(ryze_jids)} job order(s)")` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 252 | `f"{BASE_URL}/api/candidates/{fb_cid}", headers=hdrs(ryze_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 254 | `f"RYZE cannot read Firm B candidate #{fb_cid}",` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 256 | `if ryze_cids:` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 257 | `ryze_cid = next(iter(ryze_cids))` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 260 | `f"{BASE_URL}/api/candidates/{ryze_cid}", headers=hdrs(firm_b_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 262 | `f"Firm B cannot read RYZE candidate #{ryze_cid}",` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 270 | `f"{BASE_URL}/api/employer-profiles/{fb_eid}", headers=hdrs(ryze_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 272 | `f"RYZE cannot read Firm B employer #{fb_eid}",` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 274 | `if ryze_eids:` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 275 | `ryze_eid = next(iter(ryze_eids))` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 278 | `f"{BASE_URL}/api/employer-profiles/{ryze_eid}",` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 281 | `f"Firm B cannot read RYZE employer #{ryze_eid}",` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 289 | `f"{BASE_URL}/api/job-orders/{fb_jid}", headers=hdrs(ryze_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 291 | `f"RYZE cannot read Firm B job order #{fb_jid}",` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 293 | `if ryze_jids:` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 294 | `ryze_jid = next(iter(ryze_jids))` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 297 | `f"{BASE_URL}/api/job-orders/{ryze_jid}", headers=hdrs(firm_b_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 299 | `f"Firm B cannot read RYZE job order #{ryze_jid}",` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 310 | `headers=hdrs(ryze_token),` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 313 | `f"RYZE cannot PATCH Firm B candidate #{fb_cid}",` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 322 | `ok(f"Firm B candidate #{fb_cid} record unchanged after RYZE PATCH attempt")` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 334 | `headers=hdrs(ryze_token),` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 337 | `f"RYZE cannot PATCH Firm B employer #{fb_eid}",` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 350 | `headers=hdrs(ryze_token),` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 353 | `f"RYZE cannot PATCH Firm B job order #{fb_jid}",` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 362 | `headers=hdrs(ryze_token),` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 364 | `f"RYZE cannot DELETE Firm B job order #{fb_jid_for_delete}",` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 374 | `f"Firm B job order #{fb_jid_for_delete} still exists after RYZE DELETE attempt"` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 378 | `f"Firm B job order #{fb_jid_for_delete} missing after RYZE DELETE attempt",` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 385 | `if ryze_bids:` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 386 | `ryze_bid = next(iter(ryze_bids))` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 389 | `f"{BASE_URL}/api/bookings/{ryze_bid}",` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 392 | `f"Firm B cannot read RYZE booking #{ryze_bid}",` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 396 | `"No RYZE bookings found — skipping booking isolation check (run seed_full.py)"` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 402 | `ryze_search = requests.get(` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 404 | `headers=hdrs(ryze_token),` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 411 | `if ryze_search.ok and firm_b_search.ok:` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 412 | `ryze_search_ids = {r["id"] for r in ryze_search.json()}` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 414 | `search_overlap = ryze_search_ids & fb_search_ids` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 439 | `f"Search endpoints non-200 — skipping (RYZE: {ryze_search.status_code} Firm B: {firm_b_search.status_code})"` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 445 | `ryze_browse = requests.get(` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 447 | `headers=hdrs(ryze_token),` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 454 | `if ryze_browse.ok and firm_b_browse.ok:` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 455 | `ryze_browse_ids = {r["id"] for r in ryze_browse.json().get("rows", [])}` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 457 | `browse_overlap = ryze_browse_ids & fb_browse_ids` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 482 | `ryze_counts = requests.get(` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 483 | `f"{BASE_URL}/admin/db/counts", headers=hdrs(ryze_token)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 488 | `if ryze_counts.ok and firm_b_counts.ok:` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 489 | `rc = ryze_counts.json().get("candidates", 0)` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 491 | `if rc != fc or (rc == len(ryze_cids) and fc == len(fb_cids)):` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `manual_test_tenant_isolation.py` | 493 | `f"DB Explorer sidebar counts are tenant-scoped (RYZE: {rc} Firm B: {fc})"` | Label printed to the developer's terminal by the manual isolation test, or a docstring. Nothing. |
| `manual_test_tenant_isolation.py` | 501 | `f"DB Explorer non-200 — skipping (RYZE: {ryze_browse.status_code} Firm B: {firm_b_browse.status_code})"` | Local variable in a manual test script (`ryze_token`, `ryze_cids`, …). Rename consistently within the file or it raises `NameError`. |
| `reset_demo_db.py` | 10 | `Design choices (all deliberate, matching the RYZE conventions):` | Docstring. Nothing. |
| `reset_demo_db.py` | 12 | `safe to run while ryze-api is up (row-level locks don't block active` | Docstring naming the old systemd service `ryze-api`, which no longer exists. Nothing. |
| `scripts/create_superadmin.py` | 5 | `Creates a RYZE platform-owner superadmin account (tenant_id='ryze').` | Docstring. It records the design: the `ryze` slug needs no `tenants` row. |
| `scripts/create_superadmin.py` | 6 | `No Tenant row is needed — deps.py treats the 'ryze' slug as always-active` | Docstring. It records the design: the `ryze` slug needs no `tenants` row. |
| `scripts/create_superadmin.py` | 30 | `parser = argparse.ArgumentParser(description="Create a RYZE superadmin user.")` | argparse description. Nothing. |
| `seed_cleanup.py` | 3 | `RYZE.ai Seed Cleanup Script` | Docstring title. Nothing. |
| `seed_full.py` | 3 | `RYZE.ai Full Demo Seed Script` | Docstring / argparse description of the seed script. Nothing. |
| `seed_full.py` | 1682 | `parser = argparse.ArgumentParser(description="Seed full demo data for RYZE.ai.")` | Docstring / argparse description of the seed script. Nothing. |
| `seed_greenpath_demo.py` | 3 | `RYZE.ai — Greenpath Recruiting Demo Seed (Grand Finale)` | Docstring title. Nothing. |
| `seed_greenpath_demo.py` | 26 | `* On --wipe-only, user id 1 is restored to tenant_id='ryze'.` | Docstring describing the `--wipe-only` teardown. Pair with line 149. |
| `seed_greenpath_demo.py` | 32 | `python seed_greenpath_demo.py --wipe-only # post-demo teardown: wipe + restore user 1 to ryze` | Docstring describing the `--wipe-only` teardown. Pair with line 149. |
| `seed_greenpath_demo.py` | 118 | `def wipe_all(restore_ryze_tenant: bool):` | Parameter name `restore_ryze_tenant`. Rename all three lines together or the script raises `TypeError`/`NameError`. |
| `seed_greenpath_demo.py` | 148 | `if restore_ryze_tenant:` | Parameter name `restore_ryze_tenant`. Rename all three lines together or the script raises `TypeError`/`NameError`. |
| `seed_greenpath_demo.py` | 151 | `print(f" ✓ user #{SUPERADMIN_ID} ({admin.email}) restored to tenant 'ryze'\n")` | Message printed to the operator's terminal. Nothing. |
| `seed_greenpath_demo.py` | 1310 | `help="Post-demo teardown: wipe everything except user 1 and restore them to the 'ryze' tenant.")` | argparse help text. Nothing. |
| `seed_greenpath_demo.py` | 1323 | `admin = wipe_all(restore_ryze_tenant=args.wipe_only)` | Parameter name `restore_ryze_tenant`. Rename all three lines together or the script raises `TypeError`/`NameError`. |
| `seed_greenpath_demo.py` | 1326 | `print("✅ Teardown complete. Database is empty; you are back on the 'ryze' tenant.")` | Message printed to the operator's terminal. Nothing. |
| `seed_landscaping_jobs.py` | 4 | `# RYZE.ai demo video, then generates pgvector embeddings for each so the` | Header comment. Nothing. |
| `seed_landscaping_jobs.py` | 25 | `# Default tenant is 'ryze' if --tenant is omitted.` | Header comment. Nothing. |
| `tests/conftest.py` | 3 | `RYZE Intelligence regression suite.` | Docstring. Nothing. |
| `tests/conftest.py` | 8 | `1. Tenant isolation — greenpath_recruiting can see its calls; ryze cannot.` | Docstring. Nothing. |
| `tests/test_signup_tenant_resolution.py` | 58 | `def test_no_match_resolves_to_ryze(db):` | Test function name. Nothing functional; pytest IDs change. |
| `tests/test_signup_tenant_resolution.py` | 63 | `def test_multi_firm_match_resolves_to_ryze(db, caplog):` | Test function name. Nothing functional; pytest IDs change. |
| `tests/test_tenant_isolation.py` | 6 | `proved by hand that greenpath's calls are invisible to ryze. These tests turn` | Docstring. Nothing. |

---

## F. DOCS

101 matching lines in six files. Counts only, per the task spec. `context/current-feature.md` was counted as it stood when this audit was generated (10 lines); it is the live task file and will change.

| file | matching lines |
|---|---|
| `context/CHANGELOG.md` | 65 |
| `CLAUDE.md` | 21 |
| `context/current-feature.md` | 10 |
| `context/dead-code-audit.md` | 2 |
| `tests/README.md` | 2 |
| `context/tenant-assignment-problem.md` | 1 |

---

## Counts

Per category and per top-level folder. One row per matching line.

| category | `app/` | (repo root) | `alembic/` | `context/` | `scripts/` | `tests/` | total |
|---|---|---|---|---|---|---|---|
| A. TENANT-SLUG | 124 | 66 | 5 | 0 | 1 | 5 | 201 |
| B. BRANDING-RESOLVED | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| C. BRANDING-HARDCODED | 29 | 0 | 0 | 0 | 0 | 0 | 29 |
| D. DOMAIN-URL | 15 | 18 | 0 | 0 | 1 | 0 | 34 |
| E. INTERNAL-ID | 56 | 113 | 0 | 0 | 3 | 5 | 177 |
| F. DOCS | 0 | 21 | 0 | 78 | 0 | 2 | 101 |
| **Total** | **225** | **218** | **5** | **78** | **5** | **12** | **543** |

Arithmetic: A + B + C + D + E + F = 201 + 1 + 29 + 34 + 177 + 101 = 543, which equals the raw line count from the first search command (543 tracked lines; the `scripts/` search adds 0 because its 5 lines are already among them). Filename-only hits: 0.

Files with no hit that the spec or `CLAUDE.md` expected to have one: `app/services/ai_parser.py`, `app/api/candidate_pdf_template.py`, `app/api/employer_pdf_template.py`, `app/api/auth.py`, `app/services/scheduler.py`.

## Files with hits in more than one category

| file | categories |
|---|---|
| `app/services/branding.py` | A, B, D, E |
| `app/services/email.py` | A, C, D, E |
| `app/api/bookings.py` | A, C, D |
| `app/core/config.py` | C, D, E |
| `scripts/create_superadmin.py` | A, D, E |
| `seed_full.py` | A, D, E |
| `.env.example` | D, E |
| `analyze_webhook_logs.py` | A, E |
| `app/api/admin_invite.py` | A, E |
| `app/api/billing.py` | A, E |
| `app/api/candidates.py` | A, C |
| `app/api/chat.py` | A, E |
| `app/api/chat_sessions.py` | A, E |
| `app/api/db_explorer.py` | A, E |
| `app/api/job_orders.py` | A, E |
| `app/api/webhooks.py` | A, E |
| `app/core/deps.py` | A, E |
| `app/main.py` | C, D |
| `app/models/employer_profile.py` | A, E |
| `app/models/job_order.py` | A, E |
| `app/models/user.py` | A, E |
| `app/services/embedding_service.py` | A, E |
| `app/services/notifications.py` | A, E |
| `app/services/tenant_resolution.py` | A, E |
| `app/services/usage.py` | A, E |
| `audit_tenant_coverage.py` | A, E |
| `backfill_signup_tenants.py` | A, E |
| `manual_test_tenant_isolation.py` | D, E |
| `seed_cleanup.py` | D, E |
| `seed_greenpath_demo.py` | A, E |
| `seed_landscaping_jobs.py` | A, E |
| `tests/conftest.py` | A, E |
| `tests/test_signup_tenant_resolution.py` | A, E |

---

## CLAUDE.md corrections needed

Not made in this task. Recorded here so a follow-up can make them.

1. **Stale: PDF footers.** "Tenant branding" says the three PDF templates "bake `RYZE.ai` / `RYZE.AI` into their footers" and lists them as remaining migration targets. They do not. All three render `{footer_brand}`, filled from `get_branding(db, tenant_id).brand_name` at `app/api/candidates.py:905`, `app/api/employer_profiles.py:608` and `app/api/job_orders.py:526`. The only leftovers are a stale docstring (`job_order_pdf_template.py:4`) and the download filename `…_RYZE_Profile.pdf` (`candidates.py:920`).
2. **Stale: "Verify `ai_brief.py` and `calendar.py`".** Verified. `ai_brief.py` takes `brand_name` from its caller and has no hardcoded brand. `calendar.py:63` **is** hardcoded (`"RYZE.ai — {company}"`) and is a real remaining target.
3. **Incomplete: GUARDRAIL list.** Every site and count it gives is correct (four definitions; 11 + 10 + 1 `or "ryze"` fallbacks; two `default="ryze"` columns; two superadmin gates; 11 `notifications.py` defaults; the `usage.py` exemption). It omits these functional slug sites:
   - `app/services/tenant_resolution.py` — signup bucket (`25, 42, 44, 55, 56`)
   - `app/services/branding.py:86, 89` — resolver fallback and short-circuit
   - `app/services/email.py` — 17 `get_branding(None, "ryze")` fallbacks
   - `app/api/chat.py` — 13 `tenant_id: str = RYZE_TENANT` parameter defaults
   - `or RYZE_TENANT` fallbacks: `app/api/employer_profiles.py` (8), `app/api/candidates.py` (4), `app/api/search.py` (3, plus one parameter default), `app/api/billing.py` (3), `app/api/chat_sessions.py` (1), `app/api/webhooks.py` (1), `app/api/bookings.py:73` (1), `app/services/embedding_service.py` (5)
   - Column defaults via the constant: `app/models/job_order.py:16`, `app/models/job_interest.py:28` (the guardrail lists the definitions in those files but not that they are column defaults)
   - Data and tooling: migration `alembic/versions/11ae0fa76851…` (5 backfill statements), `seed_full.py`, `seed_greenpath_demo.py:149`, `seed_landscaping_jobs.py:203`, `backfill_signup_tenants.py:42`, `analyze_webhook_logs.py:180`, `audit_tenant_coverage.py:115-117`, `tests/conftest.py:54`, `scripts/create_superadmin.py:49`
4. **Understated: "Known risk" under Tenant branding.** It describes a notify call site forgetting `tenant_id` as a hypothetical. Eight of the eleven call sites do it today (Live bugs, item 2).
5. **Stale: Conventions, "Resend only sends from the verified `ryze.ai` domain".** True of the Resend account as last known, but the domain is no longer controlled; the line should say what the sending domain will be once one is verified.
6. **Wrong: "`scripts/` is gitignored, so `scripts/create_superadmin.py` exists on disk but not on GitHub"** (Local development). The ignore rule exists, but the file was committed (`0c00bcc`) and is on `origin/main`. Either the sentence or the tracking is wrong; the script contains no secret (the email is an argument and the password is prompted for with `getpass`).
7. **Minor: Appendix A of the frontend audit** (not `CLAUDE.md`, noted here for the same follow-up) says 12 chat defaults and 15 `email.py` fallbacks. The counts today are 13 and 17.

---

## Proposed scope for the narrow rebrand

A proposal. Dane decides.

### 1. Safe to rename in one pass — display text with no logic attached

- **B:** `app/services/branding.py:67` (`brand_name="RYZE.ai"`). One line; changes every resolved surface.
- **C, tenant-facing:** the public booking-response pages in `app/api/bookings.py` (`297, 348, 449, 776, 784, 848, 856, 865`), the Zoom topic (`338, 489`), the calendar title (`app/services/calendar.py:63`) and the PDF download filename (`app/api/candidates.py:920`). Better than renaming: route them through `get_branding`, since every one is shown to another tenant's contacts. That is a behaviour change and belongs in its own task; a plain rename is the narrow option.
- **C, platform-facing:** the two welcome emails in `app/services/email.py` (`1373-1381, 1419, 1431, 1456-1464, 1497, 1508`) and the API docs title (`app/main.py:30`).
- **C, unused:** `app/core/config.py:11` (`APP_NAME`) — rename or delete.
- **E, comments and docstrings in `app/`:** harmless to update; no need to.

Hold back from this list, because each is a decision and not a label:

- `app/api/bookings.py:803` and `app/services/email.py:1430, 1507` name the legal entity "RYZE GROUP, Inc." The SMS-consent text must match the Twilio registration. Change only when the entity or the registration changes.
- The C.1 prompt framing. It changes what the product does; it should be scoped with the tenant-model decision, not with a rename.

### 2. Must change before any deploy — category D

Because the domains are no longer controlled, each of these is broken, not merely mislabelled, the moment the app is hosted:

- **CORS** (`app/main.py:43-47`): a frontend on a new domain cannot call the API at all.
- **`FROM_EMAIL`** (`app/core/config.py:28`, plus Resend domain verification and DNS): no email can be sent from a domain that cannot be verified.
- **Hardcoded links** (`app/api/bookings.py:805, 844`; `app/services/email.py:1395, 1416, 1479, 1494`; link text at `email.py:466`): a new firm's welcome email and the SMS-consent privacy link point at someone else's site. Replace with `FRONTEND_URL`.
- **`.env` / `.env.example`**: `FRONTEND_URL`, `BACKEND_URL`, and the example redirect URIs; then the Google and LinkedIn OAuth consoles, the Stripe webhook destination and the Zoom webhook endpoint to match.
- **Before deploy for a different reason:** Live bugs 1 and 2. Neither is a rename, both are exploitable or visible on day one of a hosted, multi-tenant system.

### 3. Do not touch in the rebrand

- **All of A.** The slug gates billing, the AI budget, invite rights, the global DB Explorer, branding resolution and row ownership, and is stored in `users.tenant_id`. As shown above, leaving it alone never puts the word in front of a customer once `branding.py:67` is changed. Changing it is a data migration plus the 201 lines in Section A, and is a separate job.
- **E that breaks something if renamed:**
  - `alembic/versions/11ae0fa76851…` — never edit an applied migration.
  - `seed_full.py` and `seed_cleanup.py` test addresses (`@ryze.ai`) — they are fixture identities that must match each other; nothing is mailed.
  - `seed_greenpath_demo.py` (`restore_ryze_tenant`, line 149), `seed_landscaping_jobs.py`, `backfill_signup_tenants.py`, `scripts/create_superadmin.py` — they write or select the slug.
  - `tests/conftest.py:54`, `tests/test_signup_tenant_resolution.py` — they assert the slug.
  - `manual_test_tenant_isolation.py` — `RYZE_EMAIL` / `RYZE_PASSWORD` env-var names and dozens of `ryze_*` local variables; renaming buys nothing and risks a `NameError`.
  - `audit_tenant_coverage.py:115-117` — the patterns must track the slug, not the brand.
  - `_ryze_defaults` (`app/services/branding.py:64, 87`) — internal function name; rename only if the constant is ever renamed.
- **F.** `context/CHANGELOG.md` and the pre-fork docs are history. `CLAUDE.md` gets the corrections listed above in its own task.

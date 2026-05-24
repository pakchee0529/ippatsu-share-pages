# Restore real portal HTML from git history (home PC)

**Date:** 2026-05-24  
**Agent:** Cursor  
**Repo:** ippatsu-share-pages  
**Mission:** Remove E2E test keys from published `portal/survey/` and `portal/negotiation/` without `generate_portal.py` (no prod `queue.json` on home PC).

## Git history survey

| Commit | `portal/survey/index.html` | `portal/negotiation/index.html` |
|--------|---------------------------|--------------------------------|
| `8cce077`, `b5b7c37`, `0f9a75c`, `1d0c52a`, `aebc5e6` | Real keys (e.g. `51409324`), ~45 cards, no `9999000*` | **File did not exist on `main`** |
| `2b8fe8a`, `9834d42`, `69375b6` | Test keys `99990001`–`99990003`, B-plan JS | Test-only (only commits that ever added this path) |

Blob `portal/survey/index.html` is **identical** at `8cce077` and `0f9a75c` (`58508f4e…`).

`git log --all -- portal/negotiation/index.html` → only `2b8fe8a` and descendants. No commit in any branch contains real negotiation HTML.

## Actions taken

1. **Restored** `portal/survey/index.html` from **`0f9a75c`** (last `main` commit before `2b8fe8a` E2E publish; same content as `8cce077`).
2. **Removed** `portal/negotiation/index.html` with `git rm` — pre-test `main` had no this file; all git versions are test-only. Avoids publishing fake `9999000*` cases.

**Not changed:** `scripts/generate_portal.py`, `scripts/portal_immediate_status_client.py`, other `portal/` / `share/` paths, `data/`.

## Post-restore checks (survey)

- No `99990001` / `99990002` / `99990003`
- Contains real key `51409324` (and ~45 `survey-update-card` entries)
- No `mark_survey_done` / `PORTAL_IMMEDIATE` (A-plan / PC反映待ち HTML)
- `service_role` appears only in comment (“Never embed service_role”)
- No `sb_secret_`, no `SUPABASE_ACCESS_TOKEN` literal

## Negotiation page

- File **deleted** from repo (staged removal). GitHub Pages URL will 404 until company PC regenerates with prod `queue.json`.
- `portal/index.html` still links to `./negotiation/` (unchanged this commit) — human may want portal menu updated on company PC regen.

## B-plan JS

History restore **drops** B-plan immediate-status JS on survey (reverts to pre–E2E publish HTML). Correct B-plan + real negotiation list requires **`generate_portal.py` on company PC** with prod `data/survey/queue.json` and appropriate env (`PORTAL_IMMEDIATE_STATUS=1`, etc.).

## Follow-up (company PC)

- Regenerate and commit `portal/survey/index.html` and `portal/negotiation/index.html` from prod queue.
- Publish / push after human approval per AGENTS.md.

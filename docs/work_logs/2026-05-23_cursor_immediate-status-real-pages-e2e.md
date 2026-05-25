# Work log — immediate status real portal pages E2E

**Date:** 2026-05-23  
**Branch:** `main`  
**Agent:** Cursor

## Done

- `docs/examples/immediate_status_test_queue.json` — keys 99990001–99990003 only
- Generated `portal/survey/index.html` (2 survey items) and `portal/negotiation/index.html` (1 static + promoted candidates JSON)
- `PORTAL_IMMEDIATE_STATUS=1`, endpoint `submit-survey-status-request` (same as A-plan deploy)
- `scripts/load_portal_apikey_for_generate.py` — anon key from prior HTML (no service_role)
- `docs/immediate_survey_status_recovery.md` — restore procedures
- HTML safety: no service_role strings; no real 514xxxxx keys in test pages

## Publish

- Committed test portal HTML to `main` and pushed for GitHub Pages (see commit in log)

## Depends on

- ippatsu-pc: `python tools/immediate_status_e2e_setup.py all` after `SUPABASE_ACCESS_TOKEN` set

## Restore

See `docs/immediate_survey_status_recovery.md`

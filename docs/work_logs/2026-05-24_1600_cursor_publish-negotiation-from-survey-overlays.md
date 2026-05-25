# Publish negotiation page from survey overlays (home PC, no prod queue)

**Date:** 2026-05-24  
**Agent:** Cursor  
**Repo:** ippatsu-share-pages

## Context

- Prod `queue.json` not available on home PC.
- `portal/survey/index.html` restored from git history (real cases, ~43 cards).
- `portal/negotiation/index.html` was deleted (404) after E2E test publish.
- Backend B-plan (DDL, Edge Function, overlay table) operational; overlays empty.

## Approach

1. Parse **43** `survey-update-card` entries from existing `portal/survey/index.html` for `PROMOTED_SURVEY_CANDIDATES` (management_no_key, label, management_no, note).
2. Reuse **anon publishable key** already embedded in survey HTML (`SURVEY_STATUS_REQUEST_API_KEY` → `PORTAL_STATUS_API_KEY`); no new secrets written to repo.
3. Inject **B-plan immediate JS** from `portal_immediate_status_client.py` @ `69375b6`:
   - `mark_survey_done` / `revert_to_survey_wait` via `submit-survey-status-request`
   - `applySurveyOverlay(statusMap, serverOk)` — server wins; clears stale localStorage after revert
   - Negotiation promoted cards: `mapSection.insertAdjacentHTML("beforebegin", html)`
4. Generate `portal/negotiation/index.html` via `build_negotiation_html()`:
   - **Static negotiation list: empty**
   - Overlay-promoted cards are the live source of truth on the negotiation page

## Verification (pre-push)

| Check | survey | negotiation |
|-------|--------|-------------|
| 99990001/02/03 | absent | absent |
| PORTAL_STATUS_API_KEY | set (len 208) | set |
| mark_survey_done | yes | — |
| revert_to_survey_wait | — | yes |
| PROMOTED_SURVEY_CANDIDATES | — | non-empty (43) |
| serverOk fix | yes | — |
| mapSection beforebegin | — | yes |
| service_role literal | comment only | comment only |

## Not changed

- `scripts/generate_portal.py`, prod `data/`, `queue.json`
- Test keys not reintroduced

## Follow-up (company PC)

Formal regen with prod `data/survey/queue.json` + `generate_portal.py` (`PORTAL_IMMEDIATE_STATUS=1`) to align static negotiation list, map points, and queue-driven exclusions with production.

# Work Log: live portal search filter

| Item | Value |
|------|-------|
| Date | 2026-07-01 16:20 |
| Agent | codex |
| Repo | ippatsu-share-pages |
| Branch | cursor/fix-live-portal-search |

## Changed Files

- `scripts/generate_portal.py`
- `portal/negotiation/index.html`
- `portal/negotiation/gojo/index.html`
- `portal/negotiation/totsukawa/index.html`
- `portal/negotiation/yoshino/index.html`
- `portal/entrustment/index.html`
- `portal/cases/index.html`
- `docs/work_logs/2026-07-01_1620_codex_live-portal-search-filter.md`

## Summary

- Fixed the portal search filter so it reads the current DOM rows each time filtering runs.
- Re-applied the search filter after Supabase live refresh replaces the generated fallback HTML.
- Covered negotiation, entrustment, and case-list search blocks that use live refreshed content.

## Investigation Notes

- Public negotiation page contained management number `51403222`.
- Supabase live data returned it as `negotiation_wait`.
- Browser check showed the card existed after live refresh, but entering `51403222` in search reported `0` because the filter had captured stale generated nodes before live refresh.

## Generation

- `python scripts\generate_portal.py --mode negotiation-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data`
- `python scripts\generate_portal.py --mode entrustment-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data`
- `python scripts\generate_portal.py --mode cases-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data`

Focused generation updated list pages. Regenerated case detail page churn was removed from this change.

## Guardrails

- No Supabase writes.
- No Edge Function deploy.
- No `.env` changes.
- No commit, push, or GitHub Pages publish.
- No hand edits to generated `portal/` HTML.

## Verification

- `python -m py_compile scripts\generate_portal.py`
- `git diff --check`
- Local browser smoke via `http://127.0.0.1:8765/portal/negotiation/`
  - Search `51403222` returned `1`.
  - Target card existed and remained visible after Supabase live refresh.
- Local browser smoke via `http://127.0.0.1:8765/portal/cases/`
  - Search `51403222` returned `1`.
  - Only `status-negotiation_wait` remained visible with `1件`.
- Local browser smoke via `http://127.0.0.1:8765/portal/entrustment/`
  - Current page had `0` cards.
  - Search input stayed functional and empty state was shown without script failure.

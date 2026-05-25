# Immediate survey status — recovery & test page restore

## What changed (E2E test publish)

| Item | Value |
|------|--------|
| **Test commit** | See `git log -1 --oneline` on `main` after E2E publish |
| **Survey page** | `portal/survey/index.html` — only keys `99990001`, `99990002` |
| **Negotiation page** | `portal/negotiation/index.html` — static `99990003` + overlay promotions |
| **Data source** | `docs/examples/immediate_status_test_queue.json` via `.e2e_data/survey/queue.json` at generate time |
| **Mode** | `PORTAL_IMMEDIATE_STATUS=1` (B-plan ON) |
| **NOT used** | Production `ippatsu-pc/data/survey/queue.json` |

## Public URLs (after GitHub Pages deploy)

- https://pakchee0529.github.io/ippatsu-share-pages/portal/survey/
- https://pakchee0529.github.io/ippatsu-share-pages/portal/negotiation/

Backend must be deployed before buttons work (see ippatsu-pc `tools/immediate_status_e2e_setup.py`).

## Restore production portal lists

### A. Regenerate from company PC prod queue (recommended)

```powershell
cd C:\Users\kotan\Projects\ippatsu-share-pages
# clean tree; merge main if needed
$env:PORTAL_SURVEY_REQUEST_API_KEY = "<anon from Supabase Dashboard>"
$env:PORTAL_IMMEDIATE_STATUS = "1"   # or "0" for legacy A-plan only
python scripts/generate_portal.py --mode full --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data
git add portal/survey/index.html portal/negotiation/index.html
git commit -m "Restore production portal survey/negotiation from prod queue"
git push origin main
```

### B. Revert HTML to pre-test commit

```powershell
cd ippatsu-share-pages
git log --oneline -5 -- portal/survey/index.html
git checkout <commit-before-test> -- portal/survey/index.html portal/negotiation/index.html
git commit -m "Revert portal survey/negotiation to pre-E2E-test snapshot"
git push origin main
```

### C. Legacy A-plan only (no immediate overlay)

```powershell
$env:PORTAL_IMMEDIATE_STATUS = "0"
python scripts/generate_portal.py --mode full --data-root <prod-data>
# commit + push as above
```

## Clean test overlay rows (Supabase)

Test keys only: `99990001`, `99990002`, `99990003`

```powershell
cd ippatsu-pc
$env:SUPABASE_ACCESS_TOKEN = "<personal access token — do not paste in chat>"
$env:PORTAL_SURVEY_REQUEST_API_KEY = "<anon key for API tests>"
python tools/immediate_status_e2e_setup.py cleanup-test-keys
```

Or SQL Editor:

```sql
DELETE FROM portal_case_status_overrides
WHERE management_no_key IN ('99990001', '99990002', '99990003');
```

## Backend deploy (required once per environment)

```powershell
cd ippatsu-pc
$env:SUPABASE_ACCESS_TOKEN = "<token>"
python tools/immediate_status_e2e_setup.py apply-ddl
python tools/immediate_status_e2e_setup.py deploy
python tools/immediate_status_e2e_setup.py test-api
```

DDL file: `supabase/migrations/draft_portal_case_status_overrides.sql`  
Function: `submit-survey-status-request` (includes B-plan GET + overlay POST).

## Verify GitHub Pages state

- https://github.com/pakchee0529/ippatsu-share-pages/actions — Pages build succeeded
- Survey page shows `999 90001` / `999 90002` labels (not real 514xxxxx keys)

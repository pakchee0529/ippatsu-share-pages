# Immediate survey status workflow (portal side)

See also: `ippatsu-pc/docs/immediate_survey_status_workflow.md` (canonical spec).

## Portal changes (draft)

- `scripts/portal_immediate_status_client.py` — JS snippets for B-plan
- `scripts/generate_portal.py` — survey/negotiation HTML + client overlay
- Default: `PORTAL_IMMEDIATE_STATUS=1` (set `0` for legacy A-plan JS)

## Survey page button

- Label: **現調済みにする**
- Confirm → POST `action=mark_survey_done` to `update-portal-case-status`
- Success: card hidden, status “交渉待ちへ移動済み”

## Negotiation page button

- Label: **現調待ちに戻す** (enabled when immediate mode + apikey)
- Confirm → POST `action=revert_to_survey_wait`
- Success: card hidden
- Promoted cards injected from embedded `PROMOTED_SURVEY_CANDIDATES` (survey static items JSON)

## Mock generate

```powershell
cd ippatsu-share-pages
mkdir .mock_data\survey -Force
Copy-Item docs\examples\mock_survey_queue_immediate_status.json .mock_data\survey\queue.json
$env:PORTAL_SURVEY_REQUEST_API_KEY = "mock-publishable-key"
python scripts/generate_portal.py --mode full --data-root .mock_data
# verify portal/survey + portal/negotiation, then restore portal/ if needed
```

Do **not** commit generated `portal/` from mock runs.

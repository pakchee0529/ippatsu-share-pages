# Immediate survey status workflow (portal side)

Canonical backend: `ippatsu-pc-prod/supabase/functions/submit-survey-status-request`.

## Portal changes

- `scripts/portal_immediate_status_client.py` - JS snippets for portal actions
- `scripts/generate_portal.py` - survey/negotiation HTML + live cases client
- Default: `PORTAL_IMMEDIATE_STATUS=1` (set `0` for legacy A-plan JS)

## Survey page buttons

### 現調済みにする

- Confirm -> POST `action=mark_survey_done`
- Backend effect: `cases.status: survey_wait -> negotiation_wait`
- Event: `case_events.event_type = survey_completed`
- Success: card is hidden/reloaded into the negotiation list.

### 返却候補にする

- Confirm -> POST `action=mark_return_candidate`
- Backend effect: `cases.status -> return_wait`
- Event: `case_events.event_type = moved_to_return_wait`
- The button label remains "返却候補にする", but the canonical status is the existing `return_wait`.
- Success: card is hidden/reloaded into the negotiation/return-wait list.

## Negotiation page buttons

### 現調待ちに戻す

- Confirm -> POST `action=revert_to_survey_wait`
- Backend effect: `cases.status: negotiation_wait|return_wait -> survey_wait`
- Event: `case_events.event_type = moved_to_survey`
- Success: card is hidden/reloaded into the survey list.

### Other live lifecycle buttons

- `mark_entrustment_wait`: `negotiation_wait -> entrustment_wait`
- `mark_construction_wait`: `entrustment_wait -> construction_wait`
- `mark_returned`: `return_wait -> returned`

These are already canonical `cases.status` transitions via the same Edge
Function.

## Overlay role

- `portal_case_status_overrides.negotiation_wait` is legacy data from the old immediate-overlay workflow.
- `portal_case_status_overrides.return_candidate` is legacy data from the old return-candidate overlay workflow.
- New portal button operations should update `cases.status`, insert `case_events`, then delete any matching legacy overlay row.

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

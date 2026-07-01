# Portal Excel Reflection Pending Design

## Purpose

Share-page can update the Supabase workflow state from a phone, but the company master workbook is still the shared-HDD Excel file. A portal transition can therefore be correct in Supabase while still waiting for a later Excel update.

This design keeps those two ideas separate:

- `cases.status`: current workflow state used by Share-page.
- Excel reflection state: whether the shared-HDD workbook has been updated after a portal-origin transition.

## Scope

Phase 1 covers only these portal-origin transitions:

- `survey_wait` -> `negotiation_wait`
- `negotiation_wait` -> `entrustment_wait`

Phase 1 intentionally does not add a reflection-pending list for `construction_wait`.

Reason: the immediate operational gap is the return-to-office update from phone/Supabase to the negotiation master workbook. Adding the same queue to the construction side before that workflow is proven would add another state surface without a confirmed handoff need.

## Page Behavior

### Negotiation Page

Show a compact "Excel反映待ち" list for cases that:

- currently have `cases.status = negotiation_wait`;
- were moved to `negotiation_wait` by a portal-origin event such as `survey_completed`;
- do not yet have a later Excel-reflection event for that same transition.

Each item should show:

- management number;
- label/span;
- portal transition time;
- a button or action surface for "Excel反映済みにする" once the Edge Function supports it.

### Entrustment Page

Show the same compact "Excel反映待ち" list for cases that:

- currently have `cases.status = entrustment_wait`;
- were moved to `entrustment_wait` by a portal-origin event such as `negotiation_completed`;
- do not yet have a later Excel-reflection event for that same transition.

### Construction Page

No reflection-pending list in Phase 1.

If a later shared-HDD handoff requires this, add it as a separate decision with evidence from the actual construction workflow.

## Required Edge Function Support

Share-page cannot determine Excel reflection state from the current public case list alone. The Edge Function should expose a read endpoint such as:

```text
GET submit-survey-status-request?list=excel_reflection_pending&statuses=negotiation_wait,entrustment_wait
```

Suggested response shape:

```json
{
  "ok": true,
  "excel_reflection_pending": [
    {
      "case_id": "uuid",
      "management_no_key": "51403222",
      "management_no": "51403222",
      "label": "越作1～2",
      "status": "negotiation_wait",
      "transition_event_type": "survey_completed",
      "transition_source": "portal_live_cases",
      "transition_at": "2026-06-29T07:13:23.139368+00:00"
    }
  ]
}
```

To support "Excel反映済みにする", add a POST action that records an event instead of changing `cases.status`:

```json
{
  "management_no_key": "51403222",
  "action": "mark_excel_reflected",
  "reflected_status": "negotiation_wait",
  "source": "portal_excel_reflection"
}
```

Suggested event:

- `event_type`: `excel_reflection_applied`
- `from_status`: current status
- `to_status`: current status
- `actor_source`: `portal`
- `source`: `portal_excel_reflection`
- `raw_payload.reflected_status`: `negotiation_wait` or `entrustment_wait`

## Pending Rule

A case is pending when all are true:

- current status is `negotiation_wait` or `entrustment_wait`;
- the latest matching portal-origin transition into that status exists;
- no later `excel_reflection_applied` event exists for the same case and current status.

The list should be ordered by transition time ascending so the oldest unreflected updates are handled first.

## Guardrails

- Do not write directly to Excel from Share-page.
- Do not change `cases.status` when marking Excel reflection as done.
- Do not use legacy `portal_case_status_overrides` for this state.
- Do not include `construction_wait` until the workflow need is confirmed.
- Do not expose service-role keys or secrets in generated HTML.

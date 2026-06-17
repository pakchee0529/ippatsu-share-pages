# Survey GPS Rules For G9 And Virtual Poles

## Summary
- Added survey map coordinate fallback rules for steep-slope `G9` pole names.
- If normal GPS lookup is incomplete, generated labels now try `G9` variants such as `95 -> 95G9`, `95G1 -> 95G1G9`, and `K -> K9`.
- If only one side of a span resolves, the survey page now uses the resolved side as the representative map point.
- This covers virtual poles such as `K`, new/missing poles, and service-drop spans ending in `引込`.

## Confirmed Cases
- `51406108` `西川95～95G1` -> `西川95G9～95G1G9`
- `51406127` `西川116G9～118G1G9` -> uses `西川116G9` because `西川118G1G9` is missing/new
- `51406751` `沼田原85K～86N1` -> uses resolved side for virtual `K`
- `51409718` `出谷49G1～49G1S1` -> `出谷49G1G9～49G1S1`
- `51410306` `中峰3W3～引込` -> uses `中峰3W3`

## Verification
- `python -m py_compile scripts\generate_portal.py scripts\portal_immediate_status_client.py`
- `python scripts\generate_portal.py --mode survey-only`
  - HTML regenerated.
  - Existing validation blocker remains: `survey must not list negotiation_wait key 51403794`.
- Checked the five previously missing survey keys; all now have generated map coordinates.
- `git diff --check`
  - No whitespace errors; CRLF warnings only.

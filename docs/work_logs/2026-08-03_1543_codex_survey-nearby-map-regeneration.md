# Work Log: Survey nearby-map regeneration

| Field | Value |
|---|---|
| Date | 2026-08-03 15:43 JST |
| Actor | codex |
| Repository | ippatsu-share-pages |
| Branch | codex/survey-nearby-map-regen-20260803 |

## Changed files

- `portal/survey/index.html`
- `portal/survey/gojo/index.html`
- `portal/survey/totsukawa/index.html`
- `portal/survey/yoshino/index.html`

## Purpose

- Regenerated the survey-wait portal pages so each case with map data provides a working 200 m nearby-pole map control.

## Validation

- Ran `python scripts/generate_portal.py --mode survey-only` successfully.
- Confirmed all 216 cards have map payload, center coordinates, at least one nearby pole within 200 m, and the nearby-map control.
- Ran `git diff --check` successfully.

## Publish status

- Publication is pending because GitHub CLI `gh` is not installed on this PC.

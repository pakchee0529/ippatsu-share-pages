# Survey Wait Search And Nearby Map

## Summary
- Added a search box to the survey wait page.
- Search filtering updates the visible count and the bottom multipin map.
- Restored per-card Google Maps links as `地図を開く`.
- Added per-card `半径200m` nearby-pole maps.
- Survey wait cards now show only four actions: `地図を開く`, `半径200m`, `現調済みにする`, `返却候補にする`.

## Verification
- `python -m py_compile scripts\generate_portal.py scripts\portal_immediate_status_client.py`
- `python scripts\generate_portal.py --mode survey-only`
  - HTML was regenerated.
  - Existing validation blocker remains: `survey must not list negotiation_wait key 51403794`.
- Browser smoke via local `127.0.0.1` server:
  - Search input exists.
  - `西川` search returned 26 visible cards and 24 map-point cards.
  - Search result Google Maps link was enabled.
  - First visible card had exactly four buttons.
  - `半径200m` opened and rendered nearby markers.
- `git diff --check`
  - No whitespace errors; CRLF conversion warnings only.

# Survey Live Geo Fallback

## Summary
- Fixed survey wait cards losing `地図を開く` and `半径200m` after the live Supabase refresh.
- The live cases endpoint currently returns `start_lat` and `start_lng` keys with empty values for survey rows.
- The survey page now caches generated static card coordinates before live refresh and fills missing live row coordinates by `management_no_key` / `management_no`.

## Verification
- `python -m py_compile scripts\generate_portal.py scripts\portal_immediate_status_client.py`
- `python scripts\generate_portal.py --mode survey-only`
  - HTML regenerated.
  - Existing validation blocker remains: `survey must not list negotiation_wait key 51403794`.
- Read-only live endpoint check:
  - live rows: 223
  - live rows with empty coordinates before fallback: 223
  - rows fillable from static generated coordinates: 218
- Local browser smoke:
  - Static fallback display still shows four buttons.
  - Local CORS blocks live fetch from `127.0.0.1`, so deployed GitHub Pages origin is the final live browser check target.
- `git diff --check`
  - No whitespace errors; CRLF warnings only.

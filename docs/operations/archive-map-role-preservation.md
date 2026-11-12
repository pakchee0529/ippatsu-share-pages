# Archive map role preservation candidate

This candidate preserves existing maps without inventing missing historical coordinates. It is not a complete legacy business-regeneration migration.

## Role rules

An overall-map representative may be a historical midpoint rather than a span endpoint. Preserve a validated baseline representative and compare explicit plain coordinates with that same role. Keep source/GPS and baseline/source endpoint conflicts, source/prior URL conflicts, and the no-baseline plain/endpoint check.

Normal regeneration refuses newly available published roles. The published endpoint projection matches the renderer: start and end are visible only when both exist and are distinct. A single internal endpoint may be recomputed only when the published projection stays unchanged. A second endpoint enabling a new two-point map stops. Evidence-bound restoration remains a separate operation.

## Deliberately unavailable roles

`scripts/archive_map_availability.json` is a required, hash-pinned dependency next to the selected `archive_map_contract.py`. It contains three map-only records from published commit `89de62198fb8dd7c62ae0289fcd839d064a15c51`:

- 260630 / 51410138: start, end and representative remain unavailable; preserve the literal single-map URL.
- 260709 / 51513023: start and end remain unavailable.
- 260722 / 51407415: all four map roles remain unavailable.

Each record binds the exact date, management number, label, unavailable role set, and public map projection hash. The source commit, blob SHA-1 and full HTML SHA-256 document provenance and are checked during tests/adoption. Runtime validation checks the fixed JSON hash and the current map projection, so non-map text changes do not invalidate map preservation.

A matching record only suppresses GPS-derived or inferred values for its named unavailable roles. Contradictory explicit coordinates or URLs stop. Existing known-role conflicts and the general role-addition guard remain in force. Missing/changed identity, exact label, baseline, or projection also stops. Historical corrections that remove a recorded case or establish new coordinates require an explicit reviewed contract update; do not relabel or unpin records to make a run pass.

The JSON is mandatory even for dates with no special record. A missing same-directory dependency must not fall back to another checkout. The company wrapper pins generator/helper/JSON, captures verified bytes before execution, and passes the captured JSON to the helper. Package all three together and rebuild the embedded wrapper. The snapshot builder pins helper/JSON and its source contract pins the builder.

## Verified scope and limits

Normal map preparation with real company GPS preserved the exact published roles on all 22 conventional repaired dates using both public and company candidates. Three immutable ledger aliases retain their separate route. Unknown coordinates remain unknown. Historical business exports were not recreated, so these 22-date tests are map-only projection, not historical business E2E.

The confirmed 261111 export and saved forms were checked through installed and candidate compiled wrappers in an isolated copy. All 842 resulting files matched between routes and on repeat; the confirmed export, GPS and fixed forms were unchanged. Two existing normal-generation differences from the initial public copy were identical under installed and candidate code and were not published.

The source and small EXE candidates are not adopted. Formal full-runtime backup, apply/rollback/reapply checks remain blocked by insufficient local capacity. Do not weaken those guards or discard recovery copies. Real browser behavior remains unverified because the official UI connection failed. No new source publication or page publication is included in this candidate validation.

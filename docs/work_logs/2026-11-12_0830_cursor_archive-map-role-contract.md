# Work log: Preserve historical archive map roles

Date: 2026-11-12 JST. Branch: cursor/archive-map-role-contract-20261112.

## Changes

- scripts/archive_map_contract.py: preserve a validated historical representative independently from endpoints; reject implicit additions to the published map projection.
- scripts/test_archive_map_contract.py: add representative, unknown-role, repeated single-endpoint, and pre-output failure regressions. The URL equivalence fixture retains its original intent with an explicit known representative; the former single-only fixture is now an explicit rejection test.
- scripts/archive_snapshot_builder.py and portal/archive/archive-v2-r1/contract.json: update only the hashes corresponding to the changed dependency chain.
- docs/operations/archive-map-role-preservation.md: document the bounded behavior and deployment limitation.

## Verification

- Existing public baseline: 27 tests passed with UTF-8 mode.
- Candidate map contract: 40 tests passed on both public and bundled-company generator paths. The company adapter supplies its mandatory repo-root argument and synthetic script marker without weakening guards.
- Scope and area regression suites passed on both routes; immutable-alias map tests passed.
- All 13 snapshot outputs from the current and candidate builders were byte-identical.
- The company wrapper selected the expected bundled generator/helper and completed the real help bootstrap receipt. Old or modified helpers, old wrapper/new helper combinations, old snapshot source contracts, and old builder dependencies were rejected.
- Read-only projection of the 25 repaired dates: 20 conventional dates preserve the published MapView; two dates stop safely rather than add unverified roles; three immutable aliases remain separate.
- Initial local test failures were retained: default CP932 fixture encoding, one new CLI fixture missing its explicit GPS argument, and public CLI fixtures missing the company-only mandatory argument. Corrected invocations/adapters passed without removing assertions.

## Limits and state

No database changes, business export recreation, fixed-form changes, page publication, EXE rebuild, or live adoption were performed. Browser state could not be obtained because the official UI connection process exited unexpectedly. Two historical dates still need an explicit evidence-bound unavailable-role contract before unrestricted normal regeneration is possible. Historical business exports are absent from the default company directory, so map-only projection is not business regeneration E2E.

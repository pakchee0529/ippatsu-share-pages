# Archive map backfill source and snapshot compatibility

Date: 2026-11-11
Repository: ippatsu-share-pages

## Scope

Add the hash-bound map-only repair CLI and tests for 261028 and 261030. It preserves existing maps and all non-map business bytes, validates historical public pages against GPS, and executes captured verified helper bytes rather than cached bytecode. This CLI is separate from the company runtime generator.

Add explicit map-page generation for the fixed-form archive aliases 261104, 261105 and 261106. Normal snapshot generation only validates the already-generated map pages and updates references. Its output remains the existing six-file per-date contract. The source-contract key set is unchanged; only the reviewed builder LF hash changes. New dependencies are hash-verified before import. Original saved-form aliases and their fixed forms are not edited.

## Verification

- Map-only suite: 36 tests passed, repeat generation matches reviewed outputs.
- Existing archive map contract: 27 tests; completion scope: 9 tests; area-unit: 7 tests passed.
- Alias suite: 20 tests passed. Three explicit maps and three normal snapshot runs reproduced the frozen outputs.
- Independent company-wrapper checks: four dates, exact six-file outputs and receipt readback; ten missing/conflicting-map or dependency-change cases stopped without partial output. Two stale-pyc cases used verified source bytes.
- Existing share map-control checks passed.
- No DB writes, business re-export, new saved forms or company runtime replacement.

## Limits

No actual browser clicks, printing or GUI/EXE startup were verified. Older May-July map pages are outside this publication batch. A pre-existing full snapshot layout/TOP comparison failure is not counted as a pass.

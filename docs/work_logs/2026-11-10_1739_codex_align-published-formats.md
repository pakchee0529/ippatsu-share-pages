# Align currently published page formats

The user requested comparison against the adopted format and correction of published pages that drifted.

## Limited generated changes
- Six ordinary pages for 2026-11-11 and 2026-11-12 now refer to the already-adopted 20261110 transport asset generation. Only the version strings differ.
- Archive viewers for 261027, 261028 and 261029 use the current builder CSS union and catalog version. Viewers for 261104, 261105 and 261106 change catalog version only.
- Case/config data, ordering, quantities including null/zero, conditions, maps, notes, embedded cases/days/JavaScript and immutable saved forms are unchanged. No DB writes.
- The authority is the approved 11/5 correction-versus-change contract, PR23, and the adopted design-number/transport display changes. The date of an example is not a reason to roll back current software.

## Verification
- Generated twice through the existing normal-page transformer and archive builder; exact repeated output.
- Eight existing regression suites passed, including archive layout, transport, bush dimensions/cards, TOP visibility, empty dates, headings and area units.
- The audit checked 75 live URLs against the baseline commit and 256 linked HTML files/2,360 internal links with no missing target.
- Twenty immutable form files remain unchanged. Eighty-seven legacy completed dates without saved form originals remain legacy; no historical data was inferred.
- Browser initialization failed, so visual desktop/narrow-screen checks, actual printing and production saving are not claimed.

## Source inventory
The shared-ledger SOURCE-HASHES file is a historical PR23 adoption inventory, not an active runtime integrity lock in the inspected code. It remains unchanged rather than rewriting historical evidence.

## Publication
Publish only these twelve generated HTML files and this work log after final source-scope verification. Verify the exact deployment commit and HTTP bytes after publication.

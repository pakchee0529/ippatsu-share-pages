# Restore maps and map navigation on five archive dates

Date: 2026-11-11
Repository: ippatsu-share-pages

## Generated output

- 261028: restore six missing overall-map representative points; preserve all eight existing cards and their single/two-point maps, including the two existing representative points.
- 261030: restore three cases' single, two-point and overall maps from same-date historical page evidence checked against GPS.
- 261104, 261105, 261106: add separate map pages for eleven cases and connect the saved-form viewer/catalog references to them. Original index aliases and saved forms remain unchanged.
- Regenerate only the relevant archive index/catalog and three views. Unrelated views, including 261111, remain unchanged. Their catalog-version field is a cache-bust query, not a response-hash constraint.

## Checks and boundaries

All ten generated public files match the reviewed candidates. The alias builder's normal output-set contract remains unchanged. Quantities, completion state, photos, original coordinates, fixed forms and business data are preserved. No schedule or completion registration was repeated.

Two generated view files retain their existing CRLF format. Plain git diff --check flags their unchanged CR line endings; the CR-at-EOL-aware whitespace check passes. The fixed output bytes were not reformatted to hide the lint result. Actual browser/map-click and print operation remain unverified.

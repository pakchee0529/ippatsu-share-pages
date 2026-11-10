# Work log: Fix archive area unit

- Found an existing mojibake suffix in _archive_m2_expr while checking the approved 2026-11-10 completion archive.
- Changed only the area-unit literal from the corrupted text to ㎡. Numeric values, formulas, and stored business data are unchanged.
- Added seven regression checks covering both actual area formulas, unchanged numeric suffixes, zero and non-added area values.
- Source fix is committed separately from generated archive publication.

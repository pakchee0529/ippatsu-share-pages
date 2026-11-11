# Final four-date legacy map-only repair source v7

## Scope and verification

- Base: 4d98a3610503165858999f681fa5dd306a3fc190. Branch: cursor/final-four-map-only-20261111.
- Replace only the legacy adapter, fixture tests and operating contract with the independently approved standalone v7 source. No earlier revision is imported at runtime.
- The frozen all-19-date 107-test suite passed twice, and 104 additional independent checks passed. Those full suites were not repeated during this limited integration.
- Fresh CLI generation from this checkout reproduces all four approved HTML hashes. Integration checks cover 18 cards, 24 restored map roles, 28 semantic role-class additions, ordinary-reader equality, protected business bytes and retained map values.
- Existing single URL literals are preserved, including the five 260716 values. Unavailable endpoints and unresolved cases remain unavailable; no coordinates are invented.
- The exact known invalid zero payloads/points are retired only under their fixed evidence-bound exceptions. 260630 remains a partial repair.
- All 797 portal/share files remained unchanged during isolated generation. Company repository files, DB, runtime and earlier frozen artifacts were not changed.
- Ordinary prepare_archive_maps compatibility is not guaranteed: unchanged midpoint/end policy can fail closed. Browser interaction and printing remain untested.
- No push or publication was performed. Generated HTML is committed separately.

## Source provenance

Frozen source bytes are unchanged. The final document already used public-safe operational wording and contained no local paths. Git publication uses LF; raw frozen/working hashes and Git blob hashes are distinguished below.

- scripts/repair_legacy_archive_maps.py
  - Frozen input: 231d8749893485074c1d812d024578ab68b8e56b91549d8328d298025c5ed1f5
  - Public Git blob: ecb4b36303af3d1e501c882d3fc6b2febaf3f428d21cba3b66f51c97489bd02f
  - Change: identical frozen bytes
- scripts/test_legacy_archive_maps.py
  - Frozen input: 1d5cc9c824b986af2a2a9f875d9eb312d7385752955bdfae6941866fd4c28d27
  - Public Git blob: 18d668bb18764547e9a357a156c790ff5564d062b21be2546f32de53acab57ff
  - Change: identical frozen bytes
- docs/operations/legacy-archive-map-only-route.md
  - Frozen input: 5944fa71a3dbb73ae6459ff615e046d12f54581c6c2b62d1646bc6a8ab6310c6
  - Public Git blob: 5b225a0f7a9d2c6a4d0cc48e8fe242e5587bb929c8da6c8a469f3902ec7aaa65
  - Change: identical frozen bytes

Private manifests, reports, inventories and preparation scripts are excluded.

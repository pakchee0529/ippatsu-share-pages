# Verified legacy archive map-only route v4

## Scope

- Add the reviewed legacy map-only repair tool, fixture test driver and operating contract.
- Base: 71234bc370b625b58655c8c5888670708784f2ef. Branch: cursor/legacy-map-only-v4-20261111.
- No business exports, event registration, DB, company runtime, saved forms or navigation are changed.

## Verification

- The previously frozen v4 implementation passed 65 tests and independent review. That full suite was not rerun for this integration.
- Fresh CLI generation from this checkout reproduces all 15 approved HTML hashes: 69 cases and 236 recovered map roles.
- Non-map business bytes, quantities, status text, form links, existing map values and runtime code remain unchanged. The sole retained-control markup exception is 85 appended semantic role classes.
- Ordinary map reader results match every actual MapView. Ordinary prepare_archive_maps still fails closed on retained midpoint versus GPS-end representative policy conflicts. This does not constitute company runtime adoption.
- All 797 portal/share files remained unchanged during source integration and isolated generation. Generated pages are committed separately.
- Browser interaction and printing were not performed. No push or publication was performed.

## Source provenance

SHA256 values below distinguish the frozen input bytes from Git publication bytes. Python source logic is unchanged; Git stores LF line endings. The operating document changes only internal handoff wording to normal publisher terminology.

- scripts/repair_legacy_archive_maps.py
  - Frozen input: df5bec7bb9f5e36cea2b4b2ede4c02bcd211bece919be1d12a149038d3c91bcf
  - Public Git blob: fc3ce02cbac0fbfa9543161c2f58a47db20d60e52f0b57a646f76d6fe2913990
  - Change: identical frozen bytes
- scripts/test_legacy_archive_maps.py
  - Frozen input: 45c94c52af7fe306afa45a6b2ed8b8962cb5dbe4c19392b336ff50fb6f8ce1f9
  - Public Git blob: 064a7a1f1fc3a8c11787652f7d4400a05d01ad1c8d5c92d8f720ce857ff4dccd
  - Change: identical frozen bytes
- docs/operations/legacy-archive-map-only-route.md
  - Frozen input: 40da349c888b1c72cbe300e0036f0fd626c086ceb81dc7fc93430b6ee858b137
  - Public Git blob: 88adb470e3339a3f43e7b20967b379caa1f9afd466fd3402d80219e19c5e724d
  - Change: operational wording only

Only these implementation files and this work log are included. Private manifests, reports, local paths and preparation scripts are excluded.

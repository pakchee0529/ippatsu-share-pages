# Work log: Preserve evidence-bound unavailable archive map roles

Date: 2026-11-12 JST. Branch: cursor/archive-map-role-contract-20261112. This follows the bounded V1 source commit b9da1c9fd9cd16546063369165e44dce8084f108; its historical work log is unchanged.

## Changed paths

- scripts/archive_map_availability.json: three map-only availability records with exact public provenance.
- scripts/archive_map_contract.py: strict JSON validation, identity/label/projection binding, unavailable-role suppression, and independent output verification. The general role-addition guard remains.
- scripts/generate_portal.py: load the same-directory contract in map preflight and pass it to resolution.
- scripts/verify_archive_pages.py: verify the rendered contract independently and apply it to source-map checks.
- scripts/archive_snapshot_builder.py and portal/archive/archive-v2-r1/contract.json: dependency hash chain only.
- scripts/test_archive_map_availability.py: 17 tests including provenance, conflicts, missing dependencies, captured bytes, repeat projection and rendered output.
- docs/operations/archive-map-role-preservation.md and this work log.

## Verification

- Map contract: 40 tests passed on public and company routes.
- Availability: 17 tests passed on each route, with no provenance test skipped.
- Scope and area suites passed on both routes; immutable-alias tests passed.
- Snapshot builder produced 13 files byte-identical to the installed baseline builder output.
- Normal prepare_archive_maps with actual company GPS preserved published roles on 22 dates in each route. Three ledger aliases use their existing separate route. This was map-only projection, not business export fabrication.
- Independent verifier passed for 260630, 260709 and 260722. It warns that retired pre-retirement pages were not supplied for this particular invocation; exact historical provenance was checked independently against pinned Git blobs.
- Company wrapper actual bootstrap passed. Missing/changed JSON, helper and generator; an old wrapper/new candidate combination; and JSON changed between parent selection and child execution were rejected. Captured valid bytes were retained after a later disk change; unverified changed bytes were rejected.
- Independent read-only review found no major defect. The reviewer noted the mandatory JSON packaging and intentional stop on future changes to recorded identities/labels.
- Small EXE reconstruction changed only app.share.portal_execution: 1409 other modules, bootloader, non-PYZ content and final_ledger_archive remained identical. Two builds were byte-identical.
- Confirmed 261111 export, saved forms, and actual company GPS were used in an isolated copy. Installed compiled wrapper, candidate compiled wrapper, and candidate repeat produced identical 842-file results; source export, GPS and fixed forms remained unchanged. Frozen selection was tested for the generator; snapshot phase used normal external Python with a private state directory, matching the existing test procedure.

## Retained failures and recovery

An out-of-space write interrupted only the private helper candidate. It was restored byte-for-byte from the preceding local commit, then atomically rewritten after capacity was rechecked. Installed files and public pages were not altered. An early availability test used a date-bound alias renderer for an unrelated synthetic date; the test fixture was corrected without changing the production guard. The first isolated snapshot test kept frozen mode with a new state directory lacking Python; it stopped safely. Correcting the private test setup to the existing procedure passed. Failed logs were retained.

## Limits and publication state

No database writes/re-export, business registrations, schedule changes, fixed-form edits, live adoption, GUI launch, push, merge or new page publication were performed. Published 25-day repairs remain unchanged. The candidate is not a complete historical business-regeneration E2E result because old business exports are unavailable. Real browser checks remain blocked by the official UI connection. Formal runtime update requires more free space for existing backup/rehearsal guards; these were not reduced or bypassed. No recovery files were deleted or moved to shared storage.

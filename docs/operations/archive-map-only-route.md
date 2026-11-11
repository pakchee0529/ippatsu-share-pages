# Legacy archive map-only candidate route (v2)

Status: isolated candidate implementation, NOT adopted in company runtime. No DB, completion event, business export, saved form, catalog, or viewer writes. Never replace the company generator (its independent company-repo-root contract remains intact).

## Inputs and trust boundary

- CLI requires --manifest, --repo, --scripts, --gps, --output.
- Manifest schema archive-map-only-v1 binds every date to full commit, exact archive/share path, Git blob SHA-1, SHA-256, current checkout SHA-256, and explicit identity -> missing role list. Pins all three imported helper modules and the canonical GPS file. Helpers execute directly from the exact hash-verified bytes using compile/exec, never cached pyc or a second filesystem source read. The same verified bytes supply renderer AST literals. GPS is also read once, hash-checked and decoded from those exact bytes. Preloaded untracked helper modules are refused; later reuse must match the recorded module objects, paths, bytes and locks.
- Only ordinary portal/archive/YYMMDD/index.html is a target. Evidence is share/YYMMDD/index.html at a pinned historical commit. Read-only git show independently rechecks commit/path bytes on every run.
- The current published Git blob is the byte-preservation baseline. Checkout CRLF transport is separately hashed and accepted only if newline normalization yields the exact same published content. Output preserves the original published blob's non-map bytes, not a reformatted export.
- Current title/date, unique management number, exact full span, current/source identity set, endpoint roles and canonical GPS must agree. Existing map roles are immutable; the manifest must exactly list missing roles. In v1 both endpoints must be missing together or retained together.
- Retained representative points can differ from the historical choice of endpoint, but must still equal a GPS-validated endpoint. This is recorded as retained data, never silently rewritten. Current and original single URL must agree when retained.
- Unknown DOM, duplicate IDs/attributes/cards, malformed tags, fixed-form aliases, incomplete evidence, unsafe/non-coordinate Google map URL, missing GPS, source/GPS conflict, changed hashes, partial/extra/duplicate role scopes, unknown JavaScript handlers, and changed helper implementations fail closed. Symlink/reparse points in input paths or the output parent chain are rejected.

## Processing

1. Read phase parses missing maps without asserting they have already been repaired. It does not loosen archive_map_contract.py.
2. Build the exact expected projection from retained current roles plus explicitly listed missing roles from historical evidence.
3. Reuse only map-only helpers: _archive_single_map_button, _share_two_map_button, _share_two_map_panel, build_two_geo_payload, format_two_geo_script, json_for_script_tag. Reuse the map-section literal from the hash-pinned archive renderer. Do not invoke the business page renderer.
4. Replace only missing controls, insert their map JSON/panel, and update overall points/container. Existing cards are not reconstructed. No JS handler code is rewritten. The established handler signature is SHA-256 pinned with only its overall-points JSON removed.
5. Run unchanged verify_rendered against the composite projection and verify_preserved against both current and composite maps. Strip only designated map nodes/overall array and require all remaining UTF-8 bytes to match.
6. Validate the entire batch before writing. Write only a new separate staging directory and rename to the new output directory. Existing output and output inside the input repo/resources are rejected. No partial batch is written to the target repository. I/O interruption can leave a hidden staging directory, which is not an approved candidate.

## Verification

Run test_map_only.py with explicit environment variables MAP_REPAIR_TEST_OUTPUT_ROOT, MAP_REPAIR_TEST_REPO, MAP_REPAIR_TEST_MANIFEST, MAP_REPAIR_TEST_GPS. Use a private test directory and the supplied two-date private evidence manifest. The test fixture is based on pinned public historical pages, with negative mutations for wrong date/identity/span, malformed DOM, bad URL, missing evidence/GPS, coordinate conflict, duplicate scopes/controls/IDs, unknown handlers, hash mismatch, alias rejection and batch atomicity.

Independent checks compare all tables, quantity cells, status text, titles, management numbers, saved-form links, and final-ledger section. All eight 10/28 card blocks must be byte-identical. Runtime code is byte-identical after removing only overall point data. All two-map DOM references resolve to the expected payload/panel IDs. Source repository files are hashed before and after tests.

Actual browser/map-click/printing verification is NOT performed. Static/synthetic success does not establish UI operation.

## Currently supported targets

- 261028: eight retained business cards. Add six missing representative points only; preserve both retained representatives and all eight existing single/two controls and endpoint names, including legacy full-span names.
- 261030: three retained business cards. Restore single, start, end and representative for all three from same-date share evidence.
- The older nineteen May-July dates are NOT supported by this adapter. Eighteen lack the modern single control, 260722 lacks its two control, and their control layout requires a separately reviewed adapter. Verify the existing handler signature per page with point data excluded, reuse its exact selectors/schema, explicit evidence joins/exclusions when source has extra cards, per-role GPS checks, and the same non-map-byte invariant. Never broaden this parser or replace their JavaScript wholesale.
- 261104/261105/261106 fixed-form aliases are intentionally excluded. A separate map page/navigation design is required.

## Integration and publication

Only repair_archive_maps.py, test_map_only.py and this document are eligible implementation artifacts. Private manifests, inventories, reports, scratch scripts and absolute local paths are not publication artifacts. An authorized publisher reviews these files, repeats generation in a separate checkout/output, compares candidate hashes, and controls any authorized publication. Runtime adoption is a separate explicit step.

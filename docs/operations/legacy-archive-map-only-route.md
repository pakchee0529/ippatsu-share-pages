# Legacy archive map-only adapter v4

Status: isolated candidate, not adopted in the company runtime. This tool does not read business exports, write to a DB, reconstruct quantities/status/ledger data, change saved forms, change navigation, or publish. The existing modern strict guard remains unchanged.

## Trust boundary

The private manifest binds each date to a full current commit, archive path, Git blob SHA-1 and SHA-256, current checkout SHA-256, full historical source commit/share path/blob/SHA-256, exact date/management-number/full-span join, explicit missing map roles, explicit source exclusions (including each identity, span and reason), and roles not evidenced in either original/current maps. All helper files and canonical GPS bytes are hash pinned.

The adapter loads the pinned modern v2 helper from verified source bytes with compile/exec. Modern v2 likewise executes its three hash-verified helper byte strings directly and loads GPS from its single verified read. Bytecode caches cannot replace verified sources. Reparse/symlink inputs and output ancestors are refused. Import module/path provenance must remain tracked on reuse. A fresh process is required after changing dependency roots.

Current pages are parsed as whole strict DOMs. The supported controls are legacy btn-map anchors, legacy buttons with data-two-open, explicitly disabled two-map buttons, and modern single/two controls. Missing controls and exact numeric 0,0 endpoint/overall sentinels are read as absent map roles, not valid coordinates. Other invalid coordinates or unknown layouts are rejected. The known current JavaScript handler is SHA-256 pinned with only overall point data omitted. Existing handlers are never rewritten.

Historical source HTML has a known damaged non-map heading in several fixed blobs. Source business chrome is not an input. The dedicated source reader verifies the unique date title, counts all article boundaries, checks page IDs for collisions, parses every complete card fragment strictly, and joins the sole points array by management number plus exact full span. The earliest source has no management numbers in POINTS, so the entire exact span must uniquely identify one card. It never repairs a source page or trusts an observation-only audit projection. Source map binding and payload structure must still be valid. Header anomalies are recorded in the private manifest.

Every retained source/current endpoint is checked against canonical read-only GPS, including its name. Single-map URLs and overall points must equal a GPS endpoint or arithmetic midpoint of that same full span. Missing roles are restored only from the fixed original source. Existing map values remain unchanged, including current full-span endpoint names. V1 additionally requires current/source single URL agreement and literal full-span agreement; explicit whitespace-only or endpoint-versus-midpoint policy adapters belong to later revisions.

## Repair and verification

Only missing controls/endpoint objects/overall point objects are inserted or replaced. Valid existing single controls, endpoint object bytes, representative object bytes and JavaScript are preserved. Existing two-map panels and binding IDs are reused. New controls/payloads use only the pinned map-only helper functions. No business renderer is called.

The reader and strict validation projection are separate. The validation-only in-memory projection gives legacy controls modern role classes and represents known missing values with disabled controls. It is passed to the unchanged modern verify_rendered/verify_preserved guards, but is never written. Actual output is independently reparsed and checked against the exact composite role projection. Every non-map byte, including quantities, tables, statuses and form links, must match the pinned current page.

All requested dates must pass before any candidate HTML is written. A complete batch is staged and renamed into a new separate directory. Existing output and output under the source repositories/resources are refused. An I/O interruption may leave an unapproved hidden staging directory. A stopped date is never silently skipped by the production entry point: the caller first reviews the all-date private preflight report and explicitly chooses the passing batch manifest.

CLI arguments: --manifest, --repo, --scripts, --gps, --modern, --output. The caller supplies read-only input paths and a new isolated output path. No runtime adoption or publication is implicit.

## Tests and delivery boundary

The test driver uses LEGACY_TEST_ROOT, LEGACY_TEST_REPO, LEGACY_TEST_MODERN, LEGACY_TEST_GPS and LEGACY_TEST_MANIFEST environment variables. Real pinned date fixtures, wrong identities/dates/spans, ambiguous source controls, malformed/unknown DOM, changed runtime, unsafe URLs, coordinate/GPS conflicts, incorrect manifest scopes, batch failure/no partial output, repeat generation, preserved business content and all source-repository files are checked. Modern v2 has its own separate bytecode-cache, read/hash/execute swap and GPS single-read tests.

No real browser interaction, map click or print verification was performed because browser connection is unavailable. Static success is not an interactive UI claim.

Only repair_legacy_archive_maps.py, test_legacy_archive_maps.py and this document are implementation artifacts eligible for authorized review/publication. Private manifest, reports, preparation/inspection scripts, inventories, local paths and candidate reports must not be published. Only an authorized publisher integrates and publishes the approved HTML. Keep stopped dates untouched and retain their exact failure evidence.

## Explicit v2 extensions

V1 remains frozen separately. V2 adds only these contracts, with separate manifests and candidates:

- Span identity equivalence removes whitespace only. It does not change pole numbers, direction letters, punctuation or words. Normalized span collisions are refused. Current display bytes stay unchanged. Restored representative names use the unchanged current display span while their coordinates remain directly sourced from the pinned original point. Literal original/current names and their join remain in the manifest/report.
- A retained current single URL may select a GPS endpoint when the source selected the same span's midpoint. Both are independently GPS checked; current anchor and URL bytes are retained. Every such pair is explicitly enumerated in the manifest and report. Unknown coordinates still stop the date.
- On the fixed 260529 legacy layout, cards without note panels receive missing map payload/panel at the card tail and their missing two control beside the retained single. No note/status/quantity content is created or modified.
- On the fixed 260722 source layout only, the known off-by-one UI binding is recorded as an original defect. The own-card unique payload ID and own-card panel/canvas IDs must exactly follow their card index; the erroneous control must point to index minus one. Only payload endpoint evidence is used. Other offsets or structures are refused. Output bindings always use the strict current-page contract and cannot use this source exception. The original no-coordinate card remains unchanged with unavailable roles explicitly reported.

The extra date with a corrupted source point name remains stopped, as do source duplicate controls and non-whitespace word differences. V2 does not silently repair these source defects or fabricate map evidence.

## V3 strict actual-DOM correction

V1/v2 candidates were independently byte-reproduced, but negative tests exposed unrecognized hiding attributes and handler nodes that their reader did not reject. They are historical candidates, not approved tools. V3 checks actual overall-map DOM against the literal from the verified helper source; exact single/two control tag, class, attribute and caption contracts; JSON script and div panel/canvas schemas; visibility ancestors; empty panel structure; and complete accounting of all handler/map nodes, including nodes outside cards. Source payload-only exceptions do not relax these structural contracts. Modern helper module metadata and its exact verified source bytes are checked again on cache reuse. Ordinary modern parse_page is not claimed to accept legacy class bytes directly; actual legacy DOM is checked independently before validation-only projection.

## V4 explicitly approved semantic-class exception

Actual output retains every existing class token and appends only btn-map-single or btn-map-two when that role class is absent. This is the sole exception to byte-identical retained map control markup. Each addition is listed in the private receipt with identity, role and before/after class. URLs, coordinates, names, other attributes, payloads, panels, JavaScript and non-map bytes remain unchanged. Actual ordinary parse_page must return exactly the same complete MapViews as the dedicated actual reader. Prior frozen eleven-page candidates must differ only by these exact class additions.

This improves ordinary reading but does not claim ordinary prepare_archive_maps regeneration is compatible. The unchanged resolve guard combines retained midpoint representatives with GPS end representatives and raises a conflict rather than silently dropping them. No representative is rewritten to make that guard pass. Normal runtime adoption/regeneration is a separate task. The source-less zero-point card on 260722 is on hold, not silently deleted.

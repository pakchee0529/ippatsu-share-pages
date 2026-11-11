# Compatible immutable-alias map navigation

## Scope and design

- Baseline: public source 0a8a4239fa89dd01d252a4f1d8ae068abdcb9a2e; map-only evidence covers 2026-11-04, 11-05 and 11-06, eleven cases.
- A dedicated archive_alias_map_pages.py CLI generates the three reviewed map.html sidecars into a separate staging directory. Its output is exactly the already verified public map bytes. Original alias index.html files and saved ledger/instruction pairs remain untouched.
- Ordinary archive_snapshot_builder.py never generates sidecars. It requires the preinstalled repository sidecars to match fixed byte hashes, dates, management numbers and complete span labels before writing catalog/assets/index/view. Missing or changed maps fail closed even when rebuilding another date because the shared catalog references all three days.
- The company wrapper's existing three-source contract and exact ordinary output set are unchanged. The source contract updates only the builder's justified LF SHA-256. The pinned builder verifies its new module, public map-only configuration and existing map-contract helper before importing them, and executes Python dependencies from the verified bytes rather than bytecode caches.
- Map configuration contains no quantities, business status, receipts, revisions, photographs, internal identifiers or private paths. Original published map URLs and endpoint/overall roles remain exact. Canonical projection hashes prevent a retained source-blob label from authorizing altered coordinates or URLs.

## Verification

- Twenty public/synthetic unit tests passed.
- The current company archive_snapshot_publication and portal_execution source bytes were executed unchanged with an isolated repository and new private data root. install and verify_record succeeded for 261104, 261105, 261106 and non-target 261111. Each stage contained exactly six legacy-owned outputs: archive index, four assets and the selected view. All four records remained verifiable after the full sequence.
- Eight actual-wrapper negative cases passed: missing target map, missing map during another-date regeneration, conflicting map, altered module/config/helper/builder/source contract. All were rejected with zero staged or installed files; restored inputs left all four accepted records verifiable.
- The explicit map CLI produced exactly three files, repeated byte-identically, matching the previously verified map bytes.
- Full portal hashes were compared around the successful installs and again after negative fixtures. Immutable aliases, saved forms, map sidecars and all unrelated files remained unchanged. Catalog business fields remained exact; only the eleven approved reference_href values changed.
- The 261111 view regeneration was a compatibility test only and is excluded from the proposed publication set. Its business content remained unchanged. The proposal contains only the three target views, central catalog/index, sidecars, source files, contract and this log.
- Company runtime/EXE, database, existing private state and adopted checkout were not changed. No GUI EXE, browser or public HTTP acceptance is claimed. Publication is a separate reviewed step.

## Reproduction and installation order

1. Put the reviewed source/config changes in an isolated public repository. Run archive_alias_map_pages.py with --repo-root and a separate --output-root. Verify the three map file hashes and copy only those sidecars into the isolated repository.
2. Verify the exact SOURCES3 contract and the builder's transitive dependency pins. Use the existing company source wrapper to install the ordinary snapshot view for each target day, with a new private data root. No wrapper output allowlist change is needed.
3. Compare the fixed-form and unrelated file hashes, central and embedded catalog contents, and the exact proposed publication manifest. Keep the non-target-day compatibility-test output out of the publication delta.
4. Apply/publication and browser checks remain separate. Do not re-export business data or regenerate saved forms from old share pages.

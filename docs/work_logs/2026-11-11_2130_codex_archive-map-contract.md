# Work log: Preserve archive map evidence

- Repository: ippatsu-share-pages; branch: cursor/archive-map-company-20261111.
- The user requested the archive map correction and approved publication to the existing shared site.
- Added identity-bound map projection and verification for completion archives. Match date, management number and full pole span; reject duplicate identities, conflicting coordinates and invalid explicit inputs before output mutation.
- Resolve archive GPS from the explicit data root rather than the output repository location. Preserve original single URLs, endpoint roles and overall-map points independently; do not fabricate a second endpoint.
- Keep the current ordinary page and prior archive as map-only evidence. An explicit prior root must contain YYMMDD/index.html. Missing historical evidence is reported, not treated as proof of preservation.
- Fixed snapshot aliases and immutable saved forms remain separate from legacy map cards. Source completion data is not rewritten.
- Updated generator, verifier and map/scope tests. Source and generated-page changes are recorded in separate commits.
- Checks: map 27, completion scope 9, area 7, ordinary share-map controls, syntax and whitespace. The existing snapshot layout test has the same stale archive TOP failure on an unchanged baseline; this is not counted as passing. The scoped real-input pipeline was verified separately.
- No business database changes, credential changes or new public destination. Actual browser interaction and printing remain unverified because the connection could not initialize.

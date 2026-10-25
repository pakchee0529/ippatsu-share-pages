# Ledger v5 production adoption

User-approved v5 input and saved-ledger views now share one projection, quantity calculation and print-order implementation. Day generation installs the same instruction/daily templates for GUI and CLI. Backend v1, authorization and expected_revision CAS are unchanged. No database save or fixture data is included.

Input adds explicit quantity-linked versus record-only change details, preserves manual offsets and prior records, stops incomplete linked changes from saving, and retains drafts when POST outcome/readback is uncertain. Allocation preserves hand entries and supports generated-row replacement/undo. Expenses use photo-number application independently from equipment t/m. Eight-photo rows, fixed-one versus E10/N10 counts, blue additions and deferred calculator folding match accepted v5.

Saved views use actual saved documents only, refresh without stale-response replacement, preserve existing condition/table order, and distinguish missing values from zero. Day photo numbers and revision diagnostics are omitted. TOP, OJT, other published days and demos are unchanged.

Validation: production browser 35 checks at each 390/1100px; allocation14, photos7, fixed-one14; adopted print-order36; actual frozen GUI/CLI generation and publication allowlist6; generation/static5. Synthetic POSTs only; actual revision8 read-only. No physical printing or user-phone test.

Restore: restore only recorded files from the private before-v5 backup or revert these adoption commits through normal review; no DB rollback required. Existing API/documents are retained. Do not restore unrelated OJT changes.

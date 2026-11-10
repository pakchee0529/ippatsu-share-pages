# Work log: Completion archive count synchronization scope

- Date: 2026-11-10
- Repository: ippatsu-share-pages
- Status: Candidate prepared and tested in isolated outputs. Publication is handled separately.

## Files

- scripts/generate_portal.py
- scripts/test_completion_archive_scope.py

## Change

The completion-archive mode now passes its already validated target date into the archive manifest count synchronization function. That function skips all other dates before reading their exports. Full mode and share-update retain their existing unscoped synchronization behavior. Focused modes retain their existing early-return path.

This preserves every out-of-scope manifest entry, including an explicitly stored planned_incomplete_count of zero. The change does not alter completion data, saved forms, identifiers, permissions, or the archive rendering format.

## Checks

Nine synthetic regression tests cover target counts, preservation of complete other-date dictionaries, zero preservation, repeated byte-identical output, legacy all-date behavior, absent/corrupt input, unknown date, no explicit export, and actual main dispatch for full/share-update/completion-archive modes.

The company route is validated separately against the corresponding local candidate and existing fixed-form fixtures. No generated HTML belongs in this code change.

## Existing limits

The existing strict summary option rejects count disagreement only when a summary row for the target date is present. It does not require such a row or validate a missing/malformed summary. A failed generation may leave intermediate local output. Publication must remain conditional on successful generation and the final allowed-difference checks; failed runs must not be published.

## Publication

This preparation did not commit, push, merge, or publish. Keep the source change and generated-page change separate and use the authorized publication route.

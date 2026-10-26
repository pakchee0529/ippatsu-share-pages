# Saved ledger continuity after schedule moves

Current case/management/basis/revision checks remain in force. A saved document from another valid work date is retained for the same current case, without automatic POST, revision reset, or photograph date changes. Explicit saves already use the current case date and expected_revision. The view labels the current scheduled date separately. The shared GUI/non-GUI generator uses the same versioned assets. Empty moved-away dates remain accessible but are excluded from current TOP entries.

Tests: 9 isolated module regressions, 8 actual-document/read-only checks, 3 TOP regressions and 19 browser checks at 390/1100px including offline reload. No new API/DDL/auth/permissions.

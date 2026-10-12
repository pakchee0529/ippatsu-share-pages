# Fix numeric date heading corruption found by deployed browser QA

Browser QA found the rendered heading was P26年10月13日, despite the document title being correct. The existing generator replacement rf"\1{title}\2" concatenated backreference 1 and the initial digits 20 into octal escape \120 (P), deleting the h1 opening tag.

Changed normalization to a callable replacement, preserving group boundaries and h1 markup. Added a regression test for October 13 and January 1 and repeated normalization. Both pass. Source-only commit; generated output follows separately. This is the root cause of the date heading corruption, not the missing-ledger generation path.

All four case identities, instruction tables, notes, quantities, ledger query values, recovered geos and live overlay remain checked. No DB, photo or draft mutation.

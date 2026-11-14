# Monday normal-format adoption

Scope: 261116 only. The owner requested the ordinary shared-page, daily view,
instruction view, and ledger route using the adopted format. Other days stay readonly.

Retire only the three Monday entries from weekly_readonly_outputs.json. Preserve
all other output and shared-asset hashes. Record the exact old and new Monday
output hashes in weekly_normal_adoptions.json. The existing portal guard accepts
that exact transition only and still calls the ordinary output validator.
No API, credentials, business data, browser protections, or other-day output changes.

Seven isolated dispatch tests passed, including changed-content/wrong-date rejection
and normal-validator result preservation. The current normal generation entrypoint
produced all three Monday outputs byte-identical to the reviewed candidate.

Publication and live-origin acceptance are not claimed by this preparation log.
Rollback must restore these scoped source files and the three prior Monday outputs
together after checking subsequent changes. Do not rewrite unrelated commits.

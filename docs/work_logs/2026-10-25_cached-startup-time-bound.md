# Open verified cached drafts when an online connection stalls

A device may report online while the startup GET never completes. If a verified case snapshot already exists, bound that startup wait to1.5seconds and then open its retained draft. First unvisited offline use is still unsupported. A late GET cannot overwrite active input or submit. Manual save still fetches current case/date/base/revision and uses CAS. Explicit logical/authorization failures are not silently converted to new empty cases. Shared-source fetch also has a bounded timeout.

Pure cache/fallback10 and real-browser stalled-response4 passed, including late-response isolation and revision conflict before POST. Browser synthetic API only; production POSTs0. Cache generationv5n2 is not yet published, so this patch is included atomically with that pending generation. No quantity/document/API/schema/authentication change. Recovery uses the paired offline rollback procedure and before-startup-bound backup.

# Reject uncached stale module generations

Keep exact prior-generation static caches for already-open tabs, but return an explicit 503 for an old version absent from all owned caches. Never fetch a current body under an old module query. A missing current static module similarly fails closed; navigation may fetch a fresh shell online. No API cache or business writes.

Real browser offline18 + complete restart3 passed with generation-hit/miss checks. Existing input/CAS behavior and generated pages are unchanged. This is the final narrow cache-policy guard for the offline restoration release. Production POSTs0.

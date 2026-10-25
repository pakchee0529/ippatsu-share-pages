# Keep instruction/day input links on the loaded shell generation

Readback found an old ui cache query remaining on instruction/day links, although the ordinary shared-card footer already used the current generation. Derive that query from import.meta.url in both views instead of hardcoding it. The common generation guard now rejects hardcoded numeric ui versions in modules. Publish shell generation20261025-v5n2 so existing offline caches cannot retain the old links.

Focused browser6 at390/1100px verifies both links and actual navigation without POST. Positive/negative generation checks pass. Quantity calculation, stored documents, offline/CAS/pending protection, map/condition fields and navigation layout are unchanged. The preceding unknown11 + ordinary37 + real offline18/restart3 checks remain applicable; no duplicate full tests needed for this link-only fix.

Recovery follows the existing offline-worker rollback procedure and private before-link-version backup. Do not clear localStorage or revert unrelated OJT work.

# Retired share-page navigation repair source

Base: c836fdf588192af0a69eec5e1a270cfd2690eefc. Scope is four existing 2026-10-28/29 daily and instruction pages. The user requested format alignment across all publicly available pages; broken return links are included without retiring or restoring any page.

Add scripts/repair_retired_share_navigation.py and its guard test. This is a bounded historical-navigation adapter, not a new business generation route. Input LF hashes, four allowed paths, absent parent indexes, same-day archive membership, saved-document existence and source immutability are verified before output. No DB/API access, configuration changes, normal templates or saved forms are modified. Output must be an empty external staging directory. Exact already-repaired inputs return an explicit no-op.

Validation: 62 synthetic/public-fixture checks, repeat generation equality, exact href/label-only change, unchanged config/ordering/quantities/assets, 8/3 same-day archive case sets, input hash/path/duplicate or missing link/parent-index/archive-data/immutable-source/output guards. No browser or real save was tested. Source and generated changes are separate. Publication is performed by the coordinating writer, not this preparation step.

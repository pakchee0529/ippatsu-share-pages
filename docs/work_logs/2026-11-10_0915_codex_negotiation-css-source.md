# Align published negotiation CSS with its adopted source

Add scripts/align_published_negotiation_css.py and its test. This is a bounded existing-public-asset alignment adapter, not a new business generator. It extracts the exact disabled-map CSS already present in build_negotiation_html since aef1a87 (2026-07-08). No new CSS design or business rule is introduced.

The four targets are portal/negotiation/index.html and gojo, totsukawa, yoshino/index.html. Fixed source/input LF hashes, exact target paths, unique style and insertion anchor, and duplicate/conflicting CSS guards protect the scope. Exact repaired inputs explicitly no-op. All inputs pass before writing to an empty external staging root. Normal generator source, body, scripts, config, API calls and business values stay unchanged.

49 synthetic/public-fixture checks passed, including full CSS equality with the current formal template, repeat generation, idempotence, mismatched input/source/path, conflicting/duplicate CSS, nonempty/inside-repo output and input preservation. The current static pages have no affected disabled map buttons; this closes a source/output discrepancy without changing current actions. Browser testing is not claimed.

Compatibility with source commit 12979fd7be10f149932af2819b39eaf8ae044de6: only sync_archive_manifest_counts_from_completion_export and main differ from c836fdf. build_negotiation_html source and AST are identical, and all remaining AST is identical. The adapter pins the new whole-generator LF SHA256 9e2ec2d826764c249dadfc98a0a68f5903994fb7d963b1ff4a53fbe11e78a3b3 after this proof; no wildcard or weaker hash guard is introduced.

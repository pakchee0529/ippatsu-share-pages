# Source correction: source-only print pagination

Recorded 2026-11-13 23:13 UTC; branch `cursor/weekly-normal-format-candidate-20261113`, preceding candidate `f36fa02`, PC dependency unchanged at `f693fb95fc541364b448a6f3d1833907065be183`. Both checkouts were clean at task entry. User authorized fixing the failed print layout through the formal generator/style route, protecting all 23 cases and other dates, without push/merge/publication or any workaround for the map certificate failure. Current skills and this week's acceptance history remain the format authority; this is not a replacement simplified format.

## Formal source changes

- Added `portal/shared-ledger/weekly-source-print.css`, linked with `media="print"` only by the five target source-only page sets through the scoped generator and the existing detail-template source-only option. No existing non-target page references this stylesheet.
- Retained the existing normal card/detail layout and every visible datum. A4 margins, print font/spacing, card/table/row break protection and source-only activity-section grouping keep related content on the same page. Daily cards start a new page per case. The final share card stays with the whole-map section; the map region is not hidden to suppress the known map-loading failure. Open note-panel tables have bounded print padding/font sizes so they also fit without splitting. Screen styles are unchanged.
- The common normal renderer adds `thead` and an activity wrapper only when its explicit `sourceOnly` projection is true. The default normal rendering path is preserved. Source-only module cache queries advance to `20261113-weekly-source-r2`; normal nested dependency generation remains unchanged.
- Generation now copies the print stylesheet as an explicit dependency. The output manifest binds the 15 HTML files, both source-only JS assets, the common renderer, and print CSS (19 hashes). Asset guards now validate CSS as well as JS for every protected day. No path/date/content guard was relaxed.
- Saved reusable print generation and PDF acceptance checkers (`verify_weekly_source_print.cjs`, `verify_weekly_source_pdf.py`) and extended the existing scoped tests. The browser checker now fulfills CSS with its correct MIME type; its external network interception is unchanged.

## Reproduction and acceptance

Generated independently into `/workspace/weekly-print-fixed-output-a` and `-b` through `scripts/generate_weekly_source_format.py --pc-root /workspace/ippatsu-pc-candidate --output ...`, then tested in `/workspace/weekly-print-fixed-isolated`. Repeated output is byte-identical. No generated HTML was manually edited.

Seven semantic/integrity/scope/asset tests pass. Cases/order/dates remain 3/3/5/6/6 for November 16–20, 23 total, 51407008 Tuesday only. All 345 quantities/evidence states, conditions, notes, map URLs/endpoints and representative points remain unchanged: 108 nonapplicable candidates, 53 source positives, 90 previously public formal-confirmation categories, 94 unknowns. No new source blank or candidate is certified zero. Nineteen modified and nineteen missing protected files are rejected, including the new CSS.

Print checker commands:

    node scripts/verify_weekly_source_print.cjs /workspace/weekly-print-fixed-isolated /workspace/weekly-print-fixed-open-review
    python scripts/verify_weekly_source_pdf.py /workspace/weekly-print-fixed-open-review --baseline /workspace/weekly-print-review

The 38 print variants are five share entrances with notes closed, five with all notes opened by actual note buttons, five daily views, and all 23 selected instruction views. Result: 82 A4 PDF pages, zero acceptance failures. All 38 print-visible DOM texts match the full extracted PDF text; the prior 33 views also retain their pre-fix visible text. No text span lies outside the paper and no CSS table/article/heading overflows. No blank pages, header-only pages or map-only continuation tails remain. Every instruction is one page (23 pages), and daily pages are one per case (3/3/5/6/6 = 23). All opened-note share cards also remain on their case pages (23), with the last card and whole-map region together. Closed-note share entrances use 13 pages in total. For each daily page the expected single case appears in the original order; no quantity/condition table is split across case pages.

The new PDF checker was also applied to the original defective PDF set with only its missing case-ID metadata supplied from the unchanged accepted case set. It rejects 31 layout defects independently of the old inventory count, including the original blank daily page and two-page instructions. This shows the check detects the previous failure rather than merely changing an expected page count.

Visual inspection includes representative Wednesday instruction, daily and opened-note share final pages. The last case and map region are together, and both condition and quantity tables are intact. Desktop/mobile source-view traversal and all 23 instruction targets pass at 1280/390 widths. Representative pre/post desktop and mobile screenshots are pixel-identical; print-only styles do not alter the screen view. External resources are aborted by the isolated print/browser fixture, not substituted with fake map content.

Existing targeted regression checks pass: completion-archive scope (9), empty schedules, hidden TOP entries, headings, transport (25), bush cards (14), and bush dimensions (24 examples / 45,268 exhaustive / 21 invalid / 11 integration). Ordinary default detail templates are byte-identical to the public-base implementation. Five ordinary `share-update` calls exit 0 with every isolated file unchanged. Compileall and whitespace checks pass. No production saving/completion action is performed.

During correction, extending the test from closed note panels to all panels opened found additional trailing blank pages and a Wednesday header-only page. Those failures were corrected in the same source stylesheet before final acceptance; the report does not omit that state.

## Map verification boundary

No external-map load was retried. The preceding `unpkg.com` `ERR_CERT_AUTHORITY_INVALID` remains unresolved; no TLS bypass, alternate CDN, replacement Leaflet, trust/permission/configuration change or company access was attempted. Static independent checks confirm all 23 two-point JSON/wrapper/canvas bindings are unique and correctly connected, all source coordinates and URLs are preserved, and existing Leaflet 1.9.4 CDN URLs/SRI pins are unchanged. No existing local Leaflet JS/CSS asset was found in the public trees. These are static checks only. Actual marker/tile rendering, two-point map interaction, Google Maps navigation and printing a successfully rendered map remain unverified. The PDFs visibly retain an empty map region in this intercepted-network environment; they do not prove map output.

## State and payload

This source/configuration commit and the next generated-output commit each include a new log. No private evidence, original document, business dataset, secret, saved ledger, photo or immutable archive is added or modified. No company GUI/EXE/updater adoption or physical printing is performed. The PC candidate is unchanged and clean. Publication remains unperformed and requires separate authorization; actual maps remain an explicit unresolved acceptance item. Do not deploy an intermediate source-only commit without its matching outputs.

# November 16–20 ordinary-format source candidate

Recorded 2026-11-13 22:49 UTC; worker: Codex; isolated cloud branch `cursor/weekly-normal-format-candidate-20261113`.

## Scope and authority

The user requested correction from current skills and this week's generation/acceptance history, explicitly without company-PC access. Parent delegation confirmed a single new public-repository writer and no pending old writer/lock. Both fresh clones were clean. Share base and subsequently rechecked remote main: `456020e2ef96e7621b09c6c346f76f7325be2c70`; PC base: `8b7865edaf70f1e9dea359222599f9296c55710a`. Existing weekly branches are the PR45 and PR46 histories, not active competing candidates.

The format authority is the current user instruction and skills, with normal renderer/assets and this week's accepted history. PR45's minimal five-day engine and PR46's three-button TOP are explicitly not format exemplars. Compared `e17d125b8b58beedc9c4a6cb4877f3c1d2f119b8`, asset adoption `a16d58976172e24c8fe845f44d687dce1652ac31`, November 6 normal cards/detail templates, and November 10 format-alignment/transport logs. Old HTML was not copied as the format implementation.

Worker directly read both AGENTS, PC `docs/worktree_prod_operations.md`, current-source map, and the following current skill resources during this turn (log timestamp above). Both repository trees lack `.agents/skills`; share-pages delegates worktree operations to the PC document. Parent supplied authorization/history and later repeated skill text; those are separate from the worker's direct reads and application:

- `skill://user/6af1949931408191a869a74c0c65e4e2/ippatsu-align-generation/SKILL.md`, `references/operation-contract.md`, `references/route-record.md`, `references/evidence-history.md`.
- `skill://user/6af194fb53c081919ee05e6d8c5b2412/ippatsu-build-daily-pages/SKILL.md`, `references/input-and-checks.md`.
- `skill://user/6af1953337ac8191b4d4b0145e44a9d1/ippatsu-update-portal-sections/SKILL.md`, `references/focused-generation.md`.

## Route and concrete change

| Stage | Candidate route / evidence |
|---|---|
| Public input | Immutable PR45 public commit `27d90ef9d6541be58c3410376c9e55e8a5c02956`, exactly five share pages; existing content only, not a DB snapshot or new source confirmation |
| Transformation | `scripts/generate_weekly_source_format.py`; exact 3/3/5/6/6 cases, order, 51407008 Tuesday only; all evidence text/states, source notes, conditions, map endpoints and representative points retained |
| Card renderer | PC `app/share/html_generator.py` from local candidate `f693fb9`; explicit evidence mapping, ordinary `card-head/card-actions/instr-*` markup; no confirmed-zero inference |
| Detail templates | Existing `apply_saved_ledger_views.templates`, with explicit source-only mode; normal `data-share-view` templates |
| Detail renderer | Existing `ledger-view-render.renderProjection`, explicit source-only projection and unchanged ordinary default; no document/receipt fabricated |
| Postprocessing | Scoped identity/metadata/links projection in the candidate generator, not a generic editable-ledger injection; only public input information used |
| Runtime/assets | Source-only controller calls the common normal renderer; no `loadDay`, correction editor, input/save/completion actions, auto-refresh, storage or Auth calls. Its new renderer URL/cache query is pinned explicitly, with normal nested dependencies unchanged |
| Integrity | `weekly_readonly_outputs.json` pins 15 outputs plus both source assets and the newly modified common renderer (18 files). Existing exact hash/path/date checks remain. Every protected day now checks the asset hashes, extending Wednesday's previous check |
| TOP | Normal `generate_portal.py --mode portal-top-only`: one ordinary share entrance per date. TOP guard now rejects missing, duplicate or direct detail links |
| Output | Separate `weekly-format-output-a`, `weekly-format-output-b`, then isolated `weekly-format-isolated`; generated files are copied only after semantic/repeat/guard acceptance |

`SOURCE-HASHES.json` is historical adoption evidence and remains unchanged. The new output hashes correspond to the changed ordinary renderer, pinned public input and independent semantic tests; hashes were not changed to suppress a failure. Source import validation allows only the two exact new source-controller dependency URLs; ordinary mixed-generation rejection remains.

## Checks completed

- Two independent generations are byte-identical. Fifteen page identity/order, all 345 quantities, public conditions/notes, map endpoints, URLs and whole-map representative coordinates match public source semantics.
- Quantity evidence: 108 nonapplicable candidates, 53 source positives, 90 already-published formal-confirmation categories, 94 unknowns. The 90 are preserved public categories, not newly confirmed by this worker; 108 candidates remain candidates and never become zero.
- Six dedicated acceptance tests pass, including source projection, repeat output, scope, TOP and integrity. Fifteen old-format outputs, all content mutations and wrong-date bindings are rejected. All 18 modified and 18 missing protected files are rejected.
- Five ordinary `share-update --date` executions exit 0 and preserve every isolated file after TOP generation; TOP-only validation passes with five cards. Source-only assets have no other non-target page users; non-target generated files and fixed archives remain byte-identical.
- Existing targeted suites pass: completion archive scope (9), empty-day TOP, hidden portal entries, heading, transport (25 cases), bush cards (14), bush dimensions (24 examples / 45,268 exhaustive cases / 21 invalid / 11 integrations). Python compileall and diff whitespace checks pass. PC normal renderer matches HEAD byte output for two ordinary fixtures.
- Chromium uses local route fulfillment, with external requests aborted. At widths 1280 and 390: TOP → all five ordinary share entrances → daily links; 23 instruction selections; expected cards and date/selection, note toggles, no writable controls, no correction frame, and no source-view business/API requests. Existing TOP calendar attempts are preserved but intercepted, not treated as new source-view requests. Dedicated browser checker and screenshots are supplied locally. Source view sets `sourceViewReady`, never `savedLedgerReady`.
- Generated 23 A4 instruction PDFs (46 pages), inspected representative desktop/mobile screenshots and first print page. No physical printing. Remote map tiles/Leaflet CDN were deliberately not loaded, so actual two-point map interaction is not claimed.

## Failures and corrections, not hidden

The initial generator rejected an existing `formal_confirmed` public evidence category; the typed mapping was corrected to preserve it. Initial test invocation from a git-less isolated directory used the wrong source root; it now requires explicit roots. A broad unittest discovery attempt failed (7 errors) because existing script-style runners parse command-line arguments/run during import; the new runner was corrected to skip without explicit roots, and the relevant existing suites were then invoked separately. No claim that the broad suite passed. One scope check overlapped our test-file copy and detected that copy; a subsequent serialized five-day check passed. The first browser TOP traversal counted existing calendar requests as source-view requests; the assertion now excludes only the existing TOP frame, while all external requests remain intercepted. No executor/network/access denial occurred and no escalation, alternate access path, permission/configuration change or secret lookup was used.

## Boundaries and remaining publication conditions

This is a cloud Python/source candidate only. Company GUI/EXE, embedded modules, updater, adoption receipts and company-local generators are unverified and were not accessed. DB, schedule, quantities, saved ledgers, photos and existing business state were not changed. No receipt/UUID was invented. No company/private originals or input bundle were added to the repositories.

Before adoption/publication: review the two repository candidates together, repeat against the latest remote heads and approved payload, review real map operation and complete print layout, and carry out the current publication procedure only after explicit authorization. Company GUI/EXE reconciliation is a separate authorized operation when available, not satisfied by this candidate. This turn does not push, create a PR, merge, deploy or read back live HTTP. Source/configuration and generated outputs are separate local commits, each with a new work log. Recovery is to retain the current published main until the whole candidate is accepted; do not deploy the source-only intermediate commit alone.

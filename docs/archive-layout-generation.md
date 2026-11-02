# Archive layout generation

## Routes and responsibility

- Normal daily/instruction views use `portal/shared-ledger/ledger-view-render.mjs`. Its 2026-10-31 change placed the recorded branch-photo count beside the felling-count heading.
- Completed archives deliberately do **not** call that live renderer or query the DB. `scripts/archive_snapshot_builder.py` reads the manifest and explicit immutable saved-form references, copies their article/table content into catalog/day JSON, and emits a read-only viewer.
- Viewer sources are `scripts/archive_snapshot_assets/app.js` and `style.css`. The builder produces `portal/archive/archive-v2-r1/{app.js,style.css}`, the archive index, and dated `view.html` files. Dated views embed identical viewer code/CSS for self-contained viewing.
- Update viewer **sources first**, then rebuild in a separate staging directory. Do not patch only a dated view or immutable `saved-forms` HTML. Keep quantities, recorded photo counts, identifiers and frozen article JSON unchanged.
- The 2026-11-02 fix moves only the recorded, recognized `p.meta` photo-count label into its felling heading at render time. Already-new or ambiguous markup is unchanged. No recalculation. Both daily and instruction modes use this projection.
- The index references content-hashed JS/CSS. Dated pages embed their viewer, so all dated derivatives must accompany a source change.

## Regeneration check

Run `python scripts/test_archive_layout_generation.py` from the full repository checkout. It builds into temporary storage, compares generated viewer assets/index/dated pages byte-for-byte, checks the catalog and cache keys, and proves saved source HTML was not modified. Never run a broad production generator just to repair presentation.

## Validation record and limitations

For this patch, 16 actual cases / 32 recorded documents retained exact embedded JSON. Candidate JS was additionally executed against parsed source trees through a minimal element adapter: 32 real documents + 6 boundary cases passed table/label preservation, known-format-only changes, and idempotence. That adapter is **not** real browser DOM or visual acceptance.

Pre-publication local visual testing was unavailable: browser process/socket and file/localhost preview restrictions. No settings were relaxed. The authorized release therefore requires post-publication HTTPS browser verification of archive listing, a dated daily view, instruction mode, narrow viewport, and unchanged table values. If rendering regresses, revert only this layout commit (preserve unrelated subsequent work). Do not claim the adapter or static CSS review substitutes for actual display checks.

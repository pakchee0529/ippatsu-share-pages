# ippatsu-share-pages — 次 Cursor タスク

## completion_reports / portal archive（2026-06-03）

**正本:** Supabase `cases` + `case_events`（ippatsu-pc）  
**副本:** `output/completion_reports_export/` 等 — portal archive 公開素材

| 優先 | タスク | 状態 |
| ---- | ------ | ---- |
| 1 | `generate_portal.py --completion-reports-root` | **完了** — [root 明示](./work_logs/2026-06-03_portal_archive_completion_reports_root.md) |
| 2 | full dry-run + manifest 件数整合 | **完了** — [full dry-run](./work_logs/2026-06-03_portal_archive_full_dry_run_export_root.md) |
| 3 | 公開前 precheck | **完了** — [precheck](./work_logs/2026-06-03_portal_archive_publish_precheck.md)。4 日付整合・HTML ローカル準備済み。**push は人間 Go 待ち** |
| 4 | completion archive 公開 | **完了** — [公開結果](./work_logs/2026-06-03_completion_archive_publish_result.md)。260518–529 の archive HTML のみ push。share は未公開。 |
| 5 | Pages 反映・本番目視 | 人間 — 260529=1 件など |
| 6 | share / negotiation HTML 公開 | 未着手 — ローカル差分あり。archive とは別 commit 想定 |
| 7 | `export_summary` 鮮度チェック強化 | 未着手（`exported_at` トップレベル） |
| 8 | 公開成功後 data snapshot | 任意・別 Go（ippatsu-pc timing policy） |
| 9 | portal archive Supabase direct/fallback | 長期 |

**運用:** `data/completion_reports` の公開前先行更新はしない。260529 incomplete 3 件は副本 export に含めない（archive 詳細は export 件数どおり）。

**参照:** ippatsu-pc `docs/work_logs/2026-06-03_completion_reports_export_timing_policy.md`

# ippatsu-share-pages — 次 Cursor タスク

## completion_reports / portal archive（2026-06-03）

**正本:** Supabase `cases` + `case_events`（ippatsu-pc）  
**副本:** `output/completion_reports_export/` 等 — portal archive 公開素材

| 優先 | タスク | 状態 |
| ---- | ------ | ---- |
| 1 | `generate_portal.py --completion-reports-root` | **完了** — [root 明示](./work_logs/2026-06-03_portal_archive_completion_reports_root.md) |
| 2 | full dry-run + manifest 件数整合 | **完了** — [full dry-run](./work_logs/2026-06-03_portal_archive_full_dry_run_export_root.md) |
| 3 | 公開前 precheck | **完了** — [precheck](./work_logs/2026-06-03_portal_archive_publish_precheck.md)。4 日付整合・HTML ローカル準備済み。**push は人間 Go 待ち** |
| 4 | 公開 | export 再生成 → full（explicit + strict）→ 目視 → **portal/archive HTML（+必要なら index/survey/negotiation）commit/push** |
| 5 | `export_summary` 鮮度チェック強化 | 未着手（`exported_at` トップレベル） |
| 6 | 公開成功後 data snapshot | 任意・別 Go（ippatsu-pc timing policy） |
| 7 | portal archive Supabase direct/fallback | 長期 |

**運用:** `data/completion_reports` の公開前先行更新はしない。260529 incomplete 3 件は副本 export に含めない（archive 詳細は export 件数どおり）。

**参照:** ippatsu-pc `docs/work_logs/2026-06-03_completion_reports_export_timing_policy.md`

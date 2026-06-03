# ippatsu-share-pages — 次 Cursor タスク

## completion_reports / portal archive（2026-06-03）

**正本:** Supabase `cases` + `case_events`（ippatsu-pc）  
**副本:** `output/completion_reports_export/` 等 — portal archive 公開素材

| 優先 | タスク | 状態 |
| ---- | ------ | ---- |
| 1 | `generate_portal.py --completion-reports-root` | **完了** — [work log](./work_logs/2026-06-03_portal_archive_completion_reports_root.md) |
| 2 | 公開前フロー | export 再生成 → `--completion-reports-root` 指定で portal 生成 → 確認 → 公開（人間 Go） |
| 3 | `export_summary` 鮮度チェック強化 | 未着手（`exported_at` トップレベル・厳格停止の拡張は ippatsu-pc 側も可） |
| 4 | portal archive Supabase direct/fallback | 長期 |

**運用:** `data/completion_reports` の公開前先行更新はしない。260529 incomplete 3 件は副本 export に含めない（archive 詳細は export 件数どおり）。

**参照:** ippatsu-pc `docs/work_logs/2026-06-03_completion_reports_export_timing_policy.md`

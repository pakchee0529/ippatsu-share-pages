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
| 5 | Pages 反映・本番目視 | **完了**（260529 一覧・詳細・status 非表示） |
| 6 | share / negotiation HTML 公開 | **別 Go** — ローカル副産物は [棚卸しで restore 済](./work_logs/2026-06-03_share_pages_local_diff_cleanup.md)。full 再生成で差分再発 |
| 17 | ローカル残差分棚卸し | **完了** — [ログ](./work_logs/2026-06-03_share_pages_local_diff_cleanup.md) |
| 18 | archive 表記テンプレート統一 | **一部公開** — [コード](./work_logs/2026-06-03_archive_display_template_unification.md) + [公開](./work_logs/2026-06-03_archive_display_template_publish_result.md)。一覧+518/519/520/529 詳細。**260611 公開済** — [ログ](./work_logs/2026-06-12_archive_260611_publish.md) |
| 19 | archive 260611（全6件 completed） | **完了** — [公開](./work_logs/2026-06-12_archive_260611_publish.md)。manifest + 一覧 + 詳細。TOP/share 未変更。 |
| 20 | archive backfill 260605–612 | **完了** — [backfill](./work_logs/2026-06-12_archive_backfill_260610_260611_260612.md)。7日分。260610/612 は planned 未完了枠付き。 |
| 7 | `export_summary` 鮮度チェック強化 | 未着手（`exported_at` トップレベル） |
| 8 | 公開成功後 data snapshot | 任意・別 Go（ippatsu-pc timing policy） |
| 9 | portal archive Supabase direct/fallback | 長期 |
| 10 | 未完了別枠表示（portal 第 2 セクション） | **設計済** — ippatsu-pc [incomplete section 設計](https://github.com/pakchee0529/ippatsu-pc/blob/main/docs/work_logs/2026-06-03_completion_archive_incomplete_section_design.md) |
| 11 | portal planned_but_incomplete 第 2 セクション | **dry-run 実装済** — [ログ](./work_logs/2026-06-03_portal_archive_planned_incomplete_dry_run.md) |
| 12 | archive 再公開（260529 +3 未完了枠） | **完了** — [公開結果](./work_logs/2026-06-03_completion_archive_planned_incomplete_publish_result.md) |
| 13 | planned_but_incomplete UI 整理（件数・文言） | **完了** — [cleanup](./work_logs/2026-06-03_planned_incomplete_ui_cleanup.md) + [公開](./work_logs/2026-06-03_planned_incomplete_ui_publish_result.md) |
| 14 | 本番 260529 UI 目視（一覧・詳細・status非表示） | 人間 — Pages 反映後 |
| 15 | planned_but_incomplete カードから内部 status 非表示 | **完了** — [cleanup](./work_logs/2026-06-03_planned_incomplete_status_ui_cleanup.md) + [公開](./work_logs/2026-06-03_planned_incomplete_status_ui_publish_result.md) |
| 16 | 260529 未完了3件の status 業務整合 | 人間/ippatsu-pc — 正本は `negotiation_wait`。工事待ちなら `construction_wait` 是正候補（変更は別 Go） |

**運用:** `items` は completed のみ（完了件数・manifest）。260529 の 51404109/117/127 は **別枠候補**（legacy 由来・ref 付与禁止）。archive カードに英語 status は出さない。

**参照:** ippatsu-pc `docs/work_logs/2026-06-03_completion_reports_export_timing_policy.md`、同 `2026-06-03_completion_archive_incomplete_section_design.md`

## portal TOP 基準日

- **CLI:** `--portal-min-date` / `--hide-before-date` + `--mode portal-top-only`（[`2026-06-09 実装`](./work_logs/2026-06-09_portal_top_min_date_260610.md)）
- **適用済み（現行）:** `portal_min_date=260613` — 260612 以前を TOP から非表示。**260612 終了扱い**（5件完了・51405397 未完了維持）。TOP カード0件（260613 以降 share 未公開）。ログ: [`work_logs/2026-06-12_portal_top_min_date_260613.md`](./work_logs/2026-06-12_portal_top_min_date_260613.md)。`share/260612/` 直接URLは残存。
- **履歴:** `260610`（2026-06-09）— 260609 以前非表示・260610/611/612 表示。[`work_logs/2026-06-09_portal_top_min_date_260610.md`](./work_logs/2026-06-09_portal_top_min_date_260610.md)
- **未実施:** completed status との自動連動（明示日付 CLI のみ）

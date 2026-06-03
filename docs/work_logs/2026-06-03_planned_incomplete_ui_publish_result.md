# planned_but_incomplete UI 公開結果

日付: 2026-06-03  
前提コード: `86e60654e0bbd855710cee9c18a3e9c162ac1fde`（UI cleanup）

制約: Supabase write なし / `data/` 未変更 / `share/**` 未 commit / `output/` 未 commit

---

## A. 結論

260529 archive 詳細と archive 一覧のみを公開。期待 UI（完了 1件 / 当日未完了 3件、第 2 セクション圧縮）をローカル HTML で確認後、明示 add で push。

---

## B. 公開したファイル

- `portal/archive/260529/index.html`
- `portal/archive/index.html`
- `portal/archive_manifest.json`（`item_count=1`, `planned_incomplete_count=3` — 前回公開から変更なしの可能性あり）
- `docs/work_logs/2026-06-03_planned_incomplete_ui_publish_result.md`
- `docs/next_cursor_tasks.md`

---

## C. 260529 表示結果（ローカル）

| 項目 | 結果 |
| ---- | ---- |
| 完了セクション | 51404222 のみ |
| 当日予定・未完了 | 51404109 / 51404117 / 51404127 |
| 注意文 | セクション冒頭 1 回 |
| 反復文 | 「完了扱いではありません」なし |
| 生成ログ | `items=1, planned_but_incomplete=3` |

---

## D. 一覧表示結果（ローカル）

260529 行: `完了 1件 / 当日未完了 3件`（`+3` バッジ・`完了1 / 未完了0` 下段なし）

---

## E. export / 生成

```text
# ippatsu-pc
python tools/export_completion_reports_from_supabase.py --dates 260529 \
  --output-dir output/completion_reports_export_incomplete \
  --compare-legacy --attach-legacy-incomplete
# → planned_but_incomplete=3, items=1

# ippatsu-share-pages
python scripts/generate_portal.py --mode full \
  --completion-reports-root .../completion_reports_export_incomplete \
  --strict-completion-reports-root --strict-completion-reports-summary
```

---

## F. share 差分

full 生成で `share/**` は更新されたが **commit していない**（ローカル差分のまま）。

---

## G. 正本・禁止事項

- Supabase / `data/completion_reports` 未操作
- `git add .` 未使用

---

## H. 公開後確認

- GitHub Pages: push 後、CDN 反映に数分かかる場合あり
- 目視 URL（例）: `/portal/archive/` 一覧の 260529 行、`/portal/archive/260529/` 詳細

---

## I. 次の一手

1. 本番 Pages で 260529 一覧・詳細目視
2. share / negotiation HTML は別 Go

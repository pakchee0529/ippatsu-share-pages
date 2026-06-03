# planned_but_incomplete アーカイブ UI 整理

日付: 2026-06-03  
制約: Supabase write なし / `data/` 変更なし / portal HTML commit なし / 公開なし

---

## A. 結論

一覧・詳細の件数・文言表示を整理し、260529 で「完了 1件 / 当日未完了 3件」の一系統表示と、第 2 セクション冒頭のみの注意文に統一。`generate_portal.py` のみ commit/push 済み。portal HTML の本番反映は別 Go。

---

## B. 問題点

1. **一覧:** 右上 `1件` + `+3 当日未完了` と下段 `完了1 / 未完了0` が同居し、「未完了0 なのに +3？」と誤読されうる。
2. **詳細:** 各カードに「完了扱いではありません」・ref 行・note が反復し情報密度が低い。

---

## C. 一覧ページの修正

`format_archive_row_article` / `build_archive_row_context`:

- `planned_incomplete_count > 0` の日は **件数行のみ** `完了 {item_count}件 / 当日未完了 {pi}件`
- `+N 当日未完了` バッジと `archive-status` の `完了N / 未完了0` を出さない
- 検索用 `data-search` に統一文言を含める

---

## D. 詳細ページの修正

`build_planned_incomplete_section_html`:

- 見出し: **当日予定・未完了**
- 説明: セクション冒頭 1 回（指定文案）
- カード: 未完了タグ / 径間名 / 管理番号 / 現在状態 / 未完了理由 / 地図のみ
- per-card の ref・note・「完了扱いではありません」反復を削除

---

## E. 260529 dry-run確認

```text
python scripts/generate_portal.py --mode full \
  --completion-reports-root C:\Users\kotan\Projects\ippatsu-pc\output\completion_reports_export_incomplete \
  --strict-completion-reports-root \
  --strict-completion-reports-summary
```

| 確認項目 | 結果 |
| -------- | ---- |
| ログ | `archive detail 260529: items=1, planned_but_incomplete=3` |
| 一覧 `portal/archive/index.html` | `完了 1件 / 当日未完了 3件`（`+3`・`未完了0` なし） |
| 完了セクション | 51404222 のみ |
| 第 2 セクション | 51404109 / 51404117 / 51404127 |
| 注意文 | セクション冒頭 1 回 |

---

## F. item_count / planned_incomplete_count の扱い

- **item_count:** 完了（`items`）のみ — manifest / export 整合は従来どおり
- **planned_incomplete_count:** 別カウント — 一覧表示の「当日未完了 N件」にのみ使用
- 完了判定・件数集計ロジックは変更していない（表示層のみ）

---

## G. 正本を汚さない確認

- Supabase: 未操作
- `data/completion_reports/*.json`: 未変更
- export root: 既存 `completion_reports_export_incomplete` を読み取りのみ
- 正本は各ポータル一覧 + Supabase；archive は表示副本

---

## H. 公開しなかったこと

- `portal/archive/*.html` は dry-run でローカル更新のみ — **commit/push していない**
- `share/**` も commit 対象外
- GitHub Pages への archive 再公開は人間 Go 待ち

---

## I. 変更したファイル（commit 対象）

- `scripts/generate_portal.py`
- `docs/work_logs/2026-06-03_planned_incomplete_ui_cleanup.md`
- `docs/next_cursor_tasks.md`

---

## J. 人間確認事項

1. 本番 Pages で 260529 一覧・詳細の新 UI（archive HTML 再公開後）
2. 他日付で `planned_incomplete_count` がある場合の一覧表示（現状は 260529 のみ）

---

## K. 次の一手

1. **archive HTML 公開 Go** — `portal/archive/index.html`, `portal/archive/260529/index.html` を明示 add で commit/push
2. Pages 反映後 260529 目視
3. share / negotiation は別タスク

---

## L. git status --short（作業直前・portal 生成後）

```text
 M docs/work_logs/2026-06-03_completion_archive_planned_incomplete_publish_result.md
 M portal/archive/260507/index.html
 …（portal/archive/*, portal/negotiation, share/*）
 M scripts/generate_portal.py
?? output/
```

※ commit 後は `scripts/generate_portal.py` と docs のみ staged/commit 想定。portal/share はローカル差分のまま。

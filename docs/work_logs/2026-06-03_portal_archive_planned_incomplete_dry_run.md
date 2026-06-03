# portal archive — planned_but_incomplete 第 2 セクション dry-run

日付: 2026-06-03  
制約: portal 公開なし / HTML commit なし

参照: ippatsu-pc [export dry-run](https://github.com/pakchee0529/ippatsu-pc/blob/main/docs/work_logs/2026-06-03_completion_reports_export_planned_incomplete_dry_run.md)

---

## A. 結論

`load_archive_planned_incomplete` + 詳細第 2 セクション + 一覧 `+N 当日未完了` を実装。full dry-run で 260529 **completed 1 + planned 3**、manifest `planned_incomplete_count=3`（ローカルのみ）。

---

## B. 背景

公開済み archive は completed 1 件のみ。未完了 3 件を別枠で dry-run 表示。

---

## C. 実装内容

`scripts/generate_portal.py`:

- `PlannedIncompleteItem`, `load_archive_planned_incomplete`
- `build_planned_incomplete_section_html`
- `build_archive_detail_html` 第 2 セクション
- `format_archive_row_article` の `+N 当日未完了`
- manifest sync に `planned_incomplete_count`

---

## D. export 根

`C:\Users\kotan\Projects\ippatsu-pc\output\completion_reports_export_incomplete`

---

## E. portal 表示結果

```text
python scripts/generate_portal.py --mode full \
  --completion-reports-root .../completion_reports_export_incomplete \
  --strict-completion-reports-root \
  --strict-completion-reports-summary
```

- exit 0、`source=explicit`
- 260529: `archive detail … items=1, planned_but_incomplete=3`

---

## F. 260529 検証（ローカル HTML）

| 項目 | 値 |
| ---- | -- |
| 完了カード | 1 |
| 第 2 セクションカード | 3 |
| 51404222 | 完了セクションのみ |
| 51404109/117/127 | 第 2 セクションのみ |
| `archive/index` | `1件` + `+3 当日未完了` |
| manifest（ローカル） | `item_count=1`, `planned_incomplete_count=3` |

---

## G. 正本

- `load_archive_public_items` は `items` のみ
- planned は完了件数・strict-summary に含めない

---

## H. item_count / manifest

- `item_count` / `archive-count` = completed のみ
- `planned_incomplete_count` = 別（manifest・一覧バッジ）

---

## I. 公開

**していない**。`portal/archive/*.html` は commit しない。

---

## J. リスク

- 本番 Pages は旧 HTML（1 件のみ）のまま
- full 生成は share 差分も出る（今回 commit 外）

---

## K. 人間確認

1. ローカル `portal/archive/260529/` 目視
2. 再公開 Go 時は export 再生成 + 同 root + archive HTML のみ commit

---

## L. 次の一手

1. 人間目視
2. archive 再公開（260529 HTML + manifest `planned_incomplete_count` 含むか判断）

---

## M. git status

`portal/**` M（dry-run）、`share/**` M。commit は `scripts/generate_portal.py` + 本ログ + next_cursor_tasks のみ。

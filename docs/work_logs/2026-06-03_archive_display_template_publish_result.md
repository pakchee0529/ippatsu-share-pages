# archive 表記統一 — 本番 HTML 公開結果

日付: 2026-06-03  
前提コード: `424b60beae6cc95c52ba36d0a6b3c40547aa33bc`

---

## A. 結論

**一覧 + export 済み 4 日付の詳細**のみ commit/push。export 未整備の archive 詳細日は **カード消失** のため公開対象外とし、作業ツリーから restore。

---

## B. export 再生成結果

```text
python tools/export_completion_reports_from_supabase.py \
  --dates 260518 260519 260520 260529 \
  --output-dir output/completion_reports_export_incomplete \
  --compare-legacy --attach-legacy-incomplete
```

| 日付 | items | planned |
| ---- | ----- | ------- |
| 260518 | 4 | 0 |
| 260519 | 6 | 0 |
| 260520 | 7 | 0 |
| 260529 | 1 | 3 |

---

## C. full 生成結果

- exit 0、`completion_reports_root` explicit
- legacy fallback 警告なし（export 明示 root）

---

## D. 公開対象ファイル

- `portal/archive/index.html`
- `portal/archive/260518/index.html`
- `portal/archive/260519/index.html`
- `portal/archive/260520/index.html`
- `portal/archive/260529/index.html`

**含めなかった:** `portal/archive_manifest.json`（差分なし）、上記以外の `portal/archive/<date>/index.html`（後述）

---

## E. 一覧表示の確認

- planned なし: **完了 N件**（`archive-status` 二重行なし）
- 260529: **完了 1件 / 当日未完了 3件**

---

## F. 詳細表示の確認

- 見出し: **完了した作業**
- **Supabase 正本** 表記なし
- 260529 第2枠: 英語 status なし

---

## G. 260529 表示

- 完了: 51404222
- 第2枠: 51404109 / 51404117 / 51404127
- 見出し・説明文は status UI cleanup 済み

---

## H. 他日付への影響（重要）

full 生成で **export JSON が無い日**（260507–528 等、260601）は `items=0` となり、詳細 HTML から **完了カードが全削除** される。

| 例 | HEAD カード数 | 生成後 |
| -- | ------------- | ------ |
| 260528 | 3 | 0 |
| 260601 | 6 | 0 |

→ これらの詳細 HTML は **commit しない**。一覧のみ更新（詳細は本番既存 HTML を維持）。

---

## I. share / negotiation を含めなかった理由

- full 副産物。今回スコープ外
- commit / push していない

---

## J. commit hash

`f2ae7282787c08384b991b08ac35da6248ac6cc2`

---

## K. push 結果

`origin/main` 成功（`424b60b..f2ae728`）

---

## L. git status

push 後、未公開 archive 詳細・share・negotiation は restore 推奨。

---

## M. Pages 確認

- https://pakchee0529.github.io/ippatsu-share-pages/portal/archive/
- …/260529/ …/260518/ 等

反映遅延あり得る。

---

## N. 次の一手

1. export を全日付分揃えてから、残り archive 詳細の表記統一を一括公開
2. share / negotiation 別 Go

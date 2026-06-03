# completion archive — planned_but_incomplete 再公開結果

日付: 2026-06-03  
**人間 Go 済み — archive 限定公開（第 2 セクション含む）**

---

## A. 結論

260529 の **完了 1 件 + 当日未完了 3 件（別枠）** を portal archive に公開。`items` / `item_count` は 1 のまま。`share/**` は commit 外。

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

Supabase write なし / `data/completion_reports` 未変更。

---

## C. full 生成結果

- `completion_reports_root=.../completion_reports_export_incomplete` (`source=explicit`)
- exit 0、strict-summary OK
- 260529: `items=1`, `planned_but_incomplete=3`

---

## D. 公開対象ファイル

- `portal/archive/260529/index.html`（第 2 セクション追加）
- `portal/archive/index.html`（`1件` + `+3 当日未完了`）
- `portal/archive_manifest.json`（`planned_incomplete_count=3`）
- `portal/archive/260518/index.html`（共有 CSS のみ・+21 行）
- `portal/archive/260519/index.html`（同上）
- `portal/archive/260520/index.html`（同上）

---

## E. 260529 completed / planned

| 区分 | 件数 | 管理番号 |
| ---- | ---- | -------- |
| 完了セクション | 1 | 51404222 |
| 第 2 セクション | 3 | 51404109, 51404117, 51404127 |

---

## F. item_count / planned_incomplete_count

- `item_count` / 一覧 `archive-count`: **1**
- `planned_incomplete_count` / 一覧: **+3 当日未完了**

---

## G. share を含めなかった理由

archive 公開スコープのみ。full 実行で share inject 差分は出るが今回 commit しない。

---

## H. Supabase / data

変更なし（export SELECT + 副本 JSON のみ）。

---

## I. commit hash

（push 後記録）

---

## J. push 結果

`origin/main`（push 後記録）

---

## K. git status

push 後: 公開 6 archive ファイル clean。`share/**` 等は M のまま。

---

## L. Pages 反映確認

https://pakchee0529.github.io/ippatsu-share-pages/portal/archive/260529/

反映遅延の可能性あり。期待: 完了 1 + 第 2 セクション 3。

---

## M. 次にやるべきこと

1. 本番 260529 目視
2. 中期: `work_day_attempts` / event 由来へ移行
3. share / negotiation 公開は別判断

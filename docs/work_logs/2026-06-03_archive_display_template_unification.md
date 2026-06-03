# completion archive 表記テンプレート統一

日付: 2026-06-03  
制約: portal HTML commit なし / 公開なし / Supabase・`data/` 未変更

---

## A. 結論

`generate_portal.py` の archive 一覧・詳細生成を **全日付共通テンプレート** に揃えた。260529 だけが新表記だった状態を解消。内部用語「Supabase 正本」を公開 UI から除去。full dry-run で 260518/519/520/529 を確認済み。

---

## B. 問題意識

- 260529: `完了 1件 / 当日未完了 3件`、第2セクション、見出しあり
- 他日: 一覧が `N件` + `完了N / 未完了M` の二重表記、詳細に見出しなし、planned あり日のみ「Supabase 正本」見出し

同一 generator でも **分岐条件** により見え方が揃っていなかった。

---

## C. 内部構造の確認

| 関数 | 役割 |
| ---- | ---- |
| `build_archive_row_context` | 検索 blob・件数・status_summary |
| `format_archive_row_article` | 一覧 1 行 HTML |
| `build_archive_detail_html` | 詳細ページ（完了カード + planned 第2枠） |
| `build_planned_incomplete_section_html` | planned あり日のみ第2セクション |

全 archive 日は **同一コードパス**。差分は `planned_incomplete_count` の有無と `public_items` の有無のみ。

---

## D. 260529 と他日付の違い（修正前）

| 項目 | 260529 | 他日（例 260518） |
| ---- | ------ | ----------------- |
| 一覧件数 | 完了 1件 / 当日未完了 3件 | 4件 + 完了4/未完了0 |
| 詳細見出し | 完了報告（Supabase 正本） | なし（カード直出し） |
| 第2枠 | あり | なし |

---

## E. 一覧表示ルール（修正後）

| 条件 | 表示 |
| ---- | ---- |
| `planned_incomplete_count == 0` | **完了 N件** のみ（`archive-status` 行は出さない） |
| `planned_incomplete_count > 0` | **完了 N件 / 当日未完了 M件** |

`item_count` / `planned_incomplete_count` の内部意味は変更なし。

---

## F. 詳細表示ルール（修正後）

| 条件 | 表示 |
| ---- | ---- |
| 完了カードあり | 見出し **完了した作業** |
| planned あり | **当日予定・未完了** + 説明 1 回 |
| planned なし | 第2セクション **出さない** |

「Supabase 正本」は **削除**。planned 説明の「正本」も「各ポータル一覧」に変更。

---

## G. 修正した文言

- 詳細完了見出し: `完了報告（Supabase 正本）` → **完了した作業**（完了カードがある日は常に表示）
- 一覧（planned なし）: `N件` + `完了N/未完了M` → **完了 N件** のみ
- planned 説明: 「各ポータル一覧の正本」→ **各ポータル一覧**

---

## H. dry-run結果

```text
python scripts/generate_portal.py --mode full \
  --completion-reports-root .../completion_reports_export_incomplete \
  --strict-completion-reports-root --strict-completion-reports-summary
```

| 日付 | 一覧 | 詳細 |
| ---- | ---- | ---- |
| 260518 | 完了 4件 | 完了した作業 + 4カード、第2枠なし |
| 260519 | 完了 6件 | 同上 |
| 260520 | 完了 7件 | 同上 |
| 260529 | 完了 1件 / 当日未完了 3件 | 完了した作業 + 第2枠（英語 status なし） |

archive HTML 内に `Supabase` 文字列 **なし**（portal 返却待ち等は対象外）。

---

## I. 正本を汚さない確認

- Supabase write なし
- `data/` 未変更
- export root 読取のみ

---

## J. 公開しなかったこと

- `portal/archive/**` はローカル dry-run のみ（HTML commit なし）
- `share/**` も再生成副産物のみ

---

## K. 変更したファイル（commit 対象）

- `scripts/generate_portal.py`
- `docs/work_logs/2026-06-03_archive_display_template_unification.md`
- `docs/next_cursor_tasks.md`

---

## L. 人間確認事項

1. 公開 Go 後、全日付の一覧が **完了 N件** 表記になっているか
2. 260529 以外の詳細に **完了した作業** 見出しが付くことの受容
3. 過去日で `incomplete_count` が manifest にあるが planned 0 の日 — 一覧は完了件数のみ（旧「未完了M」は一覧に出さない設計）

---

## M. 次の一手

1. **archive 一括または日付単位の HTML 公開 Go**（`portal/archive/index.html` + 各 `portal/archive/YYMMDD/index.html`）
2. full 生成後は `git status` で share/negotiation 副産物を restore（[棚卸しログ](./2026-06-03_share_pages_local_diff_cleanup.md) 参照）

---

## N. git status --short（dry-run 後・commit 前）

```text
 M portal/archive/** (多数)
 M portal/negotiation/index.html
 M share/** (9)
?? output/
```

（docs + script commit 後も HTML 差分は残る想定 — 公開 Go または restore で整理）

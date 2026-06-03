# share-pages ローカル残差分棚卸し

日付: 2026-06-03  
制約: portal 公開なし / HTML commit なし / Supabase write なし / `data/` 未変更

---

## A. 結論

planned_but_incomplete UI 公開後に残っていた **full 生成副産物**（share inject、他 archive 再生成、negotiation 再生成）を分類し、安全と判断したものは **明示 `git restore`** で作業ツリーを clean 化。追跡ファイルの未 commit 差分は **0**（`?? output/` のみ）。

---

## B. 背景

260529 / archive 一覧の status UI cleanup は本番目視済み（`3f03fd1`）。その後の `generate_portal.py --mode full` で、公開スコープ外の HTML が大量に未 commit のまま残存していた。

---

## C. 作業前 git status

```text
 M docs/work_logs/2026-06-03_completion_archive_planned_incomplete_publish_result.md
 M portal/archive/260507 … 260528, 260601/index.html  (14 日)
 M portal/negotiation/index.html
 M share/260604 … 261231/index.html  (9 ファイル)
?? output/
```

`portal/archive/260529/index.html` / `portal/archive/index.html` / `portal/archive_manifest.json` は **clean**（公開済みと一致）。

---

## D. 差分カテゴリ分類

| 区分 | 対象 | 判定 |
| ---- | ---- | ---- |
| **A** 公開済み・clean | 260529 詳細、archive 一覧、manifest | 差分なし ✓ |
| **B** 不要副産物 | share/**、他 archive/*、negotiation | full 再生成。今回公開範囲外 |
| **C** 別 Go 候補 | 上記 B のうち、将来公開に価値あり | restore 済み（次回 full 生成で再現可） |
| **D** 保留 | （なし — 全て B と判定） | — |
| **E** 未追跡生成物 | `output/` | commit しない。削除せず残存 |

---

## E. share/** の判断

9 ファイルとも差分は **+23 行** のみ:

- 末尾への空行
- `<!-- share-live-edit-inject:begin -->` ブロック（detail-edit JSONP inject）

**内容・径間データの変更なし。** full 生成の定型副産物 → **restore**。

---

## F. portal/negotiation の判断

| 変化 | 内容 |
| ---- | ---- |
| 件数表示 | 30 件 → 29 件 |
| カード削除 | **51404222**（260529 完了済みのため交渉待ちから除外） |
| その他 | `data-card-index` の繰り下げ |

Supabase 正本に沿った再生成だが、**交渉待ち HTML の明示公開 Go なし** → ローカルだけ先行すると Pages とズレるため **restore**（別 Go で再生成・公開）。

---

## G. 他 archive 日差分の判断

14 日分（260507–528, 260601）。主な差分:

1. **CSS / レイアウトテンプレート** — `.portal-page-nav` → `.top-bar`、`planned-incomplete-section` 用 CSS 追加（260518 等は既に一部公開済みスタイルの再適用）
2. **260601** — export 未整備のため **完了カード本文が消える** 方向の再生成（危険）→ 必ず restore

いずれも **今回の 260529 公開スコープ外** → **restore**。

---

## H. restore したもの

```text
git restore -- share/260604/index.html share/260605/index.html share/260606/index.html
  share/260608/index.html share/260609/index.html share/260610/index.html
  share/260611/index.html share/260612/index.html share/261231/index.html

git restore -- portal/negotiation/index.html

git restore -- portal/archive/260507/index.html portal/archive/260508/index.html
  portal/archive/260509/index.html portal/archive/260511/index.html
  portal/archive/260512/index.html portal/archive/260513/index.html
  portal/archive/260514/index.html portal/archive/260515/index.html
  portal/archive/260521/index.html portal/archive/260522/index.html
  portal/archive/260525/index.html portal/archive/260526/index.html
  portal/archive/260527/index.html portal/archive/260528/index.html
  portal/archive/260601/index.html

git restore -- docs/work_logs/2026-06-03_completion_archive_planned_incomplete_publish_result.md
```

（commit hash 追記の未 commit 修正も含む — 別途必要なら docs だけ再編集可）

---

## I. restore せず残したものと理由

| 残存 | 理由 |
| ---- | ---- |
| `?? output/` | 検証ログ・一時スクリプト。secret なし。削除は未実施（`git clean` 禁止方針） |

---

## J. output/ の扱い

| ファイル例 | 用途 |
| ---------- | ---- |
| `precheck_*.log` | full 生成ログ |
| `*_verify.py` | ローカル検証スクリプト |
| `survey_addition_coordinate_audit.json` | 座標監査（status 名のみ、鍵なし） |
| `apply_supabase_*.txt` | 過去 CLI 出力コピー |

**commit しない。** `.gitignore` 未登録のまま未追跡で残す。

---

## K. secret 確認

`output/` を pattern 検索 — `service_role` / API key / token 実値 **なし**（`supabase_status` 等の業務列名のみ）。

---

## L. 作業後 git status

```text
?? output/
```

`git diff --stat` — 空（追跡ファイル差分なし）。

---

## M. リスク/注意

- 次回 `full` 生成で **share inject / negotiation / 他 archive** 差分は再発する。公開 Go 前に `git status` でスコープ確認すること。
- `260601` 等は export 未揃いのまま full すると **空ページ化** しうる — strict-root 運用を維持。

---

## N. 人間確認事項

1. 交渉待ちから 51404222 除外を **portal/negotiation として公開するか**（別 Go）
2. share detail-edit inject を **まとめて公開するか**（別 Go）
3. 他 archive 日へ **planned-incomplete CSS / top-bar** を揃えて一括公開するか

---

## O. 次の一手

1. ippatsu-pc: 51404109/117/127 の status 業務確認（タスク 16）
2. `export_summary.exported_at` 鮮度チェック（タスク 7）
3. 必要なら **スコープ限定** で portal/negotiation または share のみ明示 add 公開

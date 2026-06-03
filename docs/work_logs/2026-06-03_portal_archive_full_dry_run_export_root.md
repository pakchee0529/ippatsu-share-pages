# portal archive full dry-run（completion export root 明示）

日付: 2026-06-03  
リポジトリ: ippatsu-share-pages（export: ippatsu-pc read-only）  
制約: portal 公開なし / data 変更なし / output commit なし

---

## A. 結論

1. ippatsu-pc で 260518/519/520/529 を **再 export**（4 日付・`export_summary` 更新済み）。
2. share-pages で **`--completion-reports-root` + strict-root + strict-summary** の full 生成を実施（**strict-missing は未使用** — manifest 全 19 日付に export が無いため）。
3. 対象 4 日付の archive detail 件数は export と一致。**260529 manifest/index は 1 件に整合**（`archive_manifest.json` 自動 sync + 一覧表示ロジック修正）。
4. portal HTML / share inject はローカル生成のみ **commit しない**。

---

## B. 背景

前タスクで `--completion-reports-root` を追加し、completion-archive 単日 dry-run は成功。一方 `archive_manifest.json` の 260529 が `item_count: 4` のまま残り、detail 1 件と不整合だった。

---

## C. export 再生成結果

コマンド（ippatsu-pc）:

```text
python tools/export_completion_reports_from_supabase.py \
  --dates 260518 260519 260520 260529 \
  --output-dir output/completion_reports_export \
  --compare-legacy
```

| 日付 | export items | legacy | 備考 |
| ---- | ------------ | ------ | ---- |
| 260518 | 4 | 4 | `portal_field_gaps_in_export` 空 |
| 260519 | 6 | 6 | 同上 |
| 260520 | 7 | 7 | 同上 |
| 260529 | 1 | 4 | legacy のみ 51404109/117/127（incomplete 3）— export 対象外 |

`export_summary.json` に上記 **4 日付** を記録。Supabase write なし / `data/completion_reports` 未変更。

---

## D. full dry-run 条件

```text
python scripts/generate_portal.py --mode full \
  --completion-reports-root <ippatsu-pc>/output/completion_reports_export \
  --strict-completion-reports-root \
  --strict-completion-reports-summary
```

**未使用:** `--strict-completion-reports-missing` — manifest 登録日（例: 260601）に export JSON が無く exit 1 になるため。全 manifest 日を export するまで full では使わない。

---

## E. completion_reports_root の確認

- ログ: `completion_reports_root=...\output\completion_reports_export (source=explicit)`
- legacy fallback 警告なし（root 明示時）
- `export_summary` 4 日付を stdout 表示

---

## F. archive detail 件数

| date | `archive detail … items=` | detail HTML `class="card"` |
| ---- | --------------------------- | -------------------------- |
| 260518 | 4 | 4 |
| 260519 | 6 | 6 |
| 260520 | 7 | 7 |
| 260529 | 1 | 1 |

manifest 上の他日付で export JSON が無い場合は `items=0` + 未生成メモ（想定内）。

---

## G. manifest / index 件数整合

**実装（今回）**

- `--completion-reports-root` 指定時、`build_archive_row_context` は **読取 items 数**を一覧 `archive-count` に使用（manifest 旧件数を使わない）。
- 同条件で `sync_archive_manifest_counts_from_completion_export` が **export 読取可能な日付のみ** `archive_manifest.json` の `item_count` / `completed_count` / `incomplete_count` / title 末尾 `N件` を更新。

**260529 結果**

| 項目 | 値 |
| ---- | -- |
| manifest `item_count` | 1 |
| manifest `completed_count` / `incomplete_count` | 1 / 0 |
| title | `2026年05月29日 1件` |
| `portal/archive/index.html` | `1件` / `完了1 / 未完了0` |

---

## H. 260529 incomplete 3 件の扱い

- export・detail・manifest いずれにも **含めない**
- detail HTML に 51404109/117/127 なし

---

## I. export_summary strict 確認

- 4 日付とも `strict-completion-reports-summary` で停止せず完了（loaded 件数 = summary `item_count`）
- トップレベル `exported_at` 鮮度チェックは未実装（次タスク）

---

## J. 公開しなかったこと

- GitHub Pages / 公開用 push なし
- `portal/*.html` / `share/*/index.html` の dry-run 差分は **commit しない**

---

## K. 変更したファイル（commit 対象）

| ファイル | 内容 |
| -------- | ---- |
| `scripts/generate_portal.py` | export 由来 manifest sync・一覧件数優先 |
| `portal/archive_manifest.json` | 260529 を 1 件に更新（sync 結果） |
| `docs/work_logs/2026-06-03_portal_archive_full_dry_run_export_root.md` | 本ログ |
| `docs/next_cursor_tasks.md` | 次タスク更新 |

---

## L. リスク / 注意

| リスク | 注意 |
| ------ | ---- |
| full + explicit root で export 無し日は detail 0 件 | 公開前は対象日のみ export するか、legacy data fallback を別運用 |
| `strict-missing` は全 manifest export 後のみ | 現状 19 日中 5 JSON のみ output に存在 |
| Windows console | negotiation 統計 print で UnicodeEncodeError が出る場合あり（生成本体は完了） |
| full は share inject も走る | commit 範囲から HTML を除外すること |

---

## M. 人間確認事項

1. ブラウザで `portal/archive/260529/` を目視（1 カードのみ）
2. 公開前: 対象日付の export 再生成 → full + explicit root
3. 公開 Go（別タスク）— 今回は未実施

---

## N. 次の一手

1. 人間 Go 後に portal 公開（export → full → 確認）
2. `export_summary.exported_at` 鮮度チェック
3. manifest 全日分 export または legacy fallback 方針の整理
4. 公開成功後の `data/completion_reports` snapshot（任意）

---

## O. git status --short（作業後・commit 前）

```
 M portal/archive*/index.html  （多数・commit しない）
 M portal/archive_manifest.json
 M scripts/generate_portal.py
 M share/*/index.html         （full inject・commit しない）
?? output/
```

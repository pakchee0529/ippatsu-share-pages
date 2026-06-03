# portal archive — completion_reports root 明示化

日付: 2026-06-03  
リポジトリ: ippatsu-share-pages  
制約: portal 公開なし / data 変更なし / output commit なし

参照: ippatsu-pc `docs/work_logs/2026-06-03_completion_reports_export_timing_policy.md`

---

## A. 結論

`scripts/generate_portal.py` に **`--completion-reports-root`** を追加した。アーカイブ詳細は指定ディレクトリ直下の `YYMMDD.json` を読む。未指定時は **legacy fallback**（`data/completion_reports`）に警告付きでフォールバック。**`--strict-completion-reports-root`** で未指定時に停止可能。

dry-run（`completion-archive` + export root）で 260518=4 / 260519=6 / 260520=7 / 260529=**1** を確認。260529 の incomplete 3 件は HTML に出ない。

---

## B. 背景

完了正本は Supabase。副本 JSON は portal 公開素材。公開前に `data/completion_reports` を先行更新しない方針のため、portal 生成は **`ippatsu-pc/output/completion_reports_export`** を明示読取する必要があった。従来は `_completion_reports_root` が `ippatsu-pc/data/completion_reports` を暗黙参照していた。

---

## C. 実装した引数

| 引数 | 説明 |
| ---- | ---- |
| `--completion-reports-root DIR` | 副本 JSON ルート（`260518.json` 等が直下） |
| `--strict-completion-reports-root` | 上記未指定で exit 1 |
| `--strict-completion-reports-missing` | 対象日の JSON 無しで exit 1 |
| `--strict-completion-reports-summary` | `export_summary` の item_count と不一致で exit 1 |

既存 `--data-root` は survey 等用。archive の completion_reports は **`--completion-reports-root` 優先**。

---

## D. completion_reports root の優先順位

1. `--completion-reports-root`（**explicit**）
2. `--data-root` / 既定 `ippatsu-pc/data` の **`completion_reports/` サブディレクトリ**（legacy fallback）
3. 未指定 sibling `ippatsu-pc/data/completion_reports`（legacy fallback default）

---

## E. data fallback の扱い

- 未指定時: stderr に **legacy fallback** 警告 + 実際に読んだパスを表示
- Supabase 正本モード / 公開前: **`--completion-reports-root` 必須**（運用）。CI 等では `--strict-completion-reports-root` 可
- `data/completion_reports` を先に最新化しない方針は ippatsu-pc 側ポリシーと一致

---

## F. dry-run 生成条件

- export: `C:\Users\kotan\Projects\ippatsu-pc\output\completion_reports_export`（既存 dry-run 出力・commit なし）
- コマンド例:

```text
python scripts/generate_portal.py --mode completion-archive --date 260518 ^
  --completion-reports-root C:\Users\kotan\Projects\ippatsu-pc\output\completion_reports_export
```

- 260518 / 260519 / 260520 / 260529 を各 1 回ずつ実行
- 生成 HTML は **commit しない**（ローカル確認のみ）

---

## G. dry-run 結果

| 項目 | 結果 |
| ---- | ---- |
| 終了コード | 0（4 日付とも） |
| ログ `source=` | すべて **explicit** |
| `completion_reports_root` | `...\output\completion_reports_export` |
| legacy data 読込 | ログ上なし（explicit 指定時） |

---

## H. 260518 / 519 / 520 / 529 の件数

| date | `archive detail … items=` |
| ---- | ------------------------- |
| 260518 | 4 |
| 260519 | 6 |
| 260520 | 7 |
| 260529 | 1 |

---

## I. 260529 incomplete 3 件の扱い

- export JSON: **51404222 完了 1 件のみ**
- 生成 HTML: カード 1 件（白銀149S2～149S3）。legacy の incomplete 3 件（51404109/117/127）は **含まれない**
- manifest の `item_count: 4` は未更新（一覧メタは別作業）

---

## J. export_summary / 鮮度チェック

- root 指定時、`export_summary.json` があれば日付別 `item_count` / `case_count` を stdout に表示
- 現状の export_summary は **260507 のみ** 1 日分（再 export で 4 日付分を載せると summary 照合が有効化）
- `--strict-completion-reports-summary`: summary にある日付で loaded 件数不一致時に停止
- トップレベル `exported_at` は summary に無い場合あり → ippatsu-pc 側拡張は次タスク

---

## K. 公開しなかったこと

- GitHub Pages / git push による公開反映は行っていない
- `portal/*.html` は dry-run でローカル上書きしたが **commit 対象外**

---

## L. リスク / 注意

| リスク | 注意 |
| ------ | ---- |
| export 古いまま portal 生成 | 公開直前に ippatsu-pc export CLI で再生成 |
| legacy fallback 誤使用 | 警告を見逃さない / strict フラグ |
| manifest 件数と詳細件数のズレ | 260529 等は manifest 更新が別途必要 |
| `completion-archive` でも TOP/archive 一覧 HTML は更新される | 公開コミット時は差分範囲に注意 |

---

## M. 人間 Go が必要な操作

1. 公開前: ippatsu-pc で対象日付を **再 export**
2. 全 manifest 日付の archive 再生成（`full` または日付ループ）+ `--completion-reports-root`
3. 目視確認後 **portal 公開**
4. 任意: 公開成功後 `data/completion_reports` snapshot

---

## N. 次の一手

1. export CLI で 260518–529 をまとめて再 export（`export_summary` を 4 日付分に）
2. `full` + `--completion-reports-root` + `--strict-completion-reports-root` で本番相当 dry-run
3. manifest 260529 の `item_count` を export 整合後に更新（別 PR）
4. ippatsu-pc: `export_summary.exported_at` トップレベル追加

---

## O. git status --short（作業時点）

```
?? output/
（portal HTML は dry-run 上書き・commit しない）
```

コミット対象: `scripts/generate_portal.py`, 本ログ, `docs/next_cursor_tasks.md` のみ。

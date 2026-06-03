# portal archive 公開前 precheck

日付: 2026-06-03  
リポジトリ: ippatsu-share-pages（export: ippatsu-pc read-only）  
**まだ公開 push していない**

---

## A. 結論

| 判定 | 内容 |
| ---- | ---- |
| export | 260518=4 / 260519=6 / 260520=7 / 260529=1。`portal_field_gaps_in_export` 空。summary 4 日付 |
| full 生成 | explicit root + strict-root + strict-summary で **exit 0**（stdio UTF-8 緩和後） |
| archive 4 日付 | detail / manifest / index 件数整合 |
| 260529 | **1 件のみ**。incomplete 3 件（51404109/117/127）は HTML に無し。51404222 のみ |
| 公開 Go | **ローカル HTML + manifest は準備済み**。人間目視後に commit/push（本 precheck では HTML 未 push） |

---

## B. export 再生成結果

ippatsu-pc（read-only）:

```text
python tools/export_completion_reports_from_supabase.py \
  --dates 260518 260519 260520 260529 \
  --output-dir output/completion_reports_export \
  --compare-legacy
```

| 日付 | items | legacy | 備考 |
| ---- | ----- | ------ | ---- |
| 260518 | 4 | 4 | gaps 空 |
| 260519 | 6 | 6 | gaps 空 |
| 260520 | 7 | 7 | gaps 空 |
| 260529 | 1 | 4 | legacy のみ 51404109/117/127 |

Supabase write なし / `data/completion_reports` 未変更 / `output/` 未 commit。

---

## C. full 生成条件

```text
python scripts/generate_portal.py --mode full \
  --completion-reports-root <ippatsu-pc>/output/completion_reports_export \
  --strict-completion-reports-root \
  --strict-completion-reports-summary
```

- `--strict-completion-reports-missing` は **未使用**（manifest 19 日のうち export JSON は一部のみ）

---

## D. completion_reports_root 確認

- `completion_reports_root=...\output\completion_reports_export (source=explicit)`
- legacy fallback 警告なし
- `export_summary` に 4 日付（260518–529）を表示
- strict-summary 不一致による停止なし

---

## E. archive detail 件数

| date | ログ `items=` | HTML `article.card` |
| ---- | ------------- | ------------------- |
| 260518 | 4 | 4 |
| 260519 | 6 | 6 |
| 260520 | 7 | 7 |
| 260529 | 1 | 1 |

export 無しの他 manifest 日は `items=0` + 未生成メモ（公開対象外として想定内）。

---

## F. manifest / index 整合

**`portal/archive_manifest.json`（コミット済み 6279663 時点）**

| date | item | completed | incomplete |
| ---- | ---- | --------- | ---------- |
| 260529 | 1 | 1 | 0 |
| 260518–520 | 4 / 6 / 7 | 各完了のみ | 0 |

**`portal/archive/index.html`（ローカル生成・未 commit）**

- 260529: `archive-count` **1件**、`完了1 / 未完了0`
- 260518–520: manifest 件数と一致

---

## G. HTML 差分概要（未 commit・HEAD 比）

| パス | 概要 |
| ---- | ---- |
| `portal/archive/260529/index.html` | **4 カード → 1 カード**（export 準拠。旧 incomplete 3 サイト削除） |
| `portal/archive/260518–520/index.html` | export 由来の再生成（行の入替・地図/指示表は同一方針） |
| `portal/archive/index.html` | 260529 一覧が 1 件表示に更新 |
| `portal/archive_manifest.json` | **差分なし**（前コミットで 260529=1 済み） |
| `share/*/index.html`（9 件） | full の detail-edit inject（+54 行程度）。archive 公開とは別範囲で要判断 |

**data/completion_reports 参照の痕跡:** 生成ログはすべて explicit export root。HTML 内に legacy incomplete 3 件なし。

---

## H. 260529 incomplete 3 件

- export・detail・manifest に **含めない**
- 51404109 / 51404117 / 51404127: `260529/index.html` に **なし**
- 51404222: **あり**（完了 1 件）

---

## I. UnicodeEncodeError 確認

| 項目 | 結果 |
| ---- | ---- |
| 原因 | `survey_map_coord_warnings` 等の **末尾 print**（文字 `\u2014`）が cp932 で失敗 |
| HTML | archive / survey は **エラー前に書き込み済み**（exit 1 時も archive 完了） |
| 対策 | `main()` 先頭で `_configure_stdio_encoding()`（stdout/stderr UTF-8 replace） |
| 修正後 | `PYTHONIOENCODING` 無しでも full **exit 0**。negotiation まで完了 |

**公開成果物（HTML ファイル）への影響なし**（UTF-8 で書込済み）。

---

## J. 公開しなかったこと

- GitHub Pages / 公開用 push **未実施**
- `portal/archive/*.html` / `share/*/index.html` は **本 precheck コミットに含めない**

---

## K. 公開 Go 時に commit すべきファイル

**archive 公開スコープ（推奨）**

- `portal/archive/260518/index.html`
- `portal/archive/260519/index.html`
- `portal/archive/260520/index.html`
- `portal/archive/260529/index.html`
- `portal/archive/index.html`
- 他 manifest 日の `portal/archive/<date>/index.html`（今回 full で更新された分。export 無し日は「未生成」表示のまま）

**既に main にある**

- `portal/archive_manifest.json`（260529=1）
- `scripts/generate_portal.py`（root 明示・sync・stdio 緩和は本 precheck で追記予定）

**別判断**

- `share/*/index.html` — full inject 差分。archive のみ公開なら含めない選択可
- `portal/index.html` / `portal/survey/` / `portal/negotiation/` — 今回 full で更新。セット公開か要方針

---

## L. リスク / 注意

| リスク | 注意 |
| ------ | ---- |
| export 無し manifest 日 | detail 0 件ページが残る。公開セットを 4 日付に限定するか全 manifest export か決める |
| share 差分同梱 | archive のみ push するか full portal 一式か |
| 260507 | output に JSON あり（3 件）。今回 4 日付以外は意図的スコープ外 |
| 再生成のたび share inject | `full` は share も触る。公開 commit 範囲を明確に |

---

## M. 人間確認事項

1. ブラウザで `portal/archive/260529/` — **1 カード**のみ
2. 260518/519/520 の代表 1 現場ずつ目視
3. 公開 commit 範囲（archive のみ vs portal 一式 vs share 含む）
4. **Go 後**に commit → push → Pages 反映

---

## N. 次の一手

1. 人間 Go
2. 公開用 commit（上記 K）→ `git push origin main`
3. Pages 反映確認
4. 任意: 公開成功後 ippatsu-pc `data/completion_reports` snapshot

---

## O. git status --short（precheck 作業後）

```
 M portal/archive/**/index.html  （多数）
 M share/*/index.html
 M scripts/generate_portal.py     （stdio 緩和）
?? output/
```

本コミット: `docs/...publish_precheck.md`, `docs/next_cursor_tasks.md`, `scripts/generate_portal.py`（stdio のみ）。**HTML は push しない。**

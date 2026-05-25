# Work log: Restore real survey/negotiation portal from production queue (company PC)

| 項目 | 値 |
|------|-----|
| **Date** | 2026-05-25 |
| **Agent** | Cursor |
| **Repo** | ippatsu-share-pages |
| **Status** | **完了** — 本番 `queue.json` から正式再生成・commit 予定 |

## Purpose

家PC暫定公開（survey HTML 抽出 + negotiation overlay 正本）を、会社PCの正本 `queue.json` から
`PORTAL_IMMEDIATE_STATUS=1` で `generate_portal.py` により置き換える。

## Pre-check（未コミット差分）

| Repo | 差分 | 扱い |
|------|------|------|
| ippatsu-share-pages | `?? tools/` のみ（作業前） | 本 commit には含めない |
| ippatsu-pc | 多数の M/??（map_creation 等） | 触らず報告のみ |
| ippatsu-pc-prod | `?? data/` | 正本 data。読取専用 |

## 正本 data

| 項目 | 値 |
|------|-----|
| **queue.json** | `C:\Users\kotan\Projects\ippatsu-pc-prod\data\survey\queue.json` |
| **data-root** | `C:\Users\kotan\Projects\ippatsu-pc-prod\data` |
| **根拠** | AGENTS.md §0.1（会社PC本番 data）。`ippatsu-pc\data\queue.json` は件数不一致（交渉3件）のため未使用 |
| **queue 総件数** | 45 |
| **現調待ち（生成）** | 44（`survey_exclude_reasons`: `survey_done` ×1） |
| **交渉待ち（生成）** | 1 |
| **テストキー** | 99990001 / 99990002 / 99990003 — **なし** |

## 実行

```powershell
cd C:\Users\kotan\Projects\ippatsu-share-pages
git pull origin main

$anon = python scripts/load_portal_apikey_for_generate.py
$env:PORTAL_SURVEY_REQUEST_API_KEY = $anon
$env:PORTAL_IMMEDIATE_STATUS = "1"

python scripts/generate_portal.py --mode full --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data
```

- `load_portal_apikey_for_generate.py` は既存 `portal/survey/index.html` から anon を解決（値はログに出さない）。
- `--mode full` は archive/share 等も更新するが、**commit 対象は survey / negotiation のみ**（副産物は add しない）。

## 再生成ページ（commit 対象）

- `portal/survey/index.html` — `survey_items=44`
- `portal/negotiation/index.html` — `negotiation_items=1`

## 事後確認

| 確認 | 結果 |
|------|------|
| テストキー 99990001–03 | ✅ 両 HTML に一致なし |
| 実案件（例 51409*） | ✅ survey にあり |
| `portal/negotiation/index.html` 存在 | ✅ |
| B案 JS（`mark_survey_done` / `revert_to_survey_wait` / `serverOk` / `beforebegin`） | ✅ |
| `PORTAL_STATUS_API_KEY` 空でない | ✅（値は非表示） |
| `sb_secret_` / `SUPABASE_ACCESS_TOKEN` / service_role 実値 | ✅ なし |
| `ippatsu-pc` `check-fn` | ✅ HTTP 200 / `ok: true`（overrides 複数あり。削除せず） |

## API overrides（参考・変更なし）

`immediate_status_e2e_setup.py check-fn` で `negotiation_wait` の overlay が複数存在（家PC E2E 由来の可能性）。
本番 queue 静的生成（交渉1件）とは別レイヤ。勝手に `cleanup` しない。

## Commit

```
Restore real survey and negotiation portal data from production queue
```

Files: `portal/survey/index.html`, `portal/negotiation/index.html`, 本 work log のみ。

## 残作業

- [ ] GitHub Pages 反映後、スマホで survey / negotiation spot check
- [ ] overlay と queue 静的件数の差が意図通りか（必要なら ippatsu-pc 側で overlay 整理は別タスク）

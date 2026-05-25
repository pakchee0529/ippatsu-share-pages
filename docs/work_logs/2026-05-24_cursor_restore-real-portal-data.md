# Work log: Restore real survey/negotiation portal data

| 項目 | 値 |
|------|-----|
| **Date** | 2026-05-24 |
| **Agent** | Cursor |
| **Repo** | ippatsu-share-pages |
| **Status** | **BLOCKED（家PC）** — 本番 `queue.json` 不在のため再生成未実施 |

## Purpose

E2E テスト用 queue（99990001–99990003）で上書きした `portal/survey` / `portal/negotiation` を、
**実データ + B案（PORTAL_IMMEDIATE_STATUS=1）** で `generate_portal.py` から復旧する。

## Pre-check（実施済み）

| 確認 | 結果 |
|------|------|
| `portal/survey` に 99990001/02 | ✅ あり（テストページのまま） |
| `portal/negotiation` に 99990003 | ✅ あり |
| `portal_immediate_status_client.py` | ✅ `serverOk` + `beforebegin` 修正残存 |
| `C:\Users\yawar\Projects\ippatsu-pc\data\survey\queue.json` | ❌ **不存在** |
| `C:\Users\kotan\Projects\ippatsu-pc-prod\data\survey\queue.json` | ❌ パスなし（会社PC） |
| 家PC 上のその他 `queue.json` | ❌ `.e2e_data` のテスト用のみ |
| Supabase REST（anon）cases 読取 | ❌ 0件（RLS または列制約） |

## Block reason

AGENTS.md §0.1: 家PCには本番 `data/survey/queue.json` なし。  
任務書 §3: **実データがこのPCに無い場合は停止して報告**。

`portal/survey/index.html` の git 履歴（`8cce077` / `b5b7c37`）には実案件（例: 51409324）が埋め込まれているが、
**生成スクリプトからの再生成**要件のため、HTML の checkout だけでは完了扱いにしない。

## Company PC — 実行コマンド（人間 / 会社PC）

```powershell
cd C:\Users\kotan\Projects\ippatsu-share-pages
git pull origin main

$anon = python scripts/load_portal_apikey_for_generate.py
if (-not $anon) { throw "anon key missing — set PORTAL_SURVEY_REQUEST_API_KEY or regenerate once with key in env" }
$env:PORTAL_SURVEY_REQUEST_API_KEY = $anon
$env:PORTAL_IMMEDIATE_STATUS = "1"

python scripts/generate_portal.py --mode full --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data

# 確認（テストキーなし・実案件あり）
Select-String -Path portal/survey/index.html -Pattern "99990001|99990002|99990003"
Select-String -Path portal/survey/index.html -Pattern "51409" | Select-Object -First 3
Select-String -Path portal/survey/index.html,portal/negotiation/index.html -Pattern "service_role|SUPABASE_ACCESS_TOKEN" | Where-Object { $_.Line -notmatch "Never embed" }

git add portal/survey/index.html portal/negotiation/index.html docs/work_logs/2026-05-24_cursor_restore-real-portal-data.md
git commit -m "Restore real survey and negotiation portal data"
git push origin main
```

## Overlay 残骸（ippatsu-pc）

家PCで `cleanup-test-keys` 実行可能（anon key が HTML から読める場合）:

```powershell
cd C:\Users\kotan\Projects\ippatsu-pc
$env:PORTAL_SURVEY_REQUEST_API_KEY = "<anon — do not paste in chat>"
python tools/immediate_status_e2e_setup.py cleanup-test-keys
```

## Next

- [ ] 会社PCで上記 generate + commit + push
- [ ] スマホで実案件の survey / negotiation を spot check
- [ ] `99990001` 等がページに無いことを確認

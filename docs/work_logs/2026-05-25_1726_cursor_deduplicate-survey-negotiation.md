# Work log: Deduplicate survey and negotiation portal cases

| 項目 | 値 |
|------|-----|
| **Date** | 2026-05-25 |
| **Agent** | Cursor |
| **Repo** | ippatsu-share-pages |
| **data-root** | `C:\Users\kotan\Projects\ippatsu-pc-prod\data` |

## 重複確認（修正前）

| 指標 | 件数 |
|------|------|
| static survey（HTML） | 44 |
| static negotiation（HTML） | 1 |
| overlay `negotiation_wait`（check-fn） | 6（解析時） |
| static survey ∩ static negotiation | **0** |
| static survey ∩ overlay negotiation_wait | **6** |
| static negotiation ∩ overlay negotiation_wait | **0** |

重複の実態: queue 上は相補だが、**portal overlay で昇格した案件が survey 静的 HTML に残る**（B 案）。

## 修正内容

### `scripts/generate_portal.py`

- `is_pending_survey_item`: `is_negotiation_wait_item` が真の行を現調待ちから除外。
- `load_survey_public_items`: `exclude_portal_overlay_keys` で overlay `negotiation_wait` を静的 survey から除外（`portal_status_overlay` として集計）。
- `load_survey_promoted_candidate_items`: 昇格カード用メタは overlay 除外前の現調待ち候補を維持。
- 生成時 `fetch_portal_negotiation_wait_keys`（anon）で overlay 一覧を取得し survey 静的リストから除外。

### `scripts/portal_immediate_status_client.py`

- `fetch_portal_negotiation_wait_keys()` を追加（GET overrides、キーのみ返す）。
- survey JS: `fetch` 前に `applySurveyOverlay({}, false)` で localStorage 分を先に非表示（ちらつき低減）。

### 再生成

```powershell
PORTAL_IMMEDIATE_STATUS=1
python scripts/generate_portal.py --mode full --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data
```

- survey: **32** 件（`portal_status_overlay` 12、`negotiation_wait` 1）
- negotiation: **1** 件（静的）
- full 副産物（archive/share/portal/index）は **restore** 済み

## 修正後確認

| 確認 | 結果 |
|------|------|
| static survey ∩ static negotiation | **0** |
| static survey ∩ overlay（静的 HTML 上） | **0** |
| テストキー 99990001–03 | なし |
| `mark_survey_done` / `revert_to_survey_wait` | あり |
| secret 実値混入 | なし |

## 本番 data

- `queue.json` は**未編集**（読取のみ）。

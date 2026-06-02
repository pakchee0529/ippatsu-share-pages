# 2026-06-02 survey addition script coordinate audit

## A. 結論

- **現調待ち追加用 `.py` は GPS.json ベースの dry-run プレビューであり、ハルシネーション/ハードコード座標は使っていない。**
- **地図 UI 欠落（19 件中 14 ピン・5 件ボタンなし）の主因は、Supabase 正本 + `ippatsu-pc/data/survey/queue.json`（dev）補完の二層構造で、7 件追加案件が prod queue にだけ存在し dev queue に無かったこと。**
- **`51410418` は prod queue に座標あり・dev queue なし → 生成時 merge 不能 → 一覧のみ（分類 C）。国外ピンは当該スクリプト由来の推定座標では説明できない（座標は GPS 電柱解決）。**
- **最小修正:** `load_survey_public_items` に GPS.json 直接補完 `_supplement_map_fields_from_gps` を追加し再生成。survey multipin **19/19**、範囲外 0。

## B. 調査対象スクリプト

| ファイル | Git | 役割 |
|----------|-----|------|
| `ippatsu-pc/tools/preview_survey_wait_additions_20260529.py` | **未追跡 (`??`)** | 7 件の GPS 解決 + queue/case プレビュー出力（dry-run） |
| `ippatsu-pc/tools/apply_survey_queue_keys_to_supabase.py` | 追跡済み | prod `queue.json` から指定 7 key を Supabase INSERT |
| `ippatsu-share-pages/scripts/generate_portal.py` | 追跡済み | Supabase 正本 + dev `queue.json` merge → portal HTML |
| `ippatsu-share-pages/scripts/audit_survey_addition_coordinate_mismatch.py` | 新規（監査用） | 突合 JSON 出力 |

## C. スクリプトの目的 / 入出力

### `preview_survey_wait_additions_20260529.py`

- **目的:** 2026-05-29 追加予定 7 件の座標を GUI 同等ロジックで解決し、投入前プレビューを作る。
- **入力:** `app/resources/data/GPS.json`（`load_pole_coords`）
- **出力（書き込み先は output のみ）:**
  - `output/new_survey_queue_items_20260529.json`
  - `output/new_survey_cases_20260529/<key>.json`
  - `output/new_survey_cases_20260529/_resolution_report.json`
- **queue.json / Supabase:** 直接書かない（コメントで prod merge は人間 Go 後と明記）。

### `apply_survey_queue_keys_to_supabase.py`

- **入力:** `ippatsu-pc-prod/data/survey/queue.json`（7 key 必須）
- **出力:** Supabase `cases` INSERT（座標は queue レコード経由の import パイプライン）

## D. GPS.json 参照の有無

- **preview スクリプト:** あり。`share_gps_autofill` → `resolve_one` / `range_two_pole`（ippatsu-pc `app.core.search`）。
- **解決レポート:** 7/7 resolved、method は `range_two_pole` または `resolve_one`。
- **generate_portal（修正前）:** GPS.json は 2 点地図の nearby 用のみ。座標補完は dev `queue.json` merge のみ。

## E. ハードコード / 推定座標の有無

| 種別 | 有無 |
|------|------|
| ハードコード lat/lng | **なし** |
| LLM / ランダム推定 | **なし** |
| 中点 `map_url`（始終点の平均） | **あり**（表示用 URL のみ。ピンは始終点の GPS 座標） |
| 電柱検索フォールバック | **あり**（`general_search_order` / `exact_match` — 正規データ内） |

## F. 対象 management_no 一覧（preview 7 件）

`51404162`, `51402038`, `51410139`, `51410418`, `51410417`, `51400394`, `51403794`

## G. 対象番号の Supabase / queue / GPS / portal 突合（調査時点 → 修正後）

| key | Supabase status | prod queue + 座標 | dev queue | GPS 解決 | survey 地図 UI（修正前→後） |
|-----|-----------------|-------------------|-----------|----------|---------------------------|
| 51404162 | survey_wait | あり | **なし** | OK | なし → **あり** |
| 51402038 | survey_wait | あり | **なし** | OK | なし → **あり** |
| 51410139 | survey_wait | あり | **なし** | OK | なし → **あり** |
| 51410418 | survey_wait | あり | **なし** | OK | なし → **あり** |
| 51410417 | survey_wait | あり | **なし** | OK | なし → **あり** |
| 51400394 | negotiation_wait | あり | **なし** | OK | survey に出ない（正常） |
| 51403794 | negotiation_wait | あり | **なし** | OK | survey に出ない（正常） |

## H. survey_wait 19 件の地図 UI 欠落理由

- **14 件（分類 A）:** dev `queue.json` に同一 key が 1 件あり、merge 成功 → 地図/2 点/multipin あり。
- **5 件（分類 C）:** preview 7 のうち **現調待ちの 5 件**。prod queue のみに座標があり、`generate_portal.py` が参照する **dev queue に無い** → merge 0 件 → 座標空。
- **multipin 14 の理由:** multipin は妥当な単点座標があるカードのみ。5 件は単点属性なし。
- **修正後:** GPS 補完により **19 件すべて** multipin・地図ボタン・2 点地図ボタン。

## I. negotiation_wait 30 件の地図 UI 残骸理由

- 現行 `portal/negotiation/index.html` 再生成結果: **地図ボタン 0、data-two-open 0**（`build_negotiation_html` で地図 UI 非出力）。
- queue.json には交渉待ち案件の座標が残るが、**portal には出さない設計**（分類は queue 遺産、表示上は問題なし）。
- `51400394` / `51403794` は preview 対象だが **negotiation_wait** のため survey 地図対象外。

## J. queue.json が影響している範囲

- **正本:** Supabase `cases.status`（一覧の出所）。
- **補助:** `ippatsu-pc/data/survey/queue.json`（**dev**）— `generate_portal` の `_merge_legacy_map_fields` の唯一の legacy 源。
- **prod queue**（7 件入り）— Supabase INSERT には使われたが、**portal 生成パスでは未参照**（不整合の核心）。
- **国外ピン（過去）:** 当該 preview スクリプトの推定座標では説明困難。別経路（旧 HTML・範囲外 merge 前・目視誤認）の可能性が高い。現行 HTML ガード後は範囲外 multipin 0。

## K. 追加用 .py が原因かどうか

| 観点 | 判定 |
|------|------|
| 誤った/架空座標を直接書いた | **いいえ**（GPS.json 解決） |
| Supabase に survey_wait を増やした | **間接的に yes**（apply ツール + prod queue） |
| portal 地図欠落を作った | **間接的に yes**（prod のみ queue 更新 + dev 未同期） |
| negotiation 地図残骸 | **いいえ**（現行生成物では非表示） |

## L. 修正内容

1. `_supplement_map_fields_from_gps` — queue merge 後、label から `share_gps_autofill`（preview と同ロジック）で start/end を補完。JP 範囲外は採用しない。
2. `portal/survey/index.html` 再生成 — multipin 19 件、範囲外 0。
3. `scripts/audit_survey_addition_coordinate_mismatch.py` — 調査用突合（`output/` に JSON、commit 対象外）。

## M. 次の修正方針（未実施）

- dev/prod `queue.json` の 7 件同期（運用）または `--data-root` で prod data を指す運用ルールの明文化。
- `validate_survey_only_output` の `51403794` 必須チェック削除（既知残骸）。
- negotiation は現状維持（地図 UI なし）。

## N. 人間確認事項

- ローカル `portal/survey/index.html`: 19 件すべて地図ボタン・下部 19 ピン。
- `51410418` にピンが付くこと（GPS 解決座標。prod queue 未同期でも表示されること）。
- negotiation に地図ボタンが無いこと。

## O. 次の一手

- 人間 Go 前: push 禁止のまま目視。
- 運用: prod queue 追加分を dev `data/survey/queue.json` に同期するか、生成を `--data-root` prod に統一するか決定。
- 公開 Go 後のみ `origin/main` push。

## P. git status --short

（commit 直前の想定）

```
 M portal/survey/index.html
 M scripts/generate_portal.py
?? docs/work_logs/2026-06-02_survey_addition_script_coordinate_audit.md
?? scripts/audit_survey_addition_coordinate_mismatch.py
?? output/
```

# 2026-06-03 survey multipin HTML coordinate guard

## A. 結論
- `#share-map` マルチピン用座標を HTML 抽出監査し、範囲外 multipin は現行生成物に 0 件。
- 生成器に HTML 出力直前ガード + 書き込み前 `finalize_survey_map_html` + クライアント `isPortalJpLatLng` を追加。
- `51410418` は一覧維持・multipin 非付与（地図ボタン/ピンなし）。

## B. Leaflet が読む座標源（survey）
| 源 | 用途 |
|----|------|
| `data-multipin-lat` / `data-multipin-lng` | 下部 `#share-map`（`collectVisibleSurveyMultipinPoints` → `L.marker`） |
| `two-geo-N` JSON の `a`/`b`/`nearby` | カード内 2 点地図のみ（下部地図には未使用） |
| 静的 `var points` | 廃止済み |

## C. 前回スモークが見逃した理由
- `validate_survey_only_output` は `data-multipin-lat` の**存在**のみ確認し、全座標の範囲チェックなし。
- Python 側は merge 時ガード（`3be32a8`）のみで、**HTML 文字列への最終検証**がなかった。
- 監査用に `scripts/audit_survey_map_coords.py` を追加（article 開始タグ跨ぎの属性対応）。

## D. 修正内容
- `_multipin_data_attrs` / `finalize_survey_map_html` / `find_survey_html_multipin_violations`
- `build_survey_html` 戻り値を `finalize_survey_map_html` 経由
- `render_survey_multipin_js` に `isPortalJpLatLng`（33–36 / 134–137）
- `build_two_geo_payload` の nearby も JP 範囲外を除外

## E. 再生成スモーク
- survey-only: items=19, multipin=14, out_of_range=0, 51410418 multipin なし
- negotiation-only: validation OK, 地図ボタン・`#share-map` 非出力

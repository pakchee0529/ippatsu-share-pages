# 2026-06-02 share-pages: queue.json 座標主依存排除 Step 1

## A. 結論

`generate_portal.py` から **queue.json による座標 merge を廃止**し、portal 一覧は Supabase・地図座標は **GPS.json** のみを主軸にした。queue は **legacy_count / 差分 warning / 監査ログ** に限定。ローカルスモークは survey/negotiation とも **validation: OK**、multipin 19・範囲外 0 を維持。**portal HTML はコミット済み版と差分なし**（今回 commit は scripts + 本ログのみ）。

## B. 背景

[queue.json 役割整理](./2026-06-02_queue_json_role_and_deprecation_plan.md) で確定した方針の Step 1 実装。dev/prod queue ズレで `_merge_legacy_map_fields` が地図欠落を起こし得るため。

## C. 変更前の問題

- 一覧: Supabase 正本済み
- 座標: dev `queue.json` を merge → prod のみにある key で座標空
- GPS 直接補完で 19/19 復旧済みだが、queue merge が残ると再発リスク

## D. queue.json 参照の変更内容

| 処理 | 変更前 | 変更後 |
|------|--------|--------|
| `_merge_legacy_map_fields` | queue から start/end 座標 merge | **削除** → `_record_legacy_queue_audit` |
| `_record_legacy_queue_audit` | — | key 集合の差分 warning のみ、items 不変 |
| `_load_*_legacy` | 件数・legacy 抽出 | **維持**（read-only） |
| `_supplement_map_fields_from_gps` | queue 後の fallback | **主座標ソース**（docstring 更新） |

`stats["legacy_map_field_fallback_enabled"]` = `False`  
`stats["legacy_source"]` = `queue.json (audit only)`

## E. GPS.json 補完の主ソース化

- `load_survey_public_items`: Supabase → audit → **`_supplement_map_fields_from_gps`**
- 地図ボタン / two-geo / multipin は GPS 補完後の valid JP 座標のみで判定（従来ガード維持）

## F. legacy_count / warning の扱い

- `legacy_count`: `_load_survey_public_items_legacy` の visible 件数を `StatusSmoke` に渡す（従来通り）
- warning: `legacy_queue_keys_not_in_supabase`, `legacy_queue_key_count_mismatch` を `map_coord_warnings` に記録
- audit dict: `legacy_queue_keys_only_in_queue`, `legacy_queue_keys_only_in_primary` を stats に merge

## G. dev/prod queue ズレへの耐性

- queue の start/end は **カード・multipin に一切採用しない**
- dev queue が空 / 欠損でも GPS があれば地図 UI は成立
- prod のみにある queue key は warning のみ（表示件数・座標に影響しない）

## H. ローカル生成/スモーク結果

```
python -m py_compile scripts/generate_portal.py  # OK
python scripts/generate_portal.py --mode survey-only      # validation: OK, visible=19
python scripts/generate_portal.py --mode negotiation-only # validation: OK, visible=30, return_wait=3
python scripts/audit_survey_map_coords.py
  multipin_marker_count=19, out_of_range_multipin_count=0, key_51410418_multipin=あり
```

map_coord_warnings（期待どおり監査）:

- `legacy_queue_keys_not_in_supabase count=28 ...`
- `legacy_queue_key_count_mismatch legacy=42 supabase=19`

## I. 公開反映状況

- **未 push**（本タスク完了時点で commit 後に push 判断）
- `portal/*.html` は再生成しても **git diff なし** → push しても公開 HTML は変わらない見込み

## J. 人間確認事項

- 次回 **portal HTML に実差分が出る**再生成を push する場合は従来どおり **人間 Go**
- legacy warning 28 件は Supabase 未登録の queue 残骸。運用で整理するかは別判断

## K. まだ残る課題

- ippatsu-pc GUI の queue save 封鎖（Step 2）
- `apply_portal_overlay.py` queue patch 隔離（Step 3）
- Supabase vs GPS vs queue read-only 監査 CLI（Step 4）

## L. 次の一手

1. 本 commit を push（scripts/docs のみ・portal 差分なし）
2. 必要なら `_load_*_legacy` を key カウント専用に軽量化（任意）

## M. git status --short（作業直前）

```
 M scripts/generate_portal.py
?? docs/work_logs/2026-06-02_share_pages_queue_dependency_step1.md
?? output/
```

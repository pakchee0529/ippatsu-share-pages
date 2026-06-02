# 2026-06-02 queue.json 役割整理（ippatsu-share-pages 抜粋）

正本の棚卸し・段階廃止計画の全文は **ippatsu-pc** 側に置く。

- `C:\Users\kotan\Projects\ippatsu-pc\docs\work_logs\2026-06-02_queue_json_role_and_deprecation_plan.md`

## share-pages 固有の要点

### 参照コード

| ファイル | 役割 | 分類 |
|----------|------|------|
| `scripts/generate_portal.py` `_survey_source_path` | dev 既定 `../ippatsu-pc/data/survey/queue.json` | B→C（座標は GPS へ） |
| `_load_survey_public_items_legacy` | queue から現調/交渉候補抽出 | C（件数比較）/ B（フィルタロジック） |
| `_merge_legacy_map_fields` | Supabase 行へ map 座標 merge | **A/B**（dev/prod ズレで地図欠落の主因） |
| `_supplement_map_fields_from_gps` | GPS.json 直接補完 | **正しい座標経路** |
| `scripts/audit_survey_addition_coordinate_mismatch.py` | dev/prod queue 比較 | C |

### 現在の portal 生成フロー（survey）

1. Supabase `survey_wait` → 一覧・ラベル・管理番号（正本）
2. dev `queue.json` → legacy merge（座標・start/end）
3. GPS.json → 座標未充足分を補完（**46bef62 以降**）
4. HTML 出力 + multipin / 地図 UI ガード

### 推奨（案 C）

- Step 1: merge の座標入力を queue から外し **GPS のみ** + queue は `legacy_count` / warning
- `_survey_source_path` docstring を「legacy/cache パス」に修正

### 公開反映

- 本タスクは **docs のみ**。portal HTML 再生成・push は別 Go。

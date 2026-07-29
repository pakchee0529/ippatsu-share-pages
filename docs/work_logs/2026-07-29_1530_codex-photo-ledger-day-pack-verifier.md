# 作業ログ: 作業日QR札パックの公開検証対応

| 項目 | 値 |
|---|---|
| 日時 | 2026-07-29 15:30 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | codex/photo-ledger-day-case-switch |

## 変更ファイル

- `scripts/verify_photo_ledger_portal.py`
- `docs/work_logs/2026-07-29_1530_codex-photo-ledger-day-pack-verifier.md`

## 実施内容

- 単一案件22札を固定値で検査していた公開用verifierを、作業日パックの複数案件に対応させた。
- `caseCount`、案件ごとの22札、全marker IDの一意性、BA前後の終了モード、案件切替UIを検査する。
- 従来の単一案件パックもフォールバック形式として引き続き検査できる。

## 守った制約

- 公開PWAからSupabaseへ接続する処理は追加していない。
- 秘密情報、PC絶対パス、生写真を公開物へ含めていない。


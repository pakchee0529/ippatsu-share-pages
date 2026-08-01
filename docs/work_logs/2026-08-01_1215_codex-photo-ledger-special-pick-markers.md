# 作業ログ: 共有ポータルの倒木実費・自由記述採用札

| 項目 | 値 |
|---|---|
| 日時 | 2026-08-01 12:15 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | cursor/photo-ledger-paired-overview-pick |

## 内容

- 倒木実費を撮影前・撮影後採用のペアへ変更。
- 自由記述の撮影前・撮影後採用ペアを追加。
- 来週分の日付パックを26札形式へ更新。
- 特殊作業の前後ペア照合キーを拡張。

## 検証

- `python scripts/verify_photo_ledger_portal.py` 合格。
- PWA `app.js` の構文チェック合格。
- 260730は旧22札を保持し、来週分は26札。

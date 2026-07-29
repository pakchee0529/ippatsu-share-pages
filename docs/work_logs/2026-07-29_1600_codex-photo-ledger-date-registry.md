# 作業ログ: QR仕切り札の日付レジストリ対応

| 項目 | 値 |
|---|---|
| 日時 | 2026-07-29 16:00 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | codex/photo-ledger-date-registry |

## 変更ファイル

- `portal/photo-ledger/index.html`
- `portal/photo-ledger/styles.css`
- `portal/photo-ledger/app.js`
- `portal/photo-ledger/pack.js`
- `portal/photo-ledger/service-worker.js`
- `scripts/verify_photo_ledger_portal.py`
- `docs/work_logs/2026-07-29_1600_codex-photo-ledger-date-registry.md`

## 実施内容

- QR仕切り札パックを複数作業日保持できる version 4 レジストリ形式へ更新した。
- 保存済み日付、当日、直近の未来日、直近の過去日の順で作業日を自動選択するようにした。
- 複数日が登録された場合だけ作業日セレクタを表示し、日付ごとに案件一覧と予定数量を切り替えるようにした。
- COUNT・採用選択の途中は誤操作防止のため日付切替を止めるようにした。
- 旧単一日パックも引き続き読み込める互換性を残した。
- 静的検証に version 4 の日付数、既定日、日付重複チェックを追加した。

## 守った制約

- PWAからSupabaseや外部APIへ接続しない。
- 生写真、秘密情報、PC絶対パスを公開物へ含めない。
- 現行の単一日パックを壊さない。

## 検証

- `python scripts/verify_photo_ledger_portal.py`
- `git diff --check`
- Pixel 8a相当の画面幅で2日分の切替、案件表示、予定数量の切替を確認。

## 次に必要な作業

- いっぱつちゃん側から2日目が登録された時点で、公開ページに作業日セレクタが現れることを実機確認する。

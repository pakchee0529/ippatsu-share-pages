# 作業ログ: 写真台帳QR仕切り札のポータル同期

| 項目 | 内容 |
|------|------|
| 日時 | 2026-08-05 15:30 JST |
| 担当 | Codex |
| repo | ippatsu-share-pages |
| branch | cursor/photo-ledger-resilient-portal |

## 変更ファイル

- `portal/photo-ledger/index.html`
- `portal/photo-ledger/app.js`
- `portal/photo-ledger/styles.css`
- `portal/photo-ledger/manifest.webmanifest`
- `portal/photo-ledger/service-worker.js`
- `portal/photo-ledger/release-manifest.json`

## 実施内容

- いっぱつちゃん側を唯一のPWAソースとして、共有ポータルのQR仕切り札画面へ同期した。
- 日付別 `pack.js` は変更せず、既存パックのハッシュとPWA資産のハッシュを `release-manifest.json` に記録した。
- Service Workerのキャッシュ名を既存パックに対応させ、古いPWAが新しい日付パックを解釈しないようにした。
- 旧形式の日付パックにも、運搬・指定場所運搬の `2t車` / `軽四輪` 選択肢を表示専用の互換更新として追加した。QRの案件情報・予定数量・撮影データは変更していない。

## 確認結果

- Node.js構文確認: `portal/photo-ledger/app.js` 成功。
- リリース契約確認: pack hash、Service Worker hash、車種選択UIを確認。
- 全50件の既存運搬カードについて、車種選択肢の付与を確認した。
- 実画面で「指定場所運搬 → 軽四輪」のQR表示を確認した。
- 実画面で作業日を 2026/08/05 から 2026/08/06 へ切り替え、案件一覧と予定本数が切り替わることを確認した。

## 実施しなかった作業

- GitHub Pagesへのpush、mainへのマージ、公開反映は行っていない。
- 日付別の案件データ・写真・Supabaseデータは変更していない。

## 次に人が確認すること

- Pixel 8aで共有ポータルのハンバーガーメニューからQR仕切り札を開き、オフライン起動と車種選択を確認する。

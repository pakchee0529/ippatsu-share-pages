# 作業ログ: 写真台帳COUNT・PICK版のポータル差し替え

| 項目 | 値 |
|---|---|
| 日時 | 2026-07-29 13:25 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | `agent/photo-ledger-count-pick-refresh` |

## 変更ファイル

- `portal/photo-ledger/index.html`
- `portal/photo-ledger/app.js`
- `portal/photo-ledger/styles.css`
- `portal/photo-ledger/pack.js`
- `portal/photo-ledger/service-worker.js`
- `portal/photo-ledger/qrcode.js`
- `portal/photo-ledger/qrcode_UTF8.js`
- `scripts/verify_photo_ledger_portal.py`
- `docs/work_logs/2026-07-29_1325_codex_photo-ledger-count-pick-refresh.md`

## 実施内容

- 共有ポータルの既存`QR仕切り札（PoC）`リンク先を、
  COUNT・PICK対応のPixel用オフラインQR札へ差し替えた。
- 枝切り・根切りを各6径級の折りたたみメニューへ変更した。
- 撮影ごとに一意な開始QR、E10・N10のCOUNT終了QR、
  全景・柴・竹のPICK終了QRを端末内で生成可能にした。
- MITライセンスのQR生成ライブラリをローカルassetとして同梱し、
  Service Workerのオフラインcacheへ追加した。
- ポータル検証を22分類、COUNT/PICK、動的IP2、折りたたみ表示へ更新した。

## 守った制約

- `scripts/generate_portal.py`は変更していない。
- `portal/photo-ledger/`以外の生成ページは変更していない。
- Supabase、業務data、原本写真、現行Excelは変更していない。
- secret、ローカル絶対パスを公開assetへ追加していない。

## 確認

- ポータル専用検証
- Python構文検査
- JavaScript構文検査
- 元PoC生成物とのファイルhash一致
- 公開URLと主要assetのHTTP確認

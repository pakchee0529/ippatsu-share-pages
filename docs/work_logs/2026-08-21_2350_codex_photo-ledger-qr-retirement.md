# 作業ログ: 写真台帳QR仕切り札のポータル休止

| 項目 | 値 |
|---|---|
| 日時 | 2026-08-21 23:50 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | codex/retire-photo-ledger-qr |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/verify_photo_ledger_portal.py`
- `portal/index.html`

## 実施内容

- ポータルTOP、各サブページ、案件詳細のメニュー生成から案件用・汎用QR仕切り札リンクを除外した。
- QR PWA資産は削除せず、ポータル導線に出ない休止資産として保持した。
- 検証を、QR札の内容確認から「メニューに露出せず資産が保持されること」の確認へ変更した。

## 検証

- `python scripts/generate_portal.py --mode portal-top-only`
- `python scripts/verify_photo_ledger_portal.py`
- `python -m py_compile scripts/generate_portal.py scripts/verify_photo_ledger_portal.py`

## 守った制約

- `portal/index.html` は生成スクリプトで再生成した。直接編集していない。
- 実案件、共有日別ページ、アーカイブ、QR PWA資産は削除していない。

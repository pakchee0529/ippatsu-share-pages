# 作業ログ: 共有ポータルへ写真台帳QR仕切り札を追加

| 項目 | 値 |
|---|---|
| 日時 | 2026-07-24 17:11 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | `cursor/photo-ledger-portal-menu` |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/verify_photo_ledger_portal.py`
- `portal/index.html`
- `portal/photo-ledger/index.html`
- `portal/photo-ledger/app.js`
- `portal/photo-ledger/styles.css`
- `portal/photo-ledger/pack.js`
- `portal/photo-ledger/service-worker.js`
- `portal/photo-ledger/manifest.webmanifest`
- `portal/photo-ledger/icon-192.png`
- `portal/photo-ledger/icon-512.png`
- `docs/work_logs/2026-07-24_1711_codex_photo-ledger-portal-menu.md`

## 実施内容

- 共有ポータル配下へ写真台帳QR仕切り札PoCのPWAを追加した。
- ポータルTOPのハンバーガーメニューへ
  `QR仕切り札（PoC）`リンクを追加した。
- 下位ポータルページを今後再生成したときもリンクが入るよう、
  共通メニュー生成処理へ同じ項目を追加した。
- `portal-top-only`で`portal/index.html`だけを再生成した。
- PWAの必要asset、QR札13種、外部通信なし、絶対ローカルpathなしを
  確認する検証スクリプトを追加した。

## 守った制約

- Supabase write、業務data変更、写真原本変更を行っていない。
- `full` generateを実行していない。
- `portal/index.html`以外の既存生成ページを再生成していない。
- secretを新規HTMLへ埋め込んでいない。
- main merge、push、GitHub Pages publishを行っていない。

## 次に必要な作業

- ローカル差分とPixel 8a表示を人間確認する。
- 人間Go後にbranch push、main反映、GitHub Pages公開を行う。

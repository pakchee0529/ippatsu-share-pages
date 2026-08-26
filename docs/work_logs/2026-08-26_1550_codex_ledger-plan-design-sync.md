# 作業ログ: 台帳用予定修正の設計番号同期

| 項目 | 値 |
|---|---|
| 日時 | 2026-08-26 15:50 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | cursor/photo-ledger-transport-special-input |

## 変更ファイル

- `portal/ledger-input/index.html`
- `portal/ledger-input/app.js`

## 実施内容

- 「台帳用の予定を修正」で直接開く画面に設計番号欄を追加した。
- 画面上部の設計番号欄と修正画面内の欄を双方向同期し、端末下書きと生成JSONの `case.design_no` に同じ値を保存する。

## 守った制約

- Supabase、共有ページの業務値、写真原本には書き込まない。
- 設計番号は台帳用JSONと端末下書きだけに反映する。

## 確認

- JavaScript構文確認と、修正画面から設計番号を入力して下書き再読込後もJSON用の値が保持されることをブラウザで確認する。

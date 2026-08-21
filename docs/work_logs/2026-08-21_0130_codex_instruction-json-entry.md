# 作業ログ: 共有ページの写真台帳入力導線

| 項目 | 値 |
|---|---|
| 日時 | 2026-08-21 01:30 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | cursor/instruction-json-ledger |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/ledger-input/index.html`
- `share/<date>/index.html`（再生成済み6日分）

## 実施内容

- 個別共有カードの目立たない位置に「台帳入力」リンクを注入する生成処理を追加した。
- 管理番号、径間名、作業日、枝切り・根切り等の予定本数をクエリで引き継ぎ、スマホで指示書JSONを保存できる静的入力画面を追加した。

## 守った制約

- 静的ページからSupabaseへ直接書き込まない。
- secret、写真原本、公開済みmainは変更しない。
- QR仕切り札への導線は復活させない。

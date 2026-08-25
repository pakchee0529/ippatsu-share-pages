# 作業ログ: 写真台帳JSONの予定・実績修正復旧

| 項目 | 値 |
|---|---|
| 日時 | 2026-08-26 10:45 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | cursor/photo-ledger-transport-special-input |

## 変更ファイル

- `portal/ledger-input/index.html`
- `portal/ledger-input/app.js`
- `scripts/generate_portal.py`
- `share/260826/index.html`

## 実施内容

- 台帳入力に、完了報告と同じ6径級の枝切り・根切りと、柴・竹・つるの最終値を直す「予定・実績を修正」を追加した。
- 元の指示書値、台帳用最終値、差分をJSONへ併記する。DB、共有ページの業務値、写真原本は更新しない。
- 区分変更で新たに予定本数が出た項目は、台帳入力対象として自動的に表示する。
- 共有ページの台帳入力直下にあった「詳細を修正」を、台帳JSON専用の「台帳用の予定を修正」へ差し替えた。

## 守った制約

- Supabase、実データ、写真原本、印刷処理は変更していない。
- 予定修正はJSONと端末下書きだけに保存し、元の予定値を保持する。
- 対象日 `share/260826` だけを再生成相当で更新し、他の共有ページは変更していない。

## 確認

- `node --check portal/ledger-input/app.js`
- `python -m py_compile scripts/generate_portal.py`
- 実ブラウザで予定修正、区分変更後の入力欄自動表示、下書き再読込、JSON保存成功表示、コンソールエラーなしを確認。
- ローカル共有ページで、台帳入力3件、台帳用の予定を修正3件、旧詳細を修正0件を確認。

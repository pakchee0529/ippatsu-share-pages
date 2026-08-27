# 作業ログ: 写真台帳入力のBA流用導線

| 項目 | 値 |
|------|----|
| 日時 | 2026-08-27 17:25 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | cursor/photo-ledger-portal-drafts |

## 変更ファイル

- `portal/ledger-input/app.js`

## 実施内容

- つる伐採前後と柴伐採前後に、伐採前後（BA）の採用組を流用する入力欄を追加した。
- 指定したBA組の前後写真を区分へ複製してJSONへ保存するため、PC側の流用検査と同じ写真組になる。

## 守った制約

- 静的画面のソースだけを変更し、生成済み共有ページ、Supabase、業務データ、原本写真は変更していない。
- GitHub Pagesへの公開は実行していない。

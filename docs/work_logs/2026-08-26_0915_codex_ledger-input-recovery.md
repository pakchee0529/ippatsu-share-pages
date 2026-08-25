# 作業ログ: 写真台帳入力の公開復旧と下書き保護

| 項目 | 値 |
|------|----|
| 日時 | 2026-08-26 09:15 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | cursor/photo-ledger-transport-special-input |

## 変更ファイル

- `portal/ledger-input/index.html`
- `portal/ledger-input/app.js`

## 実施内容

- 構文エラーで初期化不能だった埋込みJavaScriptを、検証可能な外部 `app.js` に分離して復旧した。
- E10/N10 の予定分・追加分判定関数の括弧不足を修正した。
- 下書きを入力途中の値を含む形式で保存するよう変更し、主下書きと予備2世代を保持するようにした。
- 旧形式の下書きも読み込み対象に残した。
- 復元エラー時の自動削除を廃止し、明示的な削除操作だけが下書きを消すようにした。
- JS読込失敗時は、入力内容を消さない案内を表示する。

## 守った制約

- Supabase、写真原本、共有ページ生成器、実データ、印刷処理は変更していない。
- ブラウザからの削除は明示確認を要求する。

## 確認

- `node --check portal/ledger-input/app.js`
- `git diff --check`
- ローカルHTTP上の実ブラウザで、初期表示、BA/E10入力、自動保存、再読込復元、JSON保存成功表示、コンソールエラーなしを確認。

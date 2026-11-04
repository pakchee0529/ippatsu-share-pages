# 作業ログ: OJTアンケート入口を一時非表示

- 日時: 2026-11-05 07:25 JST
- repo: ippatsu-share-pages
- branch: cursor/hide-portal-surveys-20261105
- 本人依頼・公開承認により、OJTアンケートのTOP入口のみ一時非表示。
- scripts/generate_portal.py にOJT入口専用の表示フラグを追加。フォームURLと定義は維持。
- scripts/test_portal_top_entries_removed.py でOJT入口非表示、意見・改善案維持を検証。
- compileall、回帰検査、空日除外、日付見出し、diff --check成功。
- 意見・改善案、フォーム本体・回答、定期処理、業務データ、認証設定は変更しない。
- 生成物は別コミット。

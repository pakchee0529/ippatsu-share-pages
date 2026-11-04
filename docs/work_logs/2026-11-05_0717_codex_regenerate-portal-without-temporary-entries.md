# 作業ログ: TOP表示を限定再生成

- 日時: 2026-11-05 07:17 JST
- repo: ippatsu-share-pages
- branch: cursor/remove-portal-pdf-print-test-20261105
- 変更ファイル: portal/index.html
- scripts/generate_portal.py --mode portal-top-only --portal-min-date 261104 で再生成。
- 検証結果: validation OK、3日分カード維持、公開API設定維持、差分13行削除のみ。
- PDFカード・印刷テストカード・印刷テストメニューリンクを除去。他の表示・動作は変更なし。
- 元PDFやテストページ自体は削除せず、復元可能な最小表示変更とする。
- 依頼された既存ポータル更新としてmain反映・公開確認を行う。

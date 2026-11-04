# 作業ログ: TOPの週間PDF・印刷テスト導線を削除

- 日時: 2026-11-05 07:17 JST
- repo: ippatsu-share-pages
- branch: cursor/remove-portal-pdf-print-test-20261105
- 依頼: 共有ポータルTOPに再表示されたPDFと印刷テストの除去。

## 変更
- scripts/generate_portal.py: TOPの週間PDFカード、印刷テストカード、メニューの印刷テストリンクのみ削除。
- scripts/test_portal_top_entries_removed.py: 再生成後の非表示と通常導線維持を回帰検査。
- 生成物は別コミットで portal-top-only により更新。手編集なし。

## 検証・制約
- cleanなmain e6d9921から専用ブランチを作成。
- compileall、既存の空日除外・日付見出し検査、新規回帰検査、diff --checkが成功。
- portal-top-only --portal-min-date 261104 は検証成功。3日分カードを維持。
- 生成差分は対象3導線の13行削除のみ。
- 元PDF・テスト資産・通常共有日・本日の予定・フォーム・DB・認証設定は変更しない。
- full生成、本番DB通信・書込み、本番業務データ検証は実施しない。

# 作業ログ: 社員アンケート先頭配置のTOP限定生成

- 日時: 2026-10-22 19:14 JST
- 担当: Codex
- repo: ippatsu-share-pages
- branch: cursor/ojt-answer-entry-20261022
- 基点: 2b374f6541bcb2070bdfcf0c96151a86c50daab2

変更: portal/index.html、本ログ。生成スクリプトは直前の別コミット。

既存run_portal_top_onlyで再生成。生成物を手編集していない。
アンケート入口のHTML/CSS以外は前回公開TOPとバイト一致し、予定・日付カードの順序も維持。
他のportal/share追跡ファイルは不変。Form回答先も変更なし。原文/Sheet/編集リンクを公開しない。

4幅のスマホ/デスクトップ表示、48px以上の回答ボタン、メニュー、フォーカス、入口1件を確認。
公開後のcommit/Pagesビルド/HTTP/実表示の証拠はタスク側のportal-entry-topへ保存する。
mainが基点から動いていないことを確認して通常fast-forwardで公開し、forceや新認証は使わない。

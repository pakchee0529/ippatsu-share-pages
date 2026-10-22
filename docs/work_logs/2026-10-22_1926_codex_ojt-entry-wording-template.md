# 作業ログ: 社員アンケート入口の補足文言削除

- 日時: 2026-10-22 19:26 JST
- 担当: Codex
- repo: ippatsu-share-pages
- branch: cursor/ojt-answer-entry-20261022（既存の隔離clone）
- 基点: 03f2f7f03f0aa7372246ef769f1cb9afd0518fab（最新mainと同期済み）

変更: scripts/generate_portal.py、本ログ。

ユーザー指定で入口の「経験なしでも構いません。」だけを削除。
「OJTアンケート（任意）」「1問・30〜60秒。」と確認済み回答URLは維持。
CSS、配置、予定、その他の文面は変更なし。Form/Sheetには触れていない。

限定TOP生成の差分が指定文字列1か所の削除だけであることをバイト比較で確認。
compileall、diff --check、4幅の架空ブラウザ表示・メニュー・リンク検証成功。
元の業務checkoutと他writerの差分は変更なし。生成物は別コミットに分離する。
公開は親の明示指示に基づき、main競合がなければ通常fast-forwardで行う。

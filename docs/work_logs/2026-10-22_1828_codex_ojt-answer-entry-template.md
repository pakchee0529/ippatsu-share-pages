# 作業ログ: OJT任意回答入口の生成テンプレート

- 日時: 2026-10-22 18:28 JST
- 担当: Codex
- repo: ippatsu-share-pages
- branch: cursor/ojt-answer-entry-20261022（専用の隔離clone）
- 基点: 4298dca27b75d60d2f09001e7c971d9eeb64b1cc

変更ファイル: scripts/generate_portal.py、本ログ。

日付別業務カードの後ろへOJTの任意回答リンクを1件追加する生成処理を用意した。
公開するのは承認済みGoogle Formsの回答URLだけで、原文、Sheet、編集リンクは含めない。
30〜60秒の1問であることと任意回答を表示し、ランキング・催促・評価や自律分析の完成表示はない。

検証: 限定portal-top-only生成のsmoke成功。OJT追加HTML/CSSを除くと既存TOPのGit blobと
バイト一致。他のportal/share追跡ファイルに差分なし。scriptsのcompileallとdiff --check成功。
架空データのオフラインChromiumで320/375/414/1280px、横はみ出しなし、48px以上のリンク、
既存メニュー/キーボード操作、業務カードが先であることを確認。外部送信0。

元の業務checkoutと登録済み他worktreeへ書込みなし。予定・台帳・写真・数量・160〜161変更なし。
生成物は別コミットに分離する。本コミット単体で公開先へ送信していない。
ユーザーの継続収集切替・回答入口公開の明示承認は親タスクから受領済み。
公開時はGitHub mainの競合を再確認し、非fast-forward更新やforceをしない。

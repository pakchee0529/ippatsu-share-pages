# 作業ログ: 週間閲覧ページの TOP 導線を独立修正

| 項目 | 値 |
|---|---|
| 日時 | 2026-11-13 21:50 JST |
| 担当 | ChatGPT / Codex |
| repo | ippatsu-share-pages |
| branch | cursor/weekly-261116-top-entry-public-fix |

## 変更ファイル
- `scripts/generate_portal.py`
- `scripts/weekly_readonly_guard.py`

## 実施内容
公開 main `27d90ef9d6541be58c3410376c9e55e8a5c02956` と公開済み日次ページのみから作成した独立候補。会社側の私有候補を取得・採用したものではない。通常生成器は対象5日を元から検出できるが、TOP が空のまま配信されていた。公開済みの閲覧限定 manifest 対象日に共有入口・離隔表・指示書の3リンクを追加し、正式 TOP 生成の入力一致と導線検査を追加した。

## 守った制約・検査
既存17公開物、TOPカード外のカレンダー・メニュー等は byte 不変。正式 `python scripts/generate_portal.py --mode portal-top-only` の繰返し生成一致。15種類のリンク欠落、17入力/資産改変と欠損は拒否。通常日・日付範囲・明示除外を維持。保護日の存在しない通常入力 root に5日の配置を要求しないよう限定。空予定と旧入口の既存回帰、completion-archive スコープ9件も成功。業務DB、認証設定、原票、会社GUIは変更していない。

正式 share-update の対象5日も隔離コピーで各 exit 0、TOP以外不変。通常日だけの root、完了除外・archive・retired のモデル回帰も成功。会社側 caller の未確認な `portal()` は変更していない。

## 残件
実ブラウザは検査環境の起動時 socket 作成拒否により未実施。権限変更や別経路の再試行は行わず、公開せず候補保存で停止。公開配信検証は未実施。会社GUIの更新・受入は未実施。この候補の公開反映だけで会社経路の検証完了とは扱わない。

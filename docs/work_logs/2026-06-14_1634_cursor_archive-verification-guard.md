# 作業ログ: アーカイブ検証ガード

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 16:34 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/verify_archive_pages.py`
- `docs/portal_operation_notes.md`
- `docs/next_cursor_tasks.md`
- `portal/archive/260610/index.html`
- `portal/archive/260612/index.html`
- `docs/work_logs/2026-06-14_1634_cursor_archive-verification-guard.md`

## 実施内容

- アーカイブ公開前に使う read-only 検証 CLI を追加。
- `portal/archive/index.html` の TOP 件名が空欄・`—` になっていないことを検査。
- manifest とアーカイブ詳細ページの対応、detail カード数、`planned_but_incomplete` 枠、座標がある場合の全体地図・points 数を検査。
- 検証で 260610 / 260612 の詳細ページ全体地図に `planned_but_incomplete` 分の points が不足していることを検出したため、対象 2 日分だけ `completion-archive` で再生成。
- 運用メモに、completion archive 生成後の検証コマンドを追記。
- `docs/next_cursor_tasks.md` の完了報告後 archive 反映手順にも検証段を追加。

## 守った制約

- Supabase write なし。
- `data/`・`output/`・`.env` 変更なし。
- 生成済み公開 HTML は変更しない。
- `git add .` は使用しない。

## 次に必要な作業

- 次回以降の archive 反映時は `scripts/verify_archive_pages.py --date YYMMDD --completion-reports-root <export root>` を公開前確認に含める。

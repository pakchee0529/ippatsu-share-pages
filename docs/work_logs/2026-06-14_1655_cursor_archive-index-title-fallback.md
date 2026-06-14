# 作業ログ: アーカイブTOP件名補完

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 16:55 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/archive/index.html`
- `docs/portal_operation_notes.md`
- `docs/work_logs/2026-06-14_1655_cursor_archive-index-title-fallback.md`

## 実施内容

- アーカイブTOPの件名が `—` になる原因を調査。
- TOP生成時の件名候補を、完了 `items` だけでなく `planned_but_incomplete` と既存アーカイブ詳細HTMLのカードタイトルからも補完するよう修正。
- 補完元が本当に存在しない場合は `—` ではなく `現場名未取得` と表示するようにした。
- 260604 など未完了のみの日、古いアーカイブ詳細だけ残っている日付でもTOPに件名が出ることを確認。
- `docs/portal_operation_notes.md` に、アーカイブTOP件名の生成優先順を追記。

## 守った制約

- `.env` / secret / token は表示していない。
- Supabase 書き込み、deploy、publish は実施していない。
- `data/` は変更していない。

## 次に必要な作業

- 人間確認後、必要なら commit / push / publish を判断する。

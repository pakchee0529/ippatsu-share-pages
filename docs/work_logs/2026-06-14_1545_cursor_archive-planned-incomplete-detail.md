# 作業ログ: archive未完了カードの現場情報表示

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 15:45 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `docs/work_logs/2026-06-14_1545_cursor_archive-planned-incomplete-detail.md`

## 実施内容

- 完了報告 archive の `planned_but_incomplete` カードに、現場名・管理番号だけでなく、地図、現場指示ボタン、処理、B車、道幅、傾斜、枝切り/根切り合計、警告を表示できるようにした。
- `planned_but_incomplete[].source_item` に入っている現場共有情報を使い、完了カードと近い情報量を未完了カードにも出す。

## 守った制約

- Supabase write は実施していない。
- publish / push は実施していない。
- secret / token は表示していない。

## 次に必要な作業

- 260604 archive を再生成し、未完了カードに現場情報が表示されることを確認する。
- 人間 Go 後、ippatsu-pc 側の修正と合わせて commit / push する。

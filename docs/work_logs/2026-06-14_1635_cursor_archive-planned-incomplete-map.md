# 作業ログ: 未完了のみアーカイブの全体地図対応

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 16:35 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/archive/260604/index.html`
- `docs/work_logs/2026-06-14_1635_cursor_archive-planned-incomplete-map.md`

## 実施内容

- アーカイブ詳細ページの全体地図が完了済み `items` だけを点データにしていたため、`planned_but_incomplete` の座標も同じ形式で `points` に追加するよう修正。
- 未完了カードにも通常カードと同じ `start_lat/start_lng/end_lat/end_lng` を保持させ、可能な場合は `2点地図を開く` を表示するよう統一。
- 260604 のような全件未完了の日でも、下部の全体地図が表示される構成にした。

## 守った制約

- `.env` / secret / token は表示していない。
- Supabase 書き込み、deploy、publish は実施していない。
- `data/` は変更していない。

## 次に必要な作業

- 人間確認後、必要なら commit / push / publish を判断する。

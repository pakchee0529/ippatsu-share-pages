# ポータルTOP「本日の予定」モック（2026-05-27）

## 目的

共有ポータルTOPの大きな「社内カレンダー」カードをやめ、上部に本日分の簡易予定表示を置く（モック）。

## 変更

- `portal/index.html`
  - カード一覧先頭の「社内カレンダー（会社行事・健診・休み）」カードを削除
  - `today-schedule` セクションを追加（`todayScheduleMock` + `renderTodaySchedule()`）
  - ハンバーガーメニューの `./calendar/` リンクは維持
  - セクション下部に「社内カレンダーで詳細を見る」リンク

## 差し替え方針（将来）

1. `todayScheduleMock` を API 取得結果に置き換え
2. `renderTodaySchedule(rows)` はそのまま利用可能（`type` / `title` / `person`）
3. 空配列で `本日の予定はありません` を表示

## 配色

社内カレンダー（`portal/calendar/index.html`）のカテゴリ色に準拠。

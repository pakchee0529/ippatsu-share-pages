# 作業ログ: portal TOP 本日の予定を generate_portal に組み込み

| 項目 | 値 |
|------|----|
| 日時 | 2026-05-29 07:24 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/index.html`

## 実施内容

- `build_html()` に today-schedule CSS/HTML/JS を正式組み込み
- 社内カレンダー導線（`./calendar/`）をメニュー・本日の予定セクションに追加
- `portal_calendar_api_key()` で env または `portal/calendar/index.html` から anon key を解決
- `pageshow` / `visibilitychange` で `loadTodaySchedule()` 再実行
- `share-update --date 260601` 実行後も today-schedule が残ることを確認

## 守った制約

- Supabase DDL / Edge Function deploy なし
- calendar / survey / negotiation の仕様変更なし
- secrets のログ出力なし
- `git add .` 未使用
- share-update テストで触った `share/260601/index.html` は restore 済み（コミット対象外）

## 次に必要な作業

- GitHub Pages 公開後、本番 URL で「本日の予定」表示を人間確認

# 作業ログ: 付託待ち・案件管理ポータル追加

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 18:34 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/entrustment/index.html`
- `portal/cases/index.html`
- `portal/index.html`
- `portal/survey/index.html`
- `portal/negotiation/index.html`
- `portal/archive/index.html`
- `portal/calendar/index.html`
- `docs/work_logs/2026-06-14_1834_cursor_portal-entrustment-cases-pages.md`

## 実施内容

- 閲覧専用の `portal/entrustment/` を追加した。
- 閲覧専用の `portal/cases/` を追加した。
- ハンバーガーメニューに `付託待ち` と `案件管理` を追加し、TOP、現調待ち、交渉待ち、アーカイブ一覧、社内カレンダー、新規2ページから遷移できるようにした。
- `generate_portal.py` に `--mode entrustment-only` と `--mode cases-only` を追加した。
- `negotiation-only` の検証から古い固定件数ガードを外し、導入期の実データ件数変動に追従できるようにした。

## 守った制約

- 閲覧専用ページのみを追加し、公開ページからのDB write操作は追加していない。
- 地主名、住所、電話、承諾内容などの個人情報は表示していない。
- Supabaseはreadのみ。
- publish、deploy、pushは行っていない。
- `git add .` は使用しない。

## 次に必要な作業

- 人間確認後、明示Goがあれば対象ファイルを個別stageしてcommit/pushする。

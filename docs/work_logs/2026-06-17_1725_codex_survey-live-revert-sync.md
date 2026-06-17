# 作業ログ: 現調待ちページの共通ライブ描画同期

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-17 17:25 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `portal/survey/index.html`
- `portal/survey/gojo/index.html`
- `portal/survey/totsukawa/index.html`
- `portal/survey/yoshino/index.html`
- `docs/work_logs/2026-06-17_1725_codex_survey-live-revert-sync.md`

## 実施内容

- 現調待ちページに含まれる共通 live cases JS の `negotiationCard()` を、交渉待ちページ側と同じ挙動に同期した。
- Supabase live cases 取得後に交渉待ち・返却待ちカードを描画する場合でも、`現調待ちに戻す` ボタンが残るようにした。
- `revert_to_survey_wait` の確認メッセージを現調待ちページ側の共通 live action handler にも追加した。

## 守った制約

- Supabase への書き込み、Edge Function deploy、`.env` 変更、secret 表示は行っていない。
- 生成物は `scripts/generate_portal.py --mode survey-only` から再生成した。

## 確認

- `python -m py_compile scripts\generate_portal.py scripts\portal_immediate_status_client.py`
- `python scripts\generate_portal.py --mode survey-only`
- `python scripts\generate_portal.py --mode negotiation-only`
- 公開ページで現調待ち検索、管轄別ページ、交渉待ちカードのボタン残存をブラウザ確認した。

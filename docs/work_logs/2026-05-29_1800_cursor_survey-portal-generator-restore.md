# 作業ログ: 現調ポータル UX・ハンバーガーメニュー生成元復旧

| 項目 | 値 |
|------|----|
| 日時 | 2026-05-29 18:00 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | （作業時ブランチのまま） |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`
- `portal/survey/index.html`（再生成）
- `portal/archive/index.html`（再生成）

## 実施内容

- `build_survey_html`: 即時モードで `survey-case-action-row`（現調済みにする / 返却候補にする）、`survey-overlay-warning`、ハンバーガーヘッダー共通関数を復旧
- `render_survey_immediate_status_js`: `fetchReturnCandidates`・3引数 `applySurveyOverlay`・サーバー POST `mark_return_candidate` を 28bd482 相当で正本化
- `build_archive_html`: ハンバーガーメニュー（TOP / カレンダー / 現調 / 交渉 / アーカイブ）を生成元に追加
- `survey_status_request_api_key`: `.env` 未設定時は既存 `portal/negotiation` 等の anon 埋め込みからフォールバック（service_role は拒否）
- 本番 data（`ippatsu-pc-prod/data`）で survey / archive index のみ再生成。7件キー維持を確認

## 守った制約

- `portal/survey`・`portal/archive` の手修正のみでの対応は行わず、生成元修正後に再生成
- `portal/index.html`・`data/share`・prod queue・Supabase は未変更
- `git add .` / commit / push / publish 未実施
- API key 実値はログ・報告に出さず bool のみ

## 次に必要な作業

- 人間: diff 確認 → 明示 `git add` → commit → push → publish 承認
- 再生成時は `load_dotenv(ippatsu-pc/.env)` と `survey_status_request_api_key(repo)` を使うこと

# 作業ログ: 案件管理詳細ページと安全操作UI

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-15 15:26 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`
- `portal/cases/index.html`
- `portal/cases/case-*/index.html`
- `docs/work_logs/2026-06-15_1526_cursor_cases-detail-actions.md`

## 実施内容

- 案件管理一覧から案件詳細ページへ移動できるリンクを追加した。
- `portal/cases/<safe-key>/index.html` 形式の案件詳細ページを生成するようにした。
- 詳細ページのPOST payloadに `id` / `internal_management_no` / `span_key` / `management_no_key` を含めるようにした。
- 詳細ページで許可済み操作だけを表示するようにした。
  - `negotiation_wait` は `mark_entrustment_wait`
  - `return_wait` は理由必須で `mark_returned`
  - その他の状態はPC側変更の案内のみ
- `cases-only` ガードが案件詳細ページ生成を許容するように調整した。

## 守った制約

- `portal/cases/index.html` と詳細ページは生成物として `scripts/generate_portal.py` から再生成した。
- Supabase write、Edge Function deploy、公開処理、commit/push は実施していない。
- service_role key や `.env` の秘密値は表示していない。
- 個人情報や交渉内容の詳細は詳細ページに追加していない。

## 確認

- `python -m py_compile scripts\generate_portal.py scripts\portal_immediate_status_client.py`
- `python scripts\generate_portal.py --mode cases-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data`
- 生成バリデーション: `validation: OK`
- `portal/cases` 配下に詳細ページ 77 件を生成した。
- `portal/cases` 配下に `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_ACCESS_TOKEN` / `service_role` / `PORTAL_SURVEY_REQUEST_API_KEY` の文字列が含まれないことを確認した。

## 次に必要な作業

- 人間確認後、必要な対象ファイルだけを明示して stage / commit / push する。

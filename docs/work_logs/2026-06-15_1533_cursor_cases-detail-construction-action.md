# 作業ログ: 案件詳細の工事待ち遷移ボタン

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-15 15:33 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`
- `portal/cases/index.html`
- `portal/cases/case-*/index.html`
- `docs/work_logs/2026-06-15_1533_cursor_cases-detail-construction-action.md`

## 実施内容

- 案件詳細ページで `entrustment_wait` の場合に「工事待ちにする」ボタンを表示するようにした。
- ボタンは `mark_construction_wait` を送信する。
- 送信前に、CS記入・添付書類・元請けへの付託提出が済んでいる前提の確認ダイアログを表示する。

## 守った制約

- 生成物は `scripts/generate_portal.py --mode cases-only` から再生成する。
- Supabase write、Edge Function deploy、公開処理、commit/push は実施しない。
- 公開HTMLに service_role や秘密値を埋め込まない。

## 次に必要な作業

- `ippatsu-pc-prod` 側の Edge Function / RPC 変更を人間確認後にdeployする。
- 本番反映後、付託待ち案件1件で送信スモークとread-back確認を行う。

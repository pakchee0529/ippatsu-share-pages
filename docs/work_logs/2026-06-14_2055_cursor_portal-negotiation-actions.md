# 作業ログ: portal negotiation actions

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 20:55 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`
- `portal/negotiation/index.html`

## 実施内容

- 交渉待ちカードへ `付託待ちにする` ボタンを追加した。
- 返却待ちカードへ `返却済みにする` ボタンを追加した。
- 返却済み操作では `接触弱` / `地主要望` / `伐採不可` の理由選択を求めるようにした。
- ボタンは `submit-survey-status-request` の新アクション `mark_entrustment_wait` / `mark_returned` にPOSTする。
- 業務用 `C:\Users\kotan\Projects\ippatsu-pc-prod\data` を明示して `portal/negotiation/index.html` を再生成した。

## 守った制約

- service_role key や `.env` の秘密値は表示していない。
- Supabase write / Edge Function deploy / GitHub Pages publish は実施していない。
- 既存の現調待ちへ戻す導線は残した。

## 確認

- `python -m py_compile scripts\generate_portal.py scripts\portal_immediate_status_client.py`
- `python scripts\generate_portal.py --mode negotiation-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data`
- 生成バリデーション: `validation: OK`
- `portal/negotiation/index.html` に `data-negotiation-entrustment` / `data-returned-mark` / `mark_entrustment_wait` / `mark_returned` が含まれることを確認した。
- Edge Function 未deploy時は `request_id` / `requested_action` 系の旧Functionエラーを「Edge Function更新待ち」と表示する保険を追加した。

## 次に必要な作業

- Edge Function deploy 後にスマホから実送信を確認する。

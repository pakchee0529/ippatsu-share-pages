# 作業ログ: 交渉待ちライブカードの戻すボタン維持

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-17 17:02 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/negotiation/index.html`
- `portal/negotiation/gojo/index.html`
- `portal/negotiation/totsukawa/index.html`
- `portal/negotiation/yoshino/index.html`
- `docs/work_logs/2026-06-17_1702_codex_negotiation-live-revert-button.md`

## 実施内容

- Supabase live cases 取得後に描画される交渉待ちカードへ `現調待ちに戻す` ボタンを追加した。
- ライブカードの戻すボタンは `revert_to_survey_wait` を送信する。
- 交渉待ち・返却待ちのライブカードどちらでも戻すボタンが残るようにした。
- 交渉待ち全体ページと管轄別3ページを再生成した。

## 守った制約

- 生成物は `scripts/generate_portal.py` から再生成し、手編集していない。
- Supabase への書き込み、Edge Function deploy、`.env` 変更は行っていない。
- secret / token / service_role の実値は表示していない。

## 実行した確認

- `python -m py_compile scripts/generate_portal.py`
- `python scripts/generate_portal.py --mode negotiation-only`
- 生成HTMLに `data-live-action="revert_to_survey_wait"` が含まれることを確認

## 次に必要な作業

- Edge Function の live cases 返却に `jurisdiction` を追加すると、管轄別ページのライブ更新も警告なしで完全反映できる。

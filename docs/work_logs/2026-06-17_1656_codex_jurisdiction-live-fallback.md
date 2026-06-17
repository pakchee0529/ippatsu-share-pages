# 作業ログ: 管轄別ページのライブ取得フォールバック修正

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-17 16:56 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/survey/index.html`
- `portal/survey/gojo/index.html`
- `portal/survey/totsukawa/index.html`
- `portal/survey/yoshino/index.html`
- `portal/negotiation/index.html`
- `portal/negotiation/gojo/index.html`
- `portal/negotiation/totsukawa/index.html`
- `portal/negotiation/yoshino/index.html`
- `docs/work_logs/2026-06-17_1656_codex_jurisdiction-live-fallback.md`

## 実施内容

- 管轄別ページで、Supabase live cases の返却行に `jurisdiction` が含まれない場合は、ライブ結果で静的表示を上書きしないようにした。
- 上記の場合は「生成時点の管轄別表示を使っています」というステータス表示にして、カードが一瞬表示後に消える現象を防ぐようにした。
- 現調待ち・交渉待ちの全体ページと管轄別ページを再生成した。

## 守った制約

- 生成物は `scripts/generate_portal.py` から再生成し、手編集していない。
- Supabase への書き込み、Edge Function deploy、`.env` 変更は行っていない。
- secret / token / service_role の実値は表示していない。

## 実行した確認

- `python -m py_compile scripts/generate_portal.py`
- `python scripts/generate_portal.py --mode survey-only`
- `python scripts/generate_portal.py --mode negotiation-only`

## 次に必要な作業

- Edge Function 側の live cases 返却に `jurisdiction` を含めると、管轄別ページでも最新取得後の完全なライブ絞り込みが有効になる。

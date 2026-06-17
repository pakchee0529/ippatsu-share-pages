# 作業ログ: 管轄別ステータスページ生成

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-17 16:48 |
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
- `docs/work_logs/2026-06-17_1648_codex_jurisdiction-status-pages.md`

## 実施内容

- 現調待ちページと交渉待ちページに、全体 / 五條 / 十津川 / 吉野の管轄別ナビゲーションを追加した。
- `survey-only` 生成で `portal/survey/index.html` と管轄別3ページを出力するようにした。
- `negotiation-only` 生成で `portal/negotiation/index.html` と管轄別3ページを出力するようにした。
- 静的生成時の Supabase REST 取得と、ブラウザ側 live cases 取得後の表示の両方で `jurisdiction` を反映するようにした。
- 交渉待ちページでは `return_wait` も同じ管轄で絞り込むようにした。
- 古い固定管理番号に依存した検証を、管轄別ページの存在・live filter・他管轄混入チェックへ置き換えた。

## 守った制約

- 生成物は `scripts/generate_portal.py` から再生成し、手編集していない。
- Supabase への書き込み、Edge Function deploy、`.env` 変更、commit、push、GitHub Pages publish は行っていない。
- secret / token / service_role の実値は表示していない。

## 実行した確認

- `python -m py_compile scripts/generate_portal.py`
- `python scripts/generate_portal.py --mode survey-only`
- `python scripts/generate_portal.py --mode negotiation-only`

## 次に必要な作業

- 人間確認後、必要なら明示パスだけを stage して commit / push する。
- 公開反映は人間承認後に行う。

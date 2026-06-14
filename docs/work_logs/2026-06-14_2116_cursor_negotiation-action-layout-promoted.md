# 作業ログ: negotiation action layout and promoted cards

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 21:16 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`
- `portal/negotiation/index.html`

## 実施内容

- 現調待ちから即時昇格した交渉待ちカードにも `付託待ちにする` ボタンを表示するようにした。
- 交渉待ち/返却待ちの操作ボタンを縦積みから横並び優先へ変更した。
- 説明文と送信ステータスはボタン下で全幅表示するようにした。
- 業務用 `C:\Users\kotan\Projects\ippatsu-pc-prod\data` を明示して `portal/negotiation/index.html` を再生成した。

## 守った制約

- Supabase write / Edge Function deploy は実施していない。
- `.env` の秘密値は表示していない。
- `data/` は読み取りのみ。

## 確認

- `python -m py_compile scripts\generate_portal.py scripts\portal_immediate_status_client.py`
- `python scripts\generate_portal.py --mode negotiation-only --data-root C:\Users\kotan\Projects\ippatsu-pc-prod\data`
- 生成バリデーション: `validation: OK`
- 生成HTML内で `data-negotiation-entrustment`、`data-returned-mark`、横並びCSSの存在を確認した。

# 作業ログ: 公開共有ページ日付 260415 → 260615 補正

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 17:31 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `portal/index.html`
- `share/260415/index.html`
- `share/260615/index.html`
- `docs/work_logs/2026-06-14_1731_cursor_fix-share-date-260615-public.md`

## 実施内容

- 誤って公開されていた `share/260415/` を `share/260615/` に移動した。
- 共有詳細ページ内の日付、Googleフォーム連携URL、カード属性を `260615` に更新した。
- `scripts/generate_portal.py --mode share-update --date 260615` で portal TOP と対象共有ページの注入部分を再生成した。
- `260415` が portal TOP と `share/260615/index.html` に残っていないことを確認した。

## 守った制約

- 対象外の日付共有ページ、archive、survey、negotiation は更新していない。
- `git add .` は使用しない。
- force push は使用しない。

## 次に必要な作業

- なし。

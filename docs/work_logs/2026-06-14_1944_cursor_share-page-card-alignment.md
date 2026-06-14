# 作業ログ: 現場共有ページのスマホカード整列

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 19:44 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `share/260615/index.html`
- `docs/work_logs/2026-06-14_1944_cursor_share-page-card-alignment.md`

## 実施内容

- 日別現場共有ページのスマホ表示で、カード内の径間名・管理番号・操作ボタンが行ごとにずれる問題を調整。
- カードヘッダーをグリッド化し、現場共有ラベル、管理番号、径間名、操作ボタンの配置を固定。
- 現場作業員向け導線を優先し、関連ナビは `ポータルTOP` のみに整理。
- `share/260615/index.html` を `share-update` モードで再生成。

## 守った制約

- `data/`、`.env`、`output/` は変更していない。
- Supabase 書き込み、公開操作、deploy は実施していない。
- `git add .` は使用していない。

## 確認

- `python scripts\generate_portal.py --mode share-update --date 260615`
- ローカル表示を 390px 幅で確認し、6カードすべてで操作ボタンが同じ幅・同じ行に揃うことを確認。
- 関連ナビが `ポータルTOP` 1件のみであることを確認。

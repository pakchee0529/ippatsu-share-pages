# 作業ログ: 現場共有ページの不要タグ除去

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 20:02 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `share/260615/index.html`
- `docs/work_logs/2026-06-14_2002_cursor_share-page-remove-status-pill.md`

## 実施内容

- 日別現場共有ページのカードから `現場共有` タグを追加しないようにした。
- 既存HTMLに残る `現場共有` タグは、読みやすさ注入時に除去するようにした。
- タグ除去後もカード内の径間名、管理番号、操作ボタンがスマホ幅で揃うようグリッド配置を調整した。
- `share/260615/index.html` を `share-update` モードで再生成した。

## 守った制約

- `.env`、`data/`、`output/` は変更していない。
- Supabase は read-only 確認のみで、書き込みは行っていない。
- GitHub Pages 以外の公開・deploy は行っていない。

## 確認

- 390px幅のローカル表示で、`現場共有` タグが0件であることを確認。
- 6カードすべてに `2点地図を開く` と `現場指示` ボタンが残っていることを確認。
- 全体地図は `data-point-count=0` のままで、座標復旧には別途データ補完が必要。

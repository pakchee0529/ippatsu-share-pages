# 作業ログ: 共有ページGPS再生成ガード

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 20:24 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `share/260615/index.html`
- `docs/work_logs/2026-06-14_2024_cursor_share-page-gps-regeneration-guard.md`

## 実施内容

- `share-update` 再生成時に、共有ページのカード名と `GPS.json` から現場地図ボタン、2点地図JSON、全体地図ピンを復元する処理を追加。
- GPS参照先は業務用 `ippatsu-pc-prod` を優先し、なければ開発用 `ippatsu-pc` にフォールバックするように変更。
- `津風呂24N6～26N7` のように終点ラベルがGPSに直接存在しないケースでは、始点側の路線プレフィックスを使って `津風呂24N7` を候補にする補完を追加。
- `share/260615/index.html` を `share-update --date 260615` で再生成し、地図ボタンと全体地図ピンを維持。

## 守った制約

- Supabase への書き込みなし。
- `.env`・secret 表示なし。
- `data/`・`output/`・公開デプロイ設定は変更なし。
- `git add .` は使わず、対象ファイルのみを個別に stage する。

## 確認

- `python -m py_compile scripts\generate_portal.py`
- `python scripts\generate_portal.py --mode share-update --date 260615`
- メモリ上で 260615 の地図ボタン、2点座標、POINTS を壊したHTMLに対して復元処理を実行し、6件分の地図情報が復元されることを確認。
- 生成後の `share/260615/index.html` で `data-point-count="6"`、2点地図JSON 6件、0座標なしを確認。

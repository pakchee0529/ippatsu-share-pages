# 作業ログ: share-page bookmark icon

| 項目 | 値 |
|------|----|
| 日時 | 2026-07-29 14:48 |
| 担当 | codex |
| repo | ippatsu-share-pages |
| branch | cursor/photo-ledger-paired-overview-pick |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/assets/share-page-icon.svg`
- `portal/assets/apple-touch-icon.png`
- `portal/assets/icon-192.png`
- `portal/assets/icon-512.png`
- `portal/assets/site.webmanifest`
- `portal/index.html`

## 実装内容

- 共通の bookmark / favicon 用アイコンリンク注入処理を追加。
- トップページ `portal/index.html` のみに bookmark / favicon 用アイコンリンクを注入。
- それ以外の `portal` ページと `share/<date>/index.html` にはアイコンリンクを入れない。
- SVG favicon と 180x180 PNG apple-touch-icon を追加。

## 守った制約

- secret / API key の追加や表示はなし。
- 初期実装時点では GitHub Pages publish、commit、push は未実施。
- `portal/cases/case-*` の大量生成差分は今回対象外として戻し、未追跡生成ディレクトリも削除した。
- 最終方針変更により、`share/<date>/index.html` の変更は戻した。

## 確認

- `python -m py_compile scripts\generate_portal.py`
- focused generate:
  - `portal-top-only`
- `archive-only`
- `survey-only`
- `negotiation-only`
- `entrustment-only`
- `cases-only` は出力上 `validation: OK` まで到達したが、コマンドは30秒制限で timeout 扱い。
- 最終確認では `portal/index.html` のみに `share-page-site-icons` が存在し、`share/260728`, `share/260730`, `share/260731` には存在しない。

## 2026-07-29 addendum: Pixel / Android home-screen icon

- Added `site.webmanifest` plus `192x192` and `512x512` PNG icons for Pixel Chrome's Add to Home screen flow.
- Added `<link rel="manifest" href="assets/site.webmanifest">` to the top-page icon block.
- `site.webmanifest` uses `../index.html` as `start_url` and `../` as `scope` because the manifest file lives under `portal/assets/`.
- Manifest app names use ASCII `Share Portal` to avoid mojibake in Android/browser metadata.
- Verified with `python -m py_compile scripts\generate_portal.py` and `git diff --check`; only LF/CRLF warnings were printed.

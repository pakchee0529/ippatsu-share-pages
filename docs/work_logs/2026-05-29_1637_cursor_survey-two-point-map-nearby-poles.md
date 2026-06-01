# 作業ログ: survey 2点地図修正 + 周辺160m電柱

| 項目 | 値 |
|------|----|
| 日時 | 2026-05-29 16:37 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main（未 commit） |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/survey/index.html`（再生成）
- `scripts/portal_immediate_status_client.py`（UTF-8 BOM 除去）

## 実施内容

- `two-geo` JSON を `escape_html` せず `application/json` として埋め込み（`<` → `\u003c`）
- `GPS.json` から haversine 160m 周辺電柱を `nearby` 配列に付与（始点・終点・中点アンカー、端点±3m 除外、重複排除）
- Leaflet: 端点 marker + polyline + 周辺 circleMarker + 常時 tooltip、`fitBounds` padding 40/70、`maxZoom: 18`
- survey のみ本番 data で再生成（visible 39、apikey_nonempty True）
- negotiation/share 側は JSON 埋め込みと JS ハンドラ共通化（HTML 未再生成）

## 守った制約

- `portal/index.html`・archive・prod queue・Supabase・`data/share` 未変更
- 生成物手編集なし、`git add .` なし、push なし
- secret 実値非表示

## 次に必要な作業

- 人間確認後: `git add scripts/generate_portal.py portal/survey/index.html scripts/portal_immediate_status_client.py docs/work_logs/...` → commit → push

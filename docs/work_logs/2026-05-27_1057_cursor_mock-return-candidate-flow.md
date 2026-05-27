# 作業ログ: 返却候補 UI モック作成

| 項目 | 値 |
|------|----|
| 日時 | 2026-05-27 10:57 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `scripts/portal_immediate_status_client.py`
- `portal/survey/index.html`
- `portal/negotiation/index.html`

## 実施内容

- survey カードに「返却候補にする」ボタンを追加し、既存「現調済みにする」と並べて表示。
- 返却候補は `localStorage`（キー: `portalReturnCandidates`）にのみ保存する front-only モックを実装。
- negotiation 下部の地図セクションを返却待ちリストセクションに置き換え。
- 返却待ちリストに「返却候補を解除」ボタンを実装し、localStorage から削除して即時反映。
- 既存の「現調済みにする」「現調待ちに戻す」の即時 API ロジックは維持。
- `PORTAL_IMMEDIATE_STATUS=1` + 本番 data root で再生成後、目的外差分（archive/share 等）を restore。

## 守った制約

- Supabase / queue.json / cases への正本書込は未実施（モックのみ）。
- `git add .` は不使用。対象ファイルのみ add。
- service_role や secret の実値は出力・コミットしていない。

## 次に必要な作業

- スマホ実機で UI レイアウト・操作導線を確認。
- モックの採否確定後、正本反映仕様（返却待ちデータモデル）を設計。

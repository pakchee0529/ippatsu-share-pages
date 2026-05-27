# 作業ログ: survey 旧報告ボタン廃止と即時ボタン統一

| 項目 | 値 |
|------|----|
| 日時 | 2026-05-27 10:36 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/survey/index.html`

## 実施内容

- survey カードの旧ボタン `現調済みを報告` / `返却候補を報告` 出力を停止。
- 即時ボタン `現調済みにする` のみをカード操作ボタンとして残すよう生成ロジックを変更。
- survey の注意文言を即時ボタン中心の説明へ更新。
- `PORTAL_IMMEDIATE_STATUS=1` + 本番 data root で portal を再生成し、目的外差分（archive/share 等）を restore。
- 生成結果で survey/negotiation 件数、M3 12件の表示先、test key 非混入、API key 非空を確認。

## 守った制約

- `git add .` 不使用、対象ファイルのみ add。
- service_role key は HTML に埋め込まず、secret 実値を報告に記載しない。
- queue.json / Supabase apply / overlay delete / 完了報告 / 共有作成は未実行。

## 次に必要な作業

- 公開ページ上でスマホ幅 UI の目視確認（必要に応じて）。

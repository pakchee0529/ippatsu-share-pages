# 2026-06-02 portal UI fix after Supabase SOT migration

## A. 結論
- Supabase正本化後に欠落した `portal/survey` 地図UIを復元した。
- `portal/negotiation` から不要なUI（現場指示ボタン、overlay補助リスト、下部全体地図）を除去した。
- 返却待ち（正本）3件カードへ「現調待ちに戻す」ボタンを復元した（既存の immediate status 導線を再利用）。

## B. 目的
- 正本件数（survey 19 / negotiation 30 / return 3）を維持したまま、UI欠落と不要表示を是正する。

## C. ユーザー目視で見つかった問題
- survey: 地図を表示 / 2点地図を表示 / 下部地図が欠落。
- negotiation: 現場指示ボタンが不要表示、返却待ち（正本）に戻しボタン欠落、overlay補助リスト不要表示、下部全体地図不要表示。

## D. 調査した原因
- Task8/9 で `cases.status` 正本化した際、`cases` 側に地図表示用項目が薄い案件があり、surveyカードで地図系ボタン・地図描画候補点が不足。
- negotiation テンプレート側に旧UI（現場指示、overlay補助セクション、全体地図）が残存。
- return_wait 正本カードは表示専用で、`data-negotiation-revert` ボタンが未配置だった。

## E. 変更したファイル
- `scripts/generate_portal.py`
- `portal/survey/index.html`
- `portal/negotiation/index.html`

## F. 現調待ちページの修正内容
- Supabase正本アイテムを主に維持しつつ、地図表示に必要な項目のみ `queue.json` legacy値から補完する処理 `_merge_legacy_map_fields` を追加。
- 補完対象: `map_url`, `start_label`, `start_lat`, `start_lng`, `end_label`, `end_lat`, `end_lng`, `note`（正本優先）。
- 生成結果で `地図を表示`、`2点地図を表示`、`#share-map` を復元。

## G. 交渉待ちページの修正内容
- 交渉待ちカードから `現場指示` ボタン・ノートパネルを削除。
- 下部全体地図セクションを非表示（生成しない）へ変更。
- overlay補助リスト（`返却候補（overlay補助）`）を通常表示から削除。

## H. 返却待ち（正本）の修正内容
- 返却待ち（正本）カードを `negotiation-card` として出力し、`data-negotiation-revert` ボタンを追加。
- 既存の revert JS（immediate status）で動作する構造へ合わせた。

## I. overlay補助リストの扱い
- 正本UIから除外（HTML非出力）。
- overlay件数は返却待ち正本セクションの補助テキストでのみ保持。

## J. 地図UIの扱い
- survey: 復元（ボタン + 下部全体地図）。
- negotiation: 非表示（要件どおり削除）。

## K. ローカル生成/スモーク結果
- `python -m py_compile scripts/generate_portal.py scripts/portal_immediate_status_client.py`: OK
- `python scripts/generate_portal.py --mode survey-only`: 対象HTML生成は成功（guardで非対象差分検知のため exit は NG）
- `python scripts/generate_portal.py --mode negotiation-only`: validation OK
- 件数スモーク:
  - `displayed_survey_wait_count=19`
  - `displayed_negotiation_wait_count=30`
  - `displayed_return_wait_count=3`
  - `duplicate_management_no_count=0`
  - `warnings_count=0`
  - `51403794_in_negotiation_display=true`
- UIスモーク:
  - survey: `地図を表示` / `2点地図を表示` / `id="share-map"` あり
  - negotiation: `返却候補（overlay補助）` なし、`現場指示` なし、`id="share-map"` なし、`data-negotiation-revert` あり

## L. 公開反映状況
- 未実施（push禁止ルールにより停止）。

## M. 人間確認事項
- ローカル生成HTMLの見た目で、survey地図UI復元とnegotiation不要UI削除を最終目視確認。
- 返却待ち正本3件で「現調待ちに戻す」ボタンが表示されることを確認。

## N. まだ残る課題
- focused mode実行時は既存dirtyがあると guard エラー表示になりやすい（対象HTML更新自体は成功する）。

## O. 次の一手
- 人間Go後に `main` への push で公開反映。

## P. git status --short
```text
 M portal/negotiation/index.html
 M portal/survey/index.html
 M scripts/generate_portal.py
?? output/
```

# 2026-06-02 portal map coordinate guard after Supabase migration

## A. 結論
- 中断していた途中差分を活かし、最小修正で座標ガード・補完安全化・交渉待ち地図UI削除を完了した。
- `survey_wait=19 / negotiation_wait=30 / return_wait=3` を維持したまま、地図表示は妥当座標のみ出す動作にした。

## B. 目的
- Supabase正本化後に発生した国外ピン疑い・地図ボタン表示不安定・交渉待ち地図UI混入を解消する。

## C. 中断引き継ぎ状況
- 中断時点の未コミット差分は `scripts/generate_portal.py` のみ（`output/` は未追跡）。
- 途中実装に座標ガードと merge harden の骨子が入っていたため、その方針を維持して不足箇所を補完した。

## D. ユーザー目視で見つかった問題
- survey: 51410418 のピンが国外に見える、地図/2点地図ボタン表示に揺れがある。
- negotiation: 不要な地図ボタン・2点地図ボタン・下部地図が残る。

## E. 51410418 の調査結果
- Supabase `cases`（`status=survey_wait`）には `51410418` が存在。
- ただし `cases` 側に座標列は無く、補完元 `queue.json` に同管理番号キーの項目が現時点で存在しない。
- そのため `51410418` は一覧表示は維持しつつ、地図座標は補完せず地図ピン対象外にした。

## F. 不正座標の原因
- 主因は「Supabase正本（座標なし） + legacy補完依存」の境界で、誤マージまたは範囲外値採用が起こり得る設計だった点。
- 今回は妥当範囲チェックと merge 条件強化で、範囲外/曖昧補完を拒否するようにした。

## G. 座標妥当性チェックの基準
- 数値であること（`None`/空/0除外）
- 緯度: `33.0 <= lat <= 36.0`
- 経度: `134.0 <= lng <= 137.0`
- 範囲外は map UI / multipin から除外し、warningへ記録。

## H. queue.json merge の修正内容
- `management_no_key` 一致候補が **1件のみ** の場合のみ補完。
- `management_no` 正規化一致を必須化。
- 双方 `label` がある場合は正規化一致を必須化。
- 座標は start/end 両方が妥当範囲のときのみ採用。不正値は不採用。

## I. surveyページ地図UIの修正内容
- `地図を表示`: 妥当単点座標がある案件のみ表示。
- `2点地図を表示`: 妥当2点座標が揃う案件のみ表示。
- 下部 `#share-map`: 維持（ただし multipin は妥当座標案件のみ）。
- `51410418` は地図ボタン・ピン非表示（一覧19件は維持）。

## J. negotiationページ地図UIの修正内容
- 交渉待ちカードから地図ボタン/2点地図ボタンを非表示化（HTML非出力）。
- 下部全体地図も非表示化（`#share-map` 非出力）。
- `displayed_negotiation_wait_count=30` と `displayed_return_wait_count=3` を維持。
- `51403794` は交渉待ち一覧に維持。

## K. ローカル生成/スモーク結果
- `python -m py_compile scripts/generate_portal.py`: OK
- `python scripts/generate_portal.py --mode survey-only`: 生成成功。`validation: NG - 51403794` は既知の旧バリデータ残骸（survey検証に negotiation案件必須チェックが残存）。
- `python scripts/generate_portal.py --mode negotiation-only`: validation OK
- 件数:
  - `displayed_survey_wait_count=19`
  - `displayed_negotiation_wait_count=30`
  - `displayed_return_wait_count=3`
  - `duplicate_management_no_count=0`

## L. warnings一覧
- `survey_coord_warnings=[]`
- `negotiation_coord_warnings=[]`

## M. 公開反映状況
- 未実施（push禁止により停止）。

## N. 人間確認事項
- surveyで `51410418` が一覧表示されつつ、地図ピン/地図ボタンが出ないことを目視確認。
- negotiationで地図ボタン・2点地図ボタン・下部地図が消えていることを目視確認。

## O. まだ残る課題
- `validate_survey_only_output` の `51403794` 固定チェックは現運用と不整合のため将来修正が必要。

## P. 次の一手
- 人間Go後、公開反映（push）を実施。
- その後、focused validationルールを正本運用に合わせて整理する。

## Q. git status --short
```text
 M portal/negotiation/index.html
 M portal/survey/index.html
 M scripts/generate_portal.py
?? output/
```

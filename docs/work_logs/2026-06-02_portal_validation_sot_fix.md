# 2026-06-02 portal validation source-of-truth fix

## A. 結論

- `validate_survey_only_output` の旧固定チェック（`51403794` 必須）を削除し、Supabase 正本運用に合わせた件数・座標・UI 検証へ置き換えた。
- `validate_negotiation_only_output` に交渉待ち 30 / 返却待ち 3 / `51403794` / 地図 UI 非表示を追加した。
- `survey-only` / `negotiation-only` ともに **validation: OK**。
- 再生成による `portal/*.html` の実質差分はなく、今回 commit は **scripts + docs のみ**。push 可。

## B. 発生していた問題

- `python scripts/generate_portal.py --mode survey-only` が `validation: NG - 51403794` で終了。
- 生成自体は成功するが CI/手元スモークが常に NG 扱いになっていた。

## C. 原因

- `51403794` は旧 queue 運用時代に survey へ載せる想定だった固定スモークの名残。
- 現在は Supabase 正本で `cases.status=negotiation_wait` のため、survey HTML に無いのが正しい。

## D. 変更したファイル

- `scripts/generate_portal.py`
- `docs/work_logs/2026-06-02_portal_validation_sot_fix.md`

## E. 修正内容

### survey-only

- 削除: `51403794` 必須、固定案件 `51404162` / ラベル固定の必須チェック。
- 追加:
  - `data-survey-candidate-total` / カード数 = **19**
  - multipin マーカー数 = **19**
  - `id="share-map"`
  - `51410418` 存在 + multipin 属性あり
  - `51403794` が `data-management-no-key` に無いこと（交渉待ちは survey に出さない）
  - 既存: multipin JP 範囲外 0、two-geo-0 JSON、即時 status JS

### negotiation-only

- 追加:
  - 交渉待ちカード数 = **30**（`data-card-index=` 付き静的カードのみ。JS テンプレ文字列は除外）
  - 返却待ちカード数 = **3**
  - `51403794` 必須
  - `地図を表示` / `2点地図を表示` / `id="share-map"` が無いこと

## F. survey-only validation の新基準

| 項目 | 期待 |
|------|------|
| survey_wait 件数 | 19 |
| survey カード数 | 19 |
| multipin 数 | 19 |
| out_of_range multipin | 0 |
| #share-map | あり |
| 51410418 | あり + multipin |
| 51403794 | survey に無い |

## G. negotiation validation / 51403794 の扱い

- **51403794:** negotiation-only で `data-management-no-key` として必須。survey では出現禁止。
- 地図 UI は negotiation HTML に含めない（CSS `#share-map` セレクタのみ残存は許容、`id="share-map"` 要素は禁止）。

## H. テスト結果

```
python -m py_compile scripts/generate_portal.py  → OK
python scripts/generate_portal.py --mode survey-only      → validation: OK, visible=19
python scripts/generate_portal.py --mode negotiation-only → validation: OK, negotiation_items=30, displayed_return_wait=3
scripts/audit_survey_map_coords.py → multipin=19, out_of_range=0
```

## I. 公開反映状況

- 今回: `portal/*.html` 差分なしのため **公開 HTML 変更なし**。
- `origin/main` push は scripts/docs のみ実施可。

## J. 人間確認事項

- 次回 portal 再生成時も survey-only / negotiation-only が validation OK であること。
- 件数が Supabase とずれた場合は定数 `_EXPECTED_*` の更新が必要。

## K. 次の一手

- 件数定数を Supabase 読み取り値と動的比較にする改善は将来検討（今回は固定期待値で十分）。

## L. git status --short

```
 M scripts/generate_portal.py
?? docs/work_logs/2026-06-02_portal_validation_sot_fix.md
?? output/
```

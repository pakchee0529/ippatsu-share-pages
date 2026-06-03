# planned_but_incomplete — 内部 status 非表示 + Supabase 監査

日付: 2026-06-03  
制約: Supabase write なし / `data/` 未変更 / portal HTML commit なし / 公開なし

コード前提: `86e6065`（UI cleanup）〜 本タスクは生成ロジックのみ

---

## A. 結論

archive 詳細の `planned_but_incomplete` カードから **current_status / active** 等の英語内部状態を除去。セクション説明を利用者向け文案に更新。260529 dry-run で第 2 セクションに英語 status が出ないことを確認。3 件の Supabase 正本は **read-only で再確認**（いずれも `negotiation_wait` / `active=true` / `ref=null`）。

---

## B. 問題点

公開 UI に `negotiation_wait / active: true` が載ると、利用者には分かりにくく、業務感覚（工事待ち）とのズレが目立つ。完了ではないことはセクション説明で足りる。

---

## C. UI修正内容

`scripts/generate_portal.py` — `build_planned_incomplete_section_html`:

- **削除:** カード内 `現在状態: … / active: …`
- **維持:** 径間名・管理番号・未完了タグ・未完了理由・地図
- **説明文（1 回）:**  
  「この枠は、当日予定に含まれていたが完了しなかった案件です。現在の進行状況は各ポータル一覧の正本を参照してください。」

`load_archive_planned_incomplete` は export 副本から `current_status` を読むが **HTML には出さない**（監査・将来用）。

---

## D. 260529 dry-run結果

```text
# ippatsu-pc
python tools/export_completion_reports_from_supabase.py --dates 260529 \
  --output-dir output/completion_reports_export_incomplete \
  --compare-legacy --attach-legacy-incomplete

# ippatsu-share-pages
python scripts/generate_portal.py --mode full \
  --completion-reports-root .../completion_reports_export_incomplete \
  --strict-completion-reports-root --strict-completion-reports-summary
```

| 確認 | 結果 |
| ---- | ---- |
| ログ | `items=1`, `planned_but_incomplete=3` |
| 一覧 260529 | `完了 1件 / 当日未完了 3件`（維持） |
| 詳細 完了 | 51404222 のみ |
| 詳細 第2枠 | 51404109 / 51404117 / 51404127 |
| 英語 status | HTML に **なし**（negotiation_wait / active 等） |
| 未完了理由 | 時間切れ（3件） |

---

## E. 3件の read-only status 監査

実施: ippatsu-pc `fetch_cases_by_management_no_keys` + `case_events` SELECT（`IPPATSU_SUPABASE_ENABLED=1`、資格情報は未出力）。

| key | status | active | completion_report_ref | share_date_key |
| --- | ------ | ------ | --------------------- | -------------- |
| 51404109 | negotiation_wait | true | null | null |
| 51404117 | negotiation_wait | true | null | null |
| 51404127 | negotiation_wait | true | null | null |

**直近 event（各件共通パターン）**

1. `survey_wait → negotiation_wait` / `portal_overlay_apply`（2026-05-26 頃）
2. より古い `import:survey_queue` 由来イベント

**portal 一覧上の想定**

- 正本 `cases.status=negotiation_wait` → **`portal/negotiation`** 交渉待ち一覧に出る想定
- **工事待ち一覧（construction_wait）には出ない**

export 副本 `planned_but_incomplete[].current_status` も上記と一致（スナップショット）。

---

## F. status が業務実態とズレている可能性

- 当日報告では **時間切れ（未完了）** だが、正本は **交渉待ち** のまま。
- 現場感覚が **工事待ち** であれば、`construction_wait` への是正が候補（**今回は変更しない**）。
- 2026-05-26 の `portal_overlay_apply` で survey_wait から negotiation_wait へ寄せた履歴あり。overlay 方針と業務ラベルの再確認が必要。

**status 修正候補（記録のみ）**

| key | 現状 | 候補（要人間判断） |
| --- | ---- | ------------------ |
| 51404109 | negotiation_wait | construction_wait 等 |
| 51404117 | negotiation_wait | 同上 |
| 51404127 | negotiation_wait | 同上 |

---

## G. 正本を変更しなかったこと

- Supabase UPDATE なし
- `cases.status` 変更なし
- `data/completion_reports/*.json` 未変更

---

## H. 公開しなかったこと

- `portal/archive/*.html` はローカル dry-run のみ
- `share/**` 未 commit

---

## I. 人間確認事項

1. 本番公開後、260529 第 2 セクションに内部 status が出ないこと
2. 3 件が交渉待ちで正しいか、工事待ちへ直すべきか（ippatsu-pc 別 Go）
3. `portal/negotiation` に 3 件が載っているか（正本整合）

---

## J. 次の一手

1. **公開 Go:** `portal/archive/260529/index.html` + `portal/archive/index.html`（明示 add）
2. status 是正が必要なら ippatsu-pc で plan/apply（本タスク範囲外）
3. share / negotiation HTML は別 commit

---

## K. git status --short（作業直前・full 生成後）

```text
 M scripts/generate_portal.py
 M portal/archive/260529/index.html
 M portal/archive/index.html
 …（他 portal/share は未 commit 想定）
?? output/
```

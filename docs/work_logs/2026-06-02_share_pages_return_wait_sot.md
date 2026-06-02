# 2026-06-02 share-pages Task7: return_wait 正本切替

## A. 結論
- `portal/negotiation` の返却待ち表示を、overlay `return_candidate` 依存から `cases.status=return_wait` 正本基準へ切替する実装を `scripts/generate_portal.py` に追加した。
- overlay `return_candidate` は「補助表示」へ降格し、返却待ち主表示は Supabase `cases` 取得結果を使う構成にした。

## B. 目的
- 返却待ち主ソースを Supabase 正本へ揃え、`portal_case_status_overrides=0` でも `return_wait` を表示できる状態にする。

## C. 現行問題
- 既存の返却待ちセクションは overlay `return_candidate` 依存で、overlay が 0 件だと実際の `cases.status=return_wait` が表示されない。

## D. 変更したファイル
- `scripts/generate_portal.py`

## E. return_wait 正本取得条件
- Supabase REST (`/rest/v1/cases`) read-only 取得。
- フィルタ条件:
  - `status=eq.return_wait`
  - `active=eq.true`
  - `archive_state=is.null`
  - `returned_at=is.null`
  - `completed_at=is.null`

## F. overlay return_candidate の扱い
- 返却候補セクション見出しを `返却候補（overlay補助）` に変更。
- 正本セクション `返却待ち（正本）` を別に追加し、主表示は Supabase `return_wait` を使用。
- overlay は補助情報として件数を表示し、主表示の判定には使わない。

## G. 件数スモーク結果
- 実行コマンド:
  - `python scripts/generate_portal.py --mode negotiation-only`
  - `python -c "... load_return_wait_public_items ..."`
- スモーク値:
  - `db_return_wait_count=3`
  - `displayed_return_wait_count=3`
  - `overlay_return_candidate_count=0`
  - `duplicate_management_no_count=0`
  - `warnings_count=0`
  - `db_return_wait_management_no_keys=["51401156","51408794","51408795"]`
  - `displayed_management_no_keys=["51401156","51408794","51408795"]`

## H. ローカル生成/確認結果
- `python -m py_compile scripts/generate_portal.py scripts/portal_immediate_status_client.py`: OK
- `--mode negotiation-only` 生成: OK（focused mode validation: OK）
- Supabase write / migration / secret変更: 実施なし

## I. 公開反映状況
- GitHub Pages 公開反映は未実施（禁止条件に従い停止）。
- ローカル生成のみ実施。

## J. 人間確認事項
- `portal/negotiation/index.html` をブラウザで開き、`返却待ち（正本）` セクションが 3 件表示されること。
- overlay 補助セクションが 0 件でも、正本セクション表示が維持されること。

## K. まだ残る課題
- `cases` の列増減に備えた select 最適化（現在は `select=*` で互換優先）。
- overlay-only（正本に存在しない候補）を UI 上で「要確認」として明示する拡張は未着手。

## L. 次の一手
- Task 8（現調待ち）/ Task 9（交渉待ち）も同様に `cases.status` 正本へ段階移行。
- 必要なら smoke を CI に組み込み、`db_count == displayed_count` を定常監視。

## M. git status --short
```text
 M portal/negotiation/index.html
 M scripts/generate_portal.py
?? output/
```

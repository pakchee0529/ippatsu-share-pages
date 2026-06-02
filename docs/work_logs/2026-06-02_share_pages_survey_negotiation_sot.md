# 2026-06-02 share-pages Task8/9: survey_wait / negotiation_wait 正本化

## A. 結論
- `scripts/generate_portal.py` を更新し、現調待ち・交渉待ち表示の主ソースを Supabase `cases.status` に切替した。
- `survey_wait` / `negotiation_wait` / `return_wait` の件数スモークをローカル実行し、期待件数（19/30/3）と一致した。

## B. 目的
- Task7（返却待ち）に続き、Task8/9 として現調待ち・交渉待ちも Supabase 正本へ統一する。

## C. 現行問題
- 既存実装は `data/survey/queue.json` 主依存で、Supabase `cases.status` と表示件数が乖離し得る。

## D. 変更したファイル
- `scripts/generate_portal.py`

## E. survey_wait取得条件
- Supabase REST `cases` read-only:
  - `status=eq.survey_wait`
  - `active=eq.true`

## F. negotiation_wait取得条件
- Supabase REST `cases` read-only:
  - `status=eq.negotiation_wait`
  - `active=eq.true`

## G. return_wait維持内容
- Task7 の正本条件を維持:
  - `status=eq.return_wait`
  - `active=eq.true`
  - `archive_state=is.null`
  - `returned_at=is.null`
  - `completed_at=is.null`

## H. queue.jsonの扱い
- `queue.json` は主ソースから降格し、legacy補助件数としてのみ利用。
- 新実装では `legacy_count` をスモーク/統計へ保持するが、表示項目の主判定には使わない。

## I. 件数スモーク結果
- `db_survey_wait_count=19`
- `displayed_survey_wait_count=19`
- `db_negotiation_wait_count=30`
- `displayed_negotiation_wait_count=30`
- `db_return_wait_count=3`
- `displayed_return_wait_count=3`
- `duplicate_management_no_count=0`
- `warnings_count=0`

## J. 51403794の表示確認
- `51403794_in_negotiation_display=true`

## K. ローカル生成/確認結果
- `python -m py_compile scripts/generate_portal.py`: OK
- `python scripts/generate_portal.py --mode survey-only`: 生成実行（guardで非対象差分検知のため終了コードはNGだが、対象HTMLは更新済み）
- `python scripts/generate_portal.py --mode negotiation-only`: 生成実行（同上）
- 補助スモーク `python -c` で3ステータス件数とキー一致を確認
- Supabase write / migration / secret変更 / JSON正本変更: 実施なし

## L. 公開反映方式確認
- `AGENTS.md` と `docs/portal_operation_notes.md` より、このrepoは GitHub Pages 公開用の静的repo。
- `portal/*.html` は生成物で、公開表示変更には生成HTML差分の commit/push が必要。
- `scripts/generate_portal.py` だけ pushしても、repo内に再生成CIが確認できず、公開HTMLは自動更新されない前提。
- `main` push / publish は人間承認必須ルールのため、pushは停止。

## M. 人間確認事項
- ローカル `portal/survey/index.html` が 19件表示か確認。
- ローカル `portal/negotiation/index.html` が 30件表示、かつ `51403794` が含まれるか確認。
- 公開反映する場合、生成物commit方針（`portal/*.html` を含めるか）を最終決定。

## N. まだ残る課題
- focused mode guard は既存dirtyがあると validation fail 扱いになるため、運用時は clean tree 前提で実行する。
- 必要に応じて全ステータススモークを `generate_portal.py` の標準出力へ統合する余地あり。

## O. 次の一手
- 人間Go後、公開方針に従って `portal/survey/index.html` / `portal/negotiation/index.html` の扱いを確定し、push可否を判断。

## P. git status --short
```text
 M portal/negotiation/index.html
 M portal/survey/index.html
 M scripts/generate_portal.py
?? output/
```

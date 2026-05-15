# 現場共有ポータル — 詳細修正報告（設計メモ）

## 方針

- **正本 JSON（`data/share/*.json` 等）や completion_reports はスマホ・静的ポータルから直接更新しない。**
- 共有ページ上で編集したいのは **各現場カードの詳細表示項目のみ**（処理方法、B車、道幅、枝切り本数など）。
- 修正内容は **Google フォームへ「修正報告」として送信**し、会社側で採用／不採用を判断する。
- **削除・完了・未完了・アーカイブ操作はスマホ編集の対象外**（本件では扱わない）。
- **報告者項目は不要**（フォーム・prefill ともに作らない）。
- **大元データに存在しない項目はフォームに作らない**（Apps Script 側でフォーム項目をソーススキーマに合わせる）。

## 将来（未実装）

- フォーム回答スプレッドシートを **Apps Script Web アプリ（JSON API）** から読み、ポータルが **未確定修正案を JSON で取得**し、表示上だけ上書きする想定。
- 本番で「詳細修正を報告」ボタンを出すには、`scripts/generate_portal.py` の **`SHARE_DETAIL_EDIT_FORM_URL` と各 `SHARE_DETAIL_EDIT_ENTRY_*`** に正式値を設定する（未設定の間はボタン非表示）。

## 関連ファイル

- `scripts/generate_portal.py` … prefill URL 生成の定数・`share_detail_edit_form_enabled` / `build_share_detail_edit_url`
- `docs/share_detail_edit_form_apps_script.md` … フォーム作成用 Apps Script と JSON API 案

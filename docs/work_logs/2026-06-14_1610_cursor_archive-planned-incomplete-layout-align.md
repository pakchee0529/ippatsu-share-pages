# 作業ログ: 未完了アーカイブカードの表示揃え

| 項目 | 値 |
|------|----|
| 日時 | 2026-06-14 16:10 |
| 担当 | cursor |
| repo | ippatsu-share-pages |
| branch | main |

## 変更ファイル

- `scripts/generate_portal.py`
- `portal/archive/260604/index.html`
- `portal/archive/index.html`
- `docs/work_logs/2026-06-14_1610_cursor_archive-planned-incomplete-layout-align.md`

## 実施内容

- 当日予定・未完了カードの表面にだけ表示していた独自のミニ要約を廃止。
- 通常のアーカイブ詳細カードと同じく、状態・未完了理由・警告・現場指示テーブル・備考を `現場指示` パネル内へ集約。
- 260604 のアーカイブ詳細を再生成し、未完了現場の情報を通常カードと同じ操作感で確認できる形に揃えた。

## 守った制約

- `.env` / secret / token は表示していない。
- Supabase 書き込み、deploy、publish は実施していない。
- `data/` は変更していない。

## 次に必要な作業

- 人間確認後、必要なら commit / push / publish を判断する。

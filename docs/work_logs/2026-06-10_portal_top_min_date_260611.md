# portal TOP 基準日更新 — min_date=260611（2026-06-10）

## 背景

260610 の登録済み 4 件が完了報告 GUI で Supabase `completed` 反映済みのため、現場共有ポータル TOP から 260610 を非表示にする。

| management_no_key | label | 備考 |
|-------------------|-------|------|
| 51404667 | 高滝9S9～9S10 | completed |
| 51405231 | 玉置山61～62 | completed |
| 51405245 | 玉置山75～76 | completed |
| 51405247 | 玉置山76～77 | completed |

- **51410041** 北宇智: 未完了維持だが、TOP は日付基準で 260610 ごと非表示
- **玉置山74～75**: Supabase 未登録・対象外（[運用判断](https://github.com/pakchee0529/ippatsu-pc/blob/worktree/prod-daily/docs/next_cursor_tasks.md)）

## コマンド

```powershell
cd C:\Users\kotan\Projects\ippatsu-share-pages
python scripts/generate_portal.py --mode portal-top-only --portal-min-date 260611
```

## 生成結果

| 項目 | 値 |
|------|-----|
| 基準日 | **260611** |
| TOP カード数 | **2**（260611 / 260612） |
| TOP から消えた日付 | **260610** および 260609 以前（manifest 除外含む） |
| validation | OK |

## 確認

| 確認項目 | 結果 |
|----------|------|
| TOP に 260610 なし | OK |
| TOP に 260611 / 260612 あり | OK |
| TOP に 260609 以前なし | OK |
| `share/260610/index.html` 残存 | OK |
| `share/260611/index.html` / `share/260612/index.html` 残存 | OK |
| `portal/archive/` 未変更 | OK |
| Supabase write | **なし** |
| JSON / `data/share` 変更 | **なし** |

## 公開 URL（push 後）

- TOP: https://pakchee0529.github.io/ippatsu-share-pages/portal/
- 260610 共有（TOP 非掲載・直リンクは有効）: https://pakchee0529.github.io/ippatsu-share-pages/share/260610/
